"""Tests for sverdrup.application.calibration.regions.

TDD red phase — written before implementation.
Each test names the concrete bug it would catch.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LON_MID = 300.0
LAT_MID = 38.0


def _make_synthetic_mask(cells: list[tuple[int, int]]) -> np.ndarray:
    """Return a (5,5) bool array with True at the listed (row, col) pairs."""
    m = np.zeros((5, 5), dtype=bool)
    for r, c in cells:
        m[r, c] = True
    return m


# ---------------------------------------------------------------------------
# cell_index edge conventions
# Bug family: wrong searchsorted side or missing clip → wrong cell assignment.
# ---------------------------------------------------------------------------


class TestCellIndex:
    """cell_index(lon, lat) → (row, col), searchsorted-right + clip."""

    def test_interior_edge_lon_goes_right(self) -> None:
        """Point exactly on interior lon edge (e.g. 297) goes to the HIGHER col.

        Bug caught: using side='left' would place lon=297 in col 0 (cell 295-297)
        instead of col 1 (cell 297-299).
        """
        from sverdrup.application.calibration.regions import cell_index

        row, col = cell_index(np.array([297.0]), np.array([34.0]))
        # lon=297 is the right edge of cell 0 and left edge of cell 1;
        # searchsorted-right puts it in cell 1.
        assert int(col[0]) == 1, f"Expected col=1 for lon=297, got {col[0]}"

    def test_interior_edge_lat_goes_upper(self) -> None:
        """Point exactly on interior lat edge (e.g. 35) goes to the HIGHER row.

        Bug caught: using side='left' would place lat=35 in row 0 instead of row 1.
        """
        from sverdrup.application.calibration.regions import cell_index

        row, col = cell_index(np.array([296.0]), np.array([35.0]))
        assert int(row[0]) == 1, f"Expected row=1 for lat=35, got {row[0]}"

    def test_upper_bound_lon_clips_to_last_cell(self) -> None:
        """Point at lon=305 (upper domain boundary) clips into col=4, not 5.

        Bug caught: missing clip() would return col=5, causing array out-of-bounds
        or silent wrong-cell assignment.
        """
        from sverdrup.application.calibration.regions import cell_index

        row, col = cell_index(np.array([305.0]), np.array([36.0]))
        assert int(col[0]) == 4, f"Expected col=4 for lon=305, got {col[0]}"

    def test_upper_bound_lat_clips_to_last_cell(self) -> None:
        """Point at lat=43 (upper domain boundary) clips into row=4, not 5.

        Bug caught: missing clip() would return row=5, causing array out-of-bounds.
        """
        from sverdrup.application.calibration.regions import cell_index

        row, col = cell_index(np.array([298.0]), np.array([43.0]))
        assert int(row[0]) == 4, f"Expected row=4 for lat=43, got {row[0]}"

    def test_interior_point(self) -> None:
        """A strictly interior point is assigned to the expected cell.

        Expected value derived by hand: lon=296 is in [295,297) → col=0;
        lat=34 is in [33,35) → row=0.
        Bug caught: off-by-one in edge arrays or wrong arithmetic.
        """
        from sverdrup.application.calibration.regions import cell_index

        row, col = cell_index(np.array([296.0]), np.array([34.0]))
        assert int(row[0]) == 0
        assert int(col[0]) == 0


# ---------------------------------------------------------------------------
# Quadrant boundary convention
# Bug family: > vs >= for the east/north split.
# ---------------------------------------------------------------------------


class TestQuadrantOf:
    """quadrant_of(lon, lat) → label string from {SW, SE, NW, NE}."""

    def test_lon_eq_300_is_east(self) -> None:
        """lon==300 is East (SE or NE), per the shipped >= convention.

        Bug caught: using > instead of >= would assign lon=300 to the West half,
        disagreeing with diag_stage_b_localized_calibration.py lines 62-65.
        """
        from sverdrup.application.calibration.regions import quadrant_of

        label = quadrant_of(300.0, 34.0)  # lat<38 → South
        assert label == "SE", f"Expected SE for lon=300 lat=34, got {label!r}"

    def test_lat_eq_38_is_north(self) -> None:
        """lat==38 is North (NW or NE), per the shipped >= convention.

        Bug caught: using > instead of >= would assign lat=38 to the South half.
        """
        from sverdrup.application.calibration.regions import quadrant_of

        label = quadrant_of(298.0, 38.0)  # lon<300 → West
        assert label == "NW", f"Expected NW for lon=298 lat=38, got {label!r}"

    def test_ne_corner(self) -> None:
        """lon>=300 AND lat>=38 → NE.

        Bug caught: swapped lon/lat split or wrong constant would misclassify.
        """
        from sverdrup.application.calibration.regions import quadrant_of

        assert quadrant_of(302.0, 40.0) == "NE"

    def test_sw_interior(self) -> None:
        """lon<300 AND lat<38 → SW.

        Bug caught: inverted conditions would return NE instead of SW.
        """
        from sverdrup.application.calibration.regions import quadrant_of

        assert quadrant_of(297.0, 35.0) == "SW"


# ---------------------------------------------------------------------------
# Largest 4-connected component selection
# Bug family: wrong connectivity, not selecting largest, off-by-label.
# ---------------------------------------------------------------------------


class TestLargestComponent:
    """largest_4connected_component(mask) → bool mask, only largest survives."""

    def test_larger_component_survives(self) -> None:
        """With two components, the larger (3 cells) survives; the 1-cell island does not.

        Bug caught: returning all True cells, or returning smallest component,
        would include the island.
        Layout (row=0 top):
          . . . . .
          . . . . .
          . . . . .
          X . . . Y   row=3: col0 = component A, col4 = component B (island)
          X X . . .   row=4: col0,col1 = component A
        A has 3 cells (4-connected); B has 1 cell.
        """
        from sverdrup.application.calibration.regions import (
            largest_4connected_component,
        )

        mask = _make_synthetic_mask([(3, 0), (4, 0), (4, 1), (3, 4)])
        result = largest_4connected_component(mask)
        assert result[3, 0], "row=3,col=0 (component A) should survive"
        assert result[4, 0], "row=4,col=0 (component A) should survive"
        assert result[4, 1], "row=4,col=1 (component A) should survive"
        assert not result[3, 4], "row=3,col=4 (island B) should NOT survive"
        assert int(result.sum()) == 3, f"Expected 3 cells, got {result.sum()}"

    def test_diagonal_does_not_connect(self) -> None:
        """Two cells touching only diagonally are NOT in the same component.

        Bug caught: using scipy default 8-connectivity (full structure) instead
        of the cross structure [[0,1,0],[1,1,1],[0,1,0]] would merge them.
        Layout:
          . . . . .
          . . . . .
          . X . . .   row=2,col=1
          . . X . .   row=3,col=2  (diagonal neighbor of above)
          . . . . .
        With 4-connectivity, these are two separate 1-cell components. The
        function must return only one of them (the first by label index).
        """
        from sverdrup.application.calibration.regions import (
            largest_4connected_component,
        )

        mask = _make_synthetic_mask([(2, 1), (3, 2)])
        result = largest_4connected_component(mask)
        # Two components of equal size: tie-break = lowest label (first found).
        # Either way, only one cell should be True.
        assert int(result.sum()) == 1, (
            f"Diagonal cells must NOT be 4-connected; expected 1 True cell, got {result.sum()}"
        )

    def test_single_component_returns_itself(self) -> None:
        """A single 4-connected component is returned unchanged.

        Bug caught: off-by-one in component labeling that drops the only component.
        """
        from sverdrup.application.calibration.regions import (
            largest_4connected_component,
        )

        cells = [(1, 1), (1, 2), (2, 2)]
        mask = _make_synthetic_mask(cells)
        result = largest_4connected_component(mask)
        assert int(result.sum()) == 3
        for r, c in cells:
            assert result[r, c]

    def test_mask_determinism(self) -> None:
        """Same input array → same output (no random seed dependence).

        Bug caught: any non-deterministic tie-breaking or time-dependent
        logic would produce different outputs on repeated calls.
        """
        from sverdrup.application.calibration.regions import (
            largest_4connected_component,
        )

        mask = _make_synthetic_mask([(0, 0), (1, 0), (4, 4), (3, 4)])
        result_a = largest_4connected_component(mask)
        result_b = largest_4connected_component(mask)
        np.testing.assert_array_equal(result_a, result_b)


# ---------------------------------------------------------------------------
# evaluation_masks
# Bug family: wrong key set, aggregate not being union, jet_core excluded from quads.
# ---------------------------------------------------------------------------


class TestEvaluationMasks:
    """evaluation_masks(lon, lat, mask) → dict with 6 evaluation class masks."""

    def _make_inputs(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return 25 cell-centroid lon/lat and a simple jet_core mask."""
        lon_centers = np.repeat(np.arange(296.0, 305.0, 2.0), 5)  # 5 lons × 5 lats
        lat_centers = np.tile(np.arange(34.0, 43.0, 2.0), 5)
        # Mark 3 cells as jet_core (row=2,col=2 region ~ lon=300,lat=38)
        n = len(lon_centers)
        jet_mask_flat = np.zeros(n, dtype=bool)
        jet_mask_flat[:3] = True  # arbitrary 3 points
        return lon_centers, lat_centers, jet_mask_flat

    def test_exactly_6_keys(self) -> None:
        """evaluation_masks returns exactly the 6 keys: 4 quadrants + jet_core + aggregate.

        Bug caught: missing or adding a key would break callers that
        enumerate evaluation classes.
        """
        from sverdrup.application.calibration.regions import evaluation_masks

        lon, lat, jm = self._make_inputs()
        result = evaluation_masks(lon, lat, jm)
        expected_keys = {"SW", "SE", "NW", "NE", "jet_core", "aggregate"}
        assert set(result.keys()) == expected_keys, f"Wrong keys: {set(result.keys())}"

    def test_aggregate_is_union_of_quadrants(self) -> None:
        """aggregate mask == OR of all four quadrant masks (not intersection, not all-True).

        Bug caught: if aggregate were computed as all-points or as intersection,
        it would not equal the union (which should be all points in this domain).
        """
        from sverdrup.application.calibration.regions import evaluation_masks

        lon, lat, jm = self._make_inputs()
        result = evaluation_masks(lon, lat, jm)
        union = result["SW"] | result["SE"] | result["NW"] | result["NE"]
        np.testing.assert_array_equal(
            result["aggregate"],
            union,
            err_msg="aggregate must equal the union of four quadrant masks",
        )

    def test_jet_core_overlaps_quadrants(self) -> None:
        """jet_core evaluation mask overlaps quadrant evaluation masks (NOT disjoint).

        Bug caught: if evaluation_masks subtracted jet_core from quadrant masks
        (confusing evaluation classes with fit_partition), jet_core ∩ quadrant
        would be empty — wrong for the evaluation use case.
        """
        from sverdrup.application.calibration.regions import evaluation_masks

        # Use a domain where we know some jet_core points are in SW quadrant:
        # SW = lon<300 & lat<38 → lons 296,298 × lats 34,36
        lons = np.array([296.0, 296.0, 298.0, 302.0])
        lats = np.array([34.0, 34.0, 36.0, 40.0])
        # Mark first 3 points (all SW) as jet_core
        jet = np.array([True, True, True, False])
        result = evaluation_masks(lons, lats, jet)
        # Points 0,1,2 are SW and jet_core → both masks should be True for them
        assert result["SW"][0], "Point 0 (SW, jet_core) should appear in SW eval mask"
        assert result["jet_core"][0], (
            "Point 0 (SW, jet_core) should appear in jet_core eval mask"
        )

    def test_quadrant_assignment_consistent_with_convention(self) -> None:
        """lon=300,lat=38 → NE in evaluation_masks (>=300 East, >=38 North).

        Bug caught: if evaluation_masks used a different split than quadrant_of(),
        a point at the boundary would be in the wrong quadrant.
        """
        from sverdrup.application.calibration.regions import evaluation_masks

        lons = np.array([300.0])
        lats = np.array([38.0])
        jet = np.array([False])
        result = evaluation_masks(lons, lats, jet)
        assert result["NE"][0], "lon=300, lat=38 should be in NE evaluation mask"
        assert not result["NW"][0]
        assert not result["SE"][0]
        assert not result["SW"][0]


