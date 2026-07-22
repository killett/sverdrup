"""Tile-frame helper tests (phase-14 Task 12, 0d-1).

ONE shared helper emits {core, solve, obs} frames; the anchor's degenerate
frame reproduces the signed box EXACTLY (grid nodes byte-equal, obs
selection identical to the legacy ``halo_obs`` path including the recorded
43.2°N node-overshoot sliver).
"""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.adapters.altimetry import BBox
from sverdrup.application.spatial_tiles import (
    anchor_frame,
    frame_grid,
    frame_obs,
    operative_halo_deg,
    tile_plan,
)
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.validation.params import baseline_config
from sverdrup.validation.run import halo_obs

# ---------------------------------------------------------------------------
# Anchor degeneracy (the load-bearing identity)
# ---------------------------------------------------------------------------


def test_anchor_frame_is_the_signed_box() -> None:
    """core == the signed 10x10 box, overlap 0, halo = the operative 1.0."""
    f = anchor_frame()
    assert f.core == BBox(lon_min=295.0, lon_max=305.0, lat_min=33.0, lat_max=43.0)
    assert f.overlap_deg == 0.0
    assert f.halo_deg == operative_halo_deg() == 1.0
    assert f.solve_bbox == f.core  # zero overlap: degenerate


def test_anchor_grid_byte_equal_to_legacy() -> None:
    """frame_grid at 0.2 deg reproduces the baseline grid nodes EXACTLY."""
    legacy = baseline_config()[1]
    ours = frame_grid(anchor_frame(), resolution_deg=0.2)
    assert np.array_equal(ours.x, legacy.x)
    assert np.array_equal(ours.y, legacy.y)
    assert ours.x.dtype == legacy.x.dtype
    assert ours.y.dtype == legacy.y.dtype
    assert ours.crs == legacy.crs


def _spread_obs() -> ObsWindow:
    """Deterministic obs spanning past the box on every side, incl. the
    43.2-44.2N sliver the nominal-box cut silently drops (the recorded
    quirk halo_obs exists to keep)."""
    lon = np.linspace(292.0, 308.0, 41)
    lat = np.linspace(31.0, 45.5, 41)
    lon2, lat2 = np.meshgrid(lon, lat)
    lon_f, lat_f = lon2.ravel(), lat2.ravel()
    n = lon_f.size
    return ObsWindow.from_arrays(
        lon_f,
        lat_f,
        np.linspace(0.0, 10.0, n),
        np.sin(lon_f) + np.cos(lat_f),
        DiagonalErrorModel(np.full(n, 1e-3)),
        mission=np.full(n, "syn"),
    )


def test_anchor_obs_selection_identical_to_legacy_halo_obs() -> None:
    """frame_obs == halo_obs on the legacy grid — byte-equal, sliver kept."""
    obs = _spread_obs()
    legacy = halo_obs(obs, baseline_config()[1], halo_deg=1.0)
    ours = frame_obs(obs, anchor_frame(), resolution_deg=0.2)
    assert np.array_equal(ours.coords(), legacy.coords())
    assert np.array_equal(ours.values(), legacy.values())
    kept_lat = ours.coords()[:, 1]
    assert (kept_lat > 43.9).any(), "the 43.2+halo sliver must be kept"


def test_obs_bbox_from_node_extent_not_nominal_box() -> None:
    """obs_bbox derives from GRID NODES +- halo: lat_max 43.2+1, not 43+1.

    Hand-derived: np.arange(33, 43.2, 0.2) overshoots to a 43.2 last node
    (fp length 52), while lon arange stops at 305.0 (fp length 51) — the
    recorded quirk. A nominal-box implementation returns 44.0 and fails.
    """
    box = anchor_frame().obs_bbox(resolution_deg=0.2)
    assert box.lat_max == pytest.approx(44.2, abs=1e-9)
    assert box.lat_min == pytest.approx(32.0, abs=1e-9)
    assert box.lon_max == pytest.approx(306.0, abs=1e-9)
    assert box.lon_min == pytest.approx(294.0, abs=1e-9)


# ---------------------------------------------------------------------------
# tile_plan arithmetic
# ---------------------------------------------------------------------------

