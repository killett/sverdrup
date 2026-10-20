"""Hygiene item 51 (part 2): a MIOST state file keeps its basis DOMAIN.

``save_state`` wrote alpha / l_t / n_dir / ladder but not the pavement
domain (``x0_km``/``y0_km``/``d_x_km``/``d_y_km``), so a tile-domain state
reloaded onto the signed-box domain: a different element enumeration under
the same coefficient vector — a shape error at best, misplaced elements at
worst. The point state's ``basis_key`` was written and never read; the
ensemble state wrote none.

Expected values come from the in-memory object built from the spec the test
constructs — never from the persistence code under test.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from sverdrup.core.grid import GridSpec
from sverdrup.distributions.miost_ensemble import (
    MiostEnsembleDistribution,
    ensemble_provenance,
)
from sverdrup.methods.miost import MiostPointDistribution
from sverdrup.methods.miost_basis import BasisSpec, lonlat_to_km
from tests._miost_fixtures import (
    TINY_DAY,
    TINY_GRID_LAT,
    TINY_GRID_LON,
    TINY_SPEC,
    TINY_WINDOW,
)

P = np.array([[300.0, 38.0, 30.0], [301.0, 39.0, 30.0], [299.0, 37.0, 25.0]])
_X, _Y = lonlat_to_km(P[:, 0], P[:, 1])
# A tile domain around the query points — deliberately NOT the signed box.
TILE_SPEC = replace(
    TINY_SPEC,
    x0_km=float(_X.mean()) - 700.0,
    y0_km=float(_Y.mean()) - 600.0,
    d_x_km=1400.0,
    d_y_km=1200.0,
)
_DOMAIN_KEYS = ("x0_km", "y0_km", "d_x_km", "d_y_km")
M = 3


def _n_el(spec: BasisSpec) -> int:
    return int(spec.elements_for_window(TINY_WINDOW.start_day).identity.shape[0])


def _point(spec: BasisSpec) -> MiostPointDistribution:
    rng = np.random.default_rng(5)
    return MiostPointDistribution.from_etas(
        grid=GridSpec.lonlat(TINY_GRID_LON, TINY_GRID_LAT),
        time_days=TINY_DAY,
        spec=spec,
        etas={TINY_WINDOW.id: rng.standard_normal(_n_el(spec))},
        window_starts={TINY_WINDOW.id: TINY_WINDOW.start_day},
    )


def _ensemble(spec: BasisSpec) -> MiostEnsembleDistribution:
    rng = np.random.default_rng(6)
    n = _n_el(spec)
    return MiostEnsembleDistribution(
        grid=GridSpec.lonlat(TINY_GRID_LON, TINY_GRID_LAT),
        mean=np.zeros((TINY_GRID_LAT.size, TINY_GRID_LON.size)),
        provenance=ensemble_provenance(M),
        time_days=TINY_DAY,
        m=M,
        _spec=spec,
        _etas_a={TINY_WINDOW.id: rng.standard_normal(n)},
        _anoms={TINY_WINDOW.id: rng.standard_normal((n, M))},
        _window_starts={TINY_WINDOW.id: TINY_WINDOW.start_day},
    )


def _rewrite(
    path: Path, *, drop: tuple[str, ...] = (), set_: dict[str, str] | None = None
) -> None:
    """Rewrite a state file into an older / tampered layout."""
    with np.load(path) as z:
        arrays = dict(z)
    for key in drop:
        arrays.pop(key, None)
    arrays.update(set_ or {})
    np.savez(path, **arrays)


def test_the_fixture_domain_is_not_the_box_and_the_points_are_inside() -> None:
    """Guards the two tests below against vacuity: a tile spec equal to the
    box (nothing to lose) or query points outside support (0 == 0)."""
    assert TILE_SPEC.key() != TINY_SPEC.key()
    assert np.all(_point(TILE_SPEC).mean_at(P) != 0.0)


def test_point_state_round_trips_a_tile_domain(tmp_path: Path) -> None:
    """Bug caught: the domain dropped on save, so the reload enumerates the
    box's elements under the tile's coefficients."""
    d = _point(TILE_SPEC)
    p = tmp_path / "point.npz"
    d.save_state(p)
    back = MiostPointDistribution.load_state(p)
    assert back._spec == TILE_SPEC
    np.testing.assert_array_equal(back.mean_at(P), d.mean_at(P))


def test_ensemble_state_round_trips_a_tile_domain(tmp_path: Path) -> None:
    """Bug caught: as above, for the ensemble's mean AND member anomalies."""
    d = _ensemble(TILE_SPEC)
    p = tmp_path / "ens.npz"
    d.save_state(p)
    back = MiostEnsembleDistribution.load_state(p)
    assert back._spec == TILE_SPEC
    np.testing.assert_array_equal(back.member_at(1, P), d.member_at(1, P))