# ---------------------------------------------------------------------------
# fit_partition
# Bug family: not a partition (overlap or gap), wrong labels, jet not separate.
# ---------------------------------------------------------------------------


class TestFitPartition:
    """fit_partition(lon, lat, mask) → label array; each point exactly one label."""

    def test_partition_is_exhaustive_and_disjoint(self) -> None:
        """Every point gets exactly one label (no gaps, no overlaps).

        Bug caught: if a jet_core point were also labeled SW (overlap), or if a
        jet_core point were labeled nothing (gap), the sum-per-point would not be 1.
        """
        from sverdrup.application.calibration.regions import fit_partition

        rng = np.random.default_rng(42)
        n = 100
        lons = rng.uniform(295.0, 305.0, n)
        lats = rng.uniform(33.0, 43.0, n)
        # Mark ~20% as jet
        jet = rng.random(n) < 0.2

        labels = fit_partition(lons, lats, jet)
        assert labels.shape == (n,), f"Expected shape ({n},), got {labels.shape}"

        valid = {"SW", "SE", "NW", "NE", "JET"}
        for i, lbl in enumerate(labels):
            assert lbl in valid, f"Point {i} has invalid label {lbl!r}"

        # Each point must appear in exactly one label class (true partition check)
        # Count labels per point — with string array, just verify no overlap
        jet_indices = np.where(jet)[0]
        nonjet_indices = np.where(~jet)[0]
        for i in jet_indices:
            assert labels[i] == "JET", (
                f"jet point {i} should be labeled JET, got {labels[i]!r}"
            )
        for i in nonjet_indices:
            assert labels[i] in {"SW", "SE", "NW", "NE"}, (
                f"non-jet point {i} labeled {labels[i]!r}, expected quadrant"
            )

    def test_fit_partition_labels_only_valid(self) -> None:
        """fit_partition returns only labels from {SW, SE, NW, NE, JET}.

        Bug caught: a typo like 'JetCore' or '' (empty) would pass type checking
        but break downstream dispatch code that matches exact label strings.
        """
        from sverdrup.application.calibration.regions import fit_partition

        lons = np.array([296.0, 298.0, 302.0, 304.0, 300.0])
        lats = np.array([34.0, 40.0, 36.0, 40.0, 38.0])
        jet = np.array([False, False, False, False, True])

        labels = fit_partition(lons, lats, jet)
        valid = {"SW", "SE", "NW", "NE", "JET"}
        for lbl in labels:
            assert lbl in valid, f"Invalid label {lbl!r}"

    def test_fit_partition_jet_subtracts_from_quadrants(self) -> None:
        """A jet_core point at lon=302,lat=40 gets JET, not NE.

        Bug caught: if fit_partition did not subtract jet cells from quadrants,
        the point would get NE (wrong — it should be JET in the fit partition).
        """
        from sverdrup.application.calibration.regions import fit_partition

        lons = np.array([302.0, 296.0])
        lats = np.array([40.0, 34.0])
        jet = np.array([True, False])  # first point is jet

        labels = fit_partition(lons, lats, jet)
        assert labels[0] == "JET", f"Expected JET, got {labels[0]!r}"
        assert labels[1] == "SW", f"Expected SW, got {labels[1]!r}"
