"""Spatial blend + partition-of-unity tests (phase-14 Task 13, 0d-2).

The paper's linear edge blend (U2022 verbatim on edges) + our separable
corner completion. Partition of unity asserted NUMERICALLY to 1e-12 in
every configuration: interior edge, four-tile corner, domain edge, missing
(land) tile renormalization, degenerate single tile.

Expected weights are hand-derived from the linear-ramp rule, never from
the implementation: two tiles [0,15]|[15,30] with overlap 2 share the
region [13,17]; the west tile's weight at lon L is (17-L)/4 (1 at 13, 0.5
at the core boundary 15, 0 at 17).
"""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.adapters.altimetry import BBox
from sverdrup.application.spatial_tiles import (
    TileFrame,
    anchor_frame,
    assemble,
    blend_weight,
    tile_plan,
)

_TOL = 1e-12


def _grid_points(bbox: BBox, n: int = 61) -> tuple[np.ndarray, np.ndarray]:
    lon = np.linspace(bbox.lon_min, bbox.lon_max, n)
    lat = np.linspace(bbox.lat_min, bbox.lat_max, n)
    lon2, lat2 = np.meshgrid(lon, lat)
    return lon2.ravel(), lat2.ravel()


def _weight_sum(
    tiles: tuple[TileFrame, ...], lon: np.ndarray, lat: np.ndarray
) -> np.ndarray:
    return np.sum([blend_weight(t, lon, lat) for t in tiles], axis=0)


# ---------------------------------------------------------------------------
# Hand-derived ramp values (the paper rule)
# ---------------------------------------------------------------------------


def test_edge_ramp_hand_values() -> None:
    """Two-tile edge: hand-computed linear ramp values, exactly."""
    tiles = tile_plan(BBox(0.0, 30.0, 0.0, 15.0), tile_deg=15.0, overlap_deg=2.0)
    west, east = tiles
    lat = np.array([7.5, 7.5, 7.5, 7.5, 7.5])
    lon = np.array([13.0, 14.0, 15.0, 16.0, 17.0])
    np.testing.assert_allclose(
        blend_weight(west, lon, lat), [1.0, 0.75, 0.5, 0.25, 0.0], atol=_TOL
    )
    np.testing.assert_allclose(
        blend_weight(east, lon, lat), [0.0, 0.25, 0.5, 0.75, 1.0], atol=_TOL
    )


def test_edge_reduction_separable_equals_1d_rule() -> None:
    """On a pure two-tile edge the separable weight IS the 1-D paper rule.

    At latitudes far from any lat boundary the lat factor is 1, so the
    product weight must equal the 1-D lon ramp exactly (no corner term).
    """
    tiles = tile_plan(BBox(0.0, 30.0, 0.0, 15.0), tile_deg=15.0, overlap_deg=2.0)
    west = tiles[0]
    lon = np.linspace(13.0, 17.0, 41)
    lat = np.full_like(lon, 7.5)  # mid-tile: no lat ramp active
    expected_1d = (17.0 - lon) / 4.0
    np.testing.assert_allclose(blend_weight(west, lon, lat), expected_1d, atol=_TOL)


# ---------------------------------------------------------------------------
# Partition of unity, every configuration, 1e-12
# ---------------------------------------------------------------------------


def test_partition_of_unity_2x1_edge() -> None:
    """Two tiles side by side: raw weights sum to 1 everywhere."""
    tiles = tile_plan(BBox(0.0, 30.0, 0.0, 15.0), tile_deg=15.0, overlap_deg=2.0)
    lon, lat = _grid_points(BBox(0.0, 30.0, 0.0, 15.0))
    np.testing.assert_allclose(_weight_sum(tiles, lon, lat), 1.0, atol=_TOL)


def test_partition_of_unity_2x2_corner() -> None:
    """Four tiles meeting at a corner: the separable products sum to 1.

    The corner square is where the papers are silent; the separable
    completion must close it exactly (incl. the exact corner point where
    all four weights are 0.25).
    """
    tiles = tile_plan(BBox(0.0, 30.0, 0.0, 30.0), tile_deg=15.0, overlap_deg=2.0)
    lon, lat = _grid_points(BBox(13.0, 17.0, 13.0, 17.0))  # the corner square
    np.testing.assert_allclose(_weight_sum(tiles, lon, lat), 1.0, atol=_TOL)
    w_each = [blend_weight(t, np.array([15.0]), np.array([15.0])) for t in tiles]
    np.testing.assert_allclose(np.concatenate(w_each), 0.25, atol=_TOL)