_DOMAIN = BBox(lon_min=0.0, lon_max=45.0, lat_min=0.0, lat_max=45.0)


def test_tile_plan_deterministic_and_counts() -> None:
    """45x45 domain at 15-deg tiles -> 3x3 tiles, row-major, twice equal."""
    a = tile_plan(_DOMAIN, tile_deg=15.0, overlap_deg=2.0, halo_deg=1.0)
    b = tile_plan(_DOMAIN, tile_deg=15.0, overlap_deg=2.0, halo_deg=1.0)
    assert a == b
    assert len(a) == 9
    assert a[0].core == BBox(0.0, 15.0, 0.0, 15.0)
    assert a[4].core == BBox(15.0, 30.0, 15.0, 30.0)
    assert a[8].core == BBox(30.0, 45.0, 30.0, 45.0)


def test_tile_plan_clips_ragged_edge_to_domain() -> None:
    """A 40x20 domain: last column/row cores clipped to the domain bounds."""
    tiles = tile_plan(
        BBox(10.0, 50.0, 0.0, 20.0), tile_deg=15.0, overlap_deg=2.0, halo_deg=1.0
    )
    assert len(tiles) == 6  # 3 cols x 2 rows
    last = tiles[-1]
    assert last.core == BBox(40.0, 50.0, 15.0, 20.0)  # 10-wide, 5-tall remnant


def test_missing_neighbor_flags_exhaustive_3x3() -> None:
    """Every tile of the 3x3 plan carries EXACTLY its domain-edge sides.

    Exhaustive so a lat/lon flag inversion (W/S swapped) cannot pass on the
    symmetric corner cases alone.
    """
    tiles = tile_plan(_DOMAIN, tile_deg=15.0, overlap_deg=2.0, halo_deg=1.0)
    expected = [  # row-major, south row first
        {"W", "S"},
        {"S"},
        {"E", "S"},
        {"W"},
        set(),
        {"E"},
        {"W", "N"},
        {"N"},
        {"E", "N"},
    ]
    assert [set(t.missing_neighbors) for t in tiles] == expected


def test_tile_plan_rejects_invalid_domains() -> None:
    """Descending bounds and >360-deg lon spans refuse loudly."""
    with pytest.raises(ValueError, match="domain"):
        tile_plan(BBox(50.0, 10.0, 0.0, 20.0))
    with pytest.raises(ValueError, match="360"):
        tile_plan(BBox(0.0, 400.0, 0.0, 20.0))


def test_tile_plan_fp_marginal_width_no_zero_tile() -> None:
    """A width of 30+1e-12 at 15-deg tiles yields 2 columns, never a
    zero-width third (the fp-ceil overshoot bug)."""
    tiles = tile_plan(BBox(0.0, 30.0 + 1e-12, 0.0, 15.0), tile_deg=15.0, halo_deg=1.0)
    assert len(tiles) == 2
    assert all(t.core.lon_max - t.core.lon_min > 1.0 for t in tiles)


def test_solve_bbox_extends_only_toward_neighbors() -> None:
    """Overlap extends into neighbor tiles; flagged sides stay clipped."""
    tiles = tile_plan(_DOMAIN, tile_deg=15.0, overlap_deg=2.0, halo_deg=1.0)
    center = tiles[4]
    assert center.solve_bbox == BBox(13.0, 32.0, 13.0, 32.0)
    corner = tiles[0]  # W+S at domain edge: no extension there
    assert corner.solve_bbox == BBox(0.0, 17.0, 0.0, 17.0)


def test_halo_defaults_from_operative_kernel_scale() -> None:
    """tile_plan with halo unset uses operative_halo_deg() (single hook)."""
    tiles = tile_plan(_DOMAIN, tile_deg=15.0, overlap_deg=2.0)
    assert all(t.halo_deg == operative_halo_deg() for t in tiles)


def test_frame_is_frozen() -> None:
    """TileFrame is immutable (seal-grade config object)."""
    f = anchor_frame()
    with pytest.raises(AttributeError):
        f.overlap_deg = 5.0  # type: ignore[misc]
