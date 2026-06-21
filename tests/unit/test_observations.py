import dask.array as da
import numpy as np

from regatta.core.observations import (
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