def test_a_pre_fix_tile_point_state_is_refused_not_misplaced(tmp_path: Path) -> None:
    """The pre-fix layout: ``basis_key`` (with its ``;dom=`` suffix) and no
    domain fields. Bug caught: silently rebuilding it on the box domain —
    the written-but-never-read key is exactly what tells the two apart."""
    p = tmp_path / "point.npz"
    _point(TILE_SPEC).save_state(p)
    _rewrite(p, drop=_DOMAIN_KEYS)
    with pytest.raises(ValueError, match="basis_key"):
        MiostPointDistribution.load_state(p)


def test_an_ensemble_state_whose_basis_key_disagrees_is_refused(
    tmp_path: Path,
) -> None:
    """Bug caught: a stored basis key that is never compared (the point
    state's status quo) — e.g. a file from different basis constants."""
    p = tmp_path / "ens.npz"
    _ensemble(TILE_SPEC).save_state(p)
    _rewrite(p, set_={"basis_key": replace(TILE_SPEC, alpha=2.0).key()})
    with pytest.raises(ValueError, match="basis_key"):
        MiostEnsembleDistribution.load_state(p)


@pytest.mark.parametrize("kind", ["point", "ensemble"])
def test_a_legacy_box_state_without_domain_fields_still_loads(
    tmp_path: Path, kind: str
) -> None:
    """Bug caught: a fix that hard-requires the new keys, making every
    recorded phase-12/13 member store (box domain, no domain fields, no
    ensemble ``basis_key``) unreadable."""
    p = tmp_path / "legacy.npz"
    if kind == "point":
        d: MiostPointDistribution | MiostEnsembleDistribution = _point(TINY_SPEC)
        d.save_state(p)
        _rewrite(p, drop=_DOMAIN_KEYS)  # pre-fix point files kept basis_key
        back: MiostPointDistribution | MiostEnsembleDistribution = (
            MiostPointDistribution.load_state(p)
        )
    else:
        d = _ensemble(TINY_SPEC)
        d.save_state(p)
        _rewrite(p, drop=(*_DOMAIN_KEYS, "basis_key"))
        back = MiostEnsembleDistribution.load_state(p)
    assert back._spec == TINY_SPEC
    np.testing.assert_array_equal(back.mean_at(P), d.mean_at(P))


@pytest.mark.parametrize("kind", ["point", "ensemble"])
def test_a_numpy_or_int_typed_domain_round_trips_without_a_false_refusal(
    tmp_path: Path, kind: str
) -> None:
    """``Miost(basis_domain=...)`` passes the domain through uncoerced, and
    the probe builds it from km arithmetic (``np.float64``) — whose numpy-2
    repr is ``np.float64(-300.0)``. Bug caught: a key check comparing the
    saved spec's RAW ``key()`` to the float-rebuilt one, refusing every
    correctly saved file whose domain was not a Python float."""
    spec = replace(
        TILE_SPEC,
        x0_km=np.float64(TILE_SPEC.x0_km),
        y0_km=np.float64(TILE_SPEC.y0_km),
        d_x_km=1400,  # an int, as a JSON-sourced extent would arrive
    )
    assert "np.float64(" in spec.key()  # the hazard is real on this numpy
    p = tmp_path / "typed.npz"
    if kind == "point":
        d: MiostPointDistribution | MiostEnsembleDistribution = _point(spec)
        d.save_state(p)
        back: MiostPointDistribution | MiostEnsembleDistribution = (
            MiostPointDistribution.load_state(p)
        )
    else:
        d = _ensemble(spec)
        d.save_state(p)
        back = MiostEnsembleDistribution.load_state(p)
    assert back._spec == spec
    np.testing.assert_array_equal(back.mean_at(P), d.mean_at(P))