def test_partition_of_unity_domain_edge() -> None:
    """At a domain edge (missing neighbor) the single tile carries weight 1."""
    tiles = tile_plan(BBox(0.0, 30.0, 0.0, 15.0), tile_deg=15.0, overlap_deg=2.0)
    west = tiles[0]
    lon = np.array([0.0, 1.0, 7.5])  # the W domain edge and inward
    lat = np.array([7.5, 7.5, 7.5])
    np.testing.assert_allclose(blend_weight(west, lon, lat), 1.0, atol=_TOL)
    lon_all, lat_all = _grid_points(BBox(0.0, 5.0, 0.0, 15.0))
    np.testing.assert_allclose(_weight_sum(tiles, lon_all, lat_all), 1.0, atol=_TOL)


def test_partition_of_unity_degenerate_single_tile() -> None:
    """The anchor path adds NOTHING: weight is identically 1 in its box."""
    f = anchor_frame()
    lon, lat = _grid_points(f.core)
    np.testing.assert_allclose(blend_weight(f, lon, lat), 1.0, atol=_TOL)


def test_missing_tile_renormalization_recovers_constant_field() -> None:
    """A land-dropped tile: assemble renormalizes by the ACTUAL weight sum.

    With one of the 2x2 tiles absent, raw weights sum to <1 in its overlap;
    assembling a CONSTANT field from the remaining tiles must still return
    the constant exactly — a missing-renormalization bug returns c*sum_w.
    """
    tiles = tile_plan(BBox(0.0, 30.0, 0.0, 30.0), tile_deg=15.0, overlap_deg=2.0)
    present = tiles[:3]  # drop the NE tile (index 3): "land"
    lon, lat = _grid_points(BBox(0.5, 29.5, 0.5, 29.5))
    raw = _weight_sum(present, lon, lat)
    covered = raw > 0
    dented = covered & (raw < 1.0 - 1e-6)
    assert dented.any(), "dropping a tile must dent the raw sum somewhere"
    assert (~covered).any(), "the dropped core interior must be uncovered"
    const = 3.7
    fields = [np.full_like(lon, const) for _ in present]
    out = assemble(present, fields, lon, lat)
    np.testing.assert_allclose(out[covered], const, atol=_TOL)
    assert np.isnan(out[~covered]).all()


def test_assemble_blends_linearly_and_nan_outside_coverage() -> None:
    """assemble = weighted mean of per-tile fields; NaN where no tile."""
    tiles = tile_plan(BBox(0.0, 30.0, 0.0, 15.0), tile_deg=15.0, overlap_deg=2.0)
    lon = np.array([14.0, 15.0, 40.0])  # overlap, boundary, outside domain
    lat = np.array([7.5, 7.5, 7.5])
    fields = [np.full_like(lon, 1.0), np.full_like(lon, 3.0)]
    out = assemble(tiles, fields, lon, lat)
    # hand values: w_west 0.75/0.5 -> 1*0.75+3*0.25 = 1.5; 1*0.5+3*0.5 = 2
    np.testing.assert_allclose(out[:2], [1.5, 2.0], atol=_TOL)
    assert np.isnan(out[2])


def test_tile_plan_refuses_zero_overlap_multitile() -> None:
    """Zero overlap with >1 tile double-counts shared boundaries: refuse."""
    with pytest.raises(ValueError, match="overlap"):
        tile_plan(BBox(0.0, 30.0, 0.0, 15.0), tile_deg=15.0, overlap_deg=0.0)
    # single tile with zero overlap stays legal (the anchor shape)
    assert (
        len(tile_plan(BBox(0.0, 10.0, 0.0, 10.0), tile_deg=15.0, overlap_deg=0.0)) == 1
    )


def test_assemble_ignores_field_values_outside_tile_support() -> None:
    """NaN field values where a tile has zero weight must not poison the sum."""
    tiles = tile_plan(BBox(0.0, 30.0, 0.0, 15.0), tile_deg=15.0, overlap_deg=2.0)
    lon = np.array([1.0])  # deep in the west tile; east tile has w=0 here
    lat = np.array([7.5])
    fields = [np.array([2.0]), np.array([np.nan])]
    out = assemble(tiles, fields, lon, lat)
    np.testing.assert_allclose(out, 2.0, atol=_TOL)


def test_assemble_refuses_mismatched_inputs() -> None:
    """Tile/field count mismatch raises, never silently zips short."""
    tiles = tile_plan(BBox(0.0, 30.0, 0.0, 15.0), tile_deg=15.0, overlap_deg=2.0)
    with pytest.raises((ValueError, TypeError)):
        assemble(tiles, [np.zeros(1)], np.zeros(1), np.zeros(1))
