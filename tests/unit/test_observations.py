import dask.array as da
import numpy as np

from sverdrup.core.observations import (
    BandedErrorModel,
    DiagonalErrorModel,
    ObsWindow,
)


def _window(n=5):
    lon = np.linspace(-60, -58, n)
    lat = np.linspace(35, 37, n)
    t = np.linspace(0, 4, n)
    val = np.arange(n, dtype=float)
    return ObsWindow.from_arrays(lon, lat, t, val, DiagonalErrorModel(np.full(n, 0.01)))


def test_coords_and_values_shapes():
    w = _window(5)
    assert w.coords().shape == (5, 3)
    assert w.values().shape == (5,)
    assert np.allclose(w.coords()[:, 2], np.linspace(0, 4, 5))


def test_lazy_values_not_computed_on_construction():
    # Bug caught: eagerly materialising obs (invariant 2).
    arr = da.from_array(np.arange(5.0), chunks=2)
    w = ObsWindow.from_arrays(
        np.zeros(5), np.zeros(5), np.zeros(5), arr, DiagonalErrorModel(np.full(5, 1.0))
    )
    assert hasattr(w._values, "compute")  # still lazy
    assert w.values().shape == (5,)  # materialise on demand


def test_diagonal_error_adds_to_kernel_diagonal():
    # Bug caught: treating R as a scalar instead of a per-obs operator (spec 5.1).
    model = DiagonalErrorModel(np.array([0.1, 0.2, 0.3]))
    k = np.zeros((3, 3))
    model.add_to_diagonal(k)
    assert np.allclose(np.diag(k), [0.1, 0.2, 0.3])


def test_banded_error_model_is_correlated():
    # Bug caught: error model that can only be white noise.
    model = BandedErrorModel(
        variance=np.full(4, 1.0), corr_length=2.0, coords1d=np.arange(4.0)
    )
    r = model.as_matrix(4)
    assert r[0, 1] > 0  # off-diagonal correlation present
    assert np.allclose(r, r.T)


# ---------------------------------------------------------------------------
# P1-#6: diagonal-only paths read R through ONE refusing accessor
# ---------------------------------------------------------------------------

import re  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from sverdrup.core.observations import diagonal_variances  # noqa: E402


def _banded(n=4):
    return BandedErrorModel(
        variance=np.full(n, 1.0), corr_length=2.0, coords1d=np.arange(float(n))
    )


def test_diagonal_variances_returns_a_copy_of_the_variances():
    """Bug caught: aliasing the frozen model's array (a caller scaling the
    returned vector in place would rescale every later reader's R)."""
    v = np.array([0.1, 0.2, 0.3])
    model = DiagonalErrorModel(v)
    got = diagonal_variances(model, 3)
    np.testing.assert_array_equal(got, [0.1, 0.2, 0.3])
    got *= 10.0
    np.testing.assert_array_equal(model.variance, [0.1, 0.2, 0.3])


def test_a_correlated_R_is_refused_not_truncated():
    """Bug caught (hygiene P1-#6): ``np.diag(as_matrix(n))`` silently kept a
    BandedErrorModel's diagonal and dropped every correlation, in every
    diagonal-only method — the swath-ready hook working as white noise."""
    with pytest.raises(NotImplementedError, match="BandedErrorModel"):
        diagonal_variances(_banded(), 4)


def test_a_variance_count_that_is_not_n_is_refused():
    """Bug caught: ``as_matrix(n)`` ignored ``n``, so an R sized for a
    different window passed through as a wrong-length vector."""
    with pytest.raises(ValueError, match="3 variances for 4 observations"):
        diagonal_variances(DiagonalErrorModel(np.full(3, 0.1)), 4)
    with pytest.raises(ValueError, match="3 variances"):
        DiagonalErrorModel(np.full(3, 0.1)).as_matrix(4)
    with pytest.raises(ValueError, match="4 variances"):
        _banded(4).as_matrix(5)


def test_a_diagonal_model_of_another_class_is_accepted():
    """Bug caught: a guard keyed on the CLASS that refuses any other model,
    even one whose R has no off-diagonal entries at all."""

    class _OtherDiagonal:
        def add_to_diagonal(self, k):
            k[np.diag_indices_from(k)] += 2.0

        def as_matrix(self, n):
            return 2.0 * np.eye(n)

    np.testing.assert_array_equal(diagonal_variances(_OtherDiagonal(), 3), [2.0] * 3)


def test_no_src_path_reads_R_through_as_matrix_any_more():
    """Tripwire for the family: every vector read of R in ``src`` goes
    through ``diagonal_variances`` (seven sites took ``np.diag(as_matrix)``
    or ``.diagonal()``; a new one would silently re-open the hole)."""
    src = Path(__file__).resolve().parents[2] / "src" / "sverdrup"
    offenders = [
        f"{p.relative_to(src)}:{i}"
        for p in src.rglob("*.py")
        if p.name != "observations.py"
        for i, line in enumerate(p.read_text().splitlines(), 1)
        if re.search(r"\.as_matrix\(", line)
    ]
    assert offenders == []
