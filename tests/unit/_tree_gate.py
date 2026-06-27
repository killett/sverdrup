"""Shared Stage-B gate harness: real solved tiles + dense global reference + per-edge metrics.

Used by both the Task-8 oracles (fast, well-conditioned 2x2) and the Task-9 gate. Builds genuinely
real ``MaternGMRF``-solved tiles (NOT hand-stubbed fields) and the matching dense global posterior so
joint covariance can be scored per adjacency edge against ground truth.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np

from sverdrup.core.geometry import Tile, Window
from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider, ParameterProvider
from sverdrup.distributions.blend import BlendInput, partition_weights
from sverdrup.distributions.coherent import (
    GmrfKrigingSolve,
    GmrfTreeKrigingSolve,
    NoiseSpec,
    _max_overlap_spanning_tree,
    _node_keys,
    _support_points,
    _tile_adjacency,
)
from sverdrup.distributions.persisted import PrecisionDistribution, PrecisionFields
from sverdrup.distributions.reduction import GMRFPrecisionReduction
from sverdrup.methods.gmrf import MaternGMRF

_NOISE = NoiseSpec(method="gmrf", params_key="p", lattice_step=0.5)
_DEFAULT = ConstantProvider(
    {"range": 300.0, "variance": 0.05, "temporal_taper_scale": 5.0}
)
_T = 2.0

_Win = tuple[tuple[float, float], tuple[float, float]]
_Quad = tuple[np.ndarray, np.ndarray, float, _Win, _Win]


def _scattered_obs() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A deterministic 4x4 lattice of obs spread across 0..9 (so every halo shares seam data)."""
    coords = np.array([1.0, 3.5, 6.0, 8.5])
    lon, lat = np.meshgrid(coords, coords)
    lon = lon.ravel()
    lat = lat.ravel()
    val = np.sin(0.7 * lon) + np.cos(0.5 * lat)  # deterministic, spatially varying
    return lon, lat, val


def _obs_in(lon: np.ndarray, lat: np.ndarray, val: np.ndarray, ext: _Win) -> ObsWindow:
    (lo_lon, hi_lon), (lo_lat, hi_lat) = ext
    m = (lon >= lo_lon) & (lon <= hi_lon) & (lat >= lo_lat) & (lat <= hi_lat)
    return ObsWindow.from_arrays(
        lon[m],
        lat[m],
        np.full(int(m.sum()), _T),
        val[m],
        DiagonalErrorModel(np.full(int(m.sum()), 1e-3)),
    )


class GateFixture:
    """A real-tile partition + its dense global reference + per-edge measurement helpers.

    Obs are a fixed lattice scattered across the whole domain; each tile solves the obs falling in
    its EXTENDED window (mirroring the pipeline's per-tile windowing), so adjacent tiles share seam
    data and their posteriors are mutually consistent — the regime the spanning-tree sweep targets.
    """

    def __init__(
        self,
        quads: list[_Quad],
        grid: GridSpec,
        prov: ParameterProvider,
    ) -> None:
        self.grid = grid
        self.prov = prov
        olon, olat, oval = _scattered_obs()
        self.parts = []
        for lon, lat, _val, core, ext in quads:
            tgrid = GridSpec.lonlat(lon, lat)
            obs = _obs_in(olon, olat, oval, ext)
            dist = MaternGMRF().solve(obs, tgrid, prov, _T)
            unit = GMRFPrecisionReduction().reduce(
                dist, tgrid.points(_T), None, rank=0, seed=3
            )
            pd = PrecisionDistribution(
                tgrid, cast(PrecisionFields, unit.base_fields), dist.provenance, _T
            )
            tile = Tile(
                Window(core[0], core[1], (0.0, 0.0)),
                Window(ext[0], ext[1], (0.0, 0.0)),
                tgrid,
            )
            self.parts.append(BlendInput(pd, tile))
        gdist = MaternGMRF().solve(
            ObsWindow.from_arrays(
                olon,
                olat,
                np.full(olon.size, _T),
                oval,
                DiagonalErrorModel(np.full(olon.size, 1e-3)),
            ),
            grid,
            prov,
            _T,
        )
        self.gop = (
            gdist.cov_op
        )  # single global-tile operator (the conservative reference)
        self.sig_g = np.asarray(np.linalg.inv(cast(Any, self.gop).q_post.toarray()))
        gp = grid.points(_T)
        self.key2g = {
            (round(gp[i, 0], 6), round(gp[i, 1], 6)): i for i in range(gp.shape[0])
        }
        self.pts = gp
        self.ny, self.nx = grid.shape

    def assert_fixture_integrity(self) -> None:
        """Each tile carries a populated posterior precision; adjacent tiles resolve shared nodes.

        Pins the property whose absence caused the prior_precision=None / stub-fixture rot: a future
        refactor that reintroduces a hand-stubbed (None-precision) fixture fails loudly here.
        """
        for p in self.parts:
            prec = cast(Any, p.distribution).fields.precision
            assert prec is not None and prec.shape[0] > 0
        adj = _tile_adjacency(self.parts)
        assert adj, "no usable tile adjacency — shared strip nodes did not resolve"
        for keys in adj.values():
            assert len(keys) > 0

    def tree(
        self,
    ) -> tuple[
        dict[int, int | None], list[int], set[tuple[int, int]], list[tuple[int, int]]
    ]:
        return _max_overlap_spanning_tree(_tile_adjacency(self.parts), len(self.parts))

    def _ensemble(self, driver: object, m: int, seed0: int = 0) -> np.ndarray:
        w = partition_weights([p.tile for p in self.parts], self.pts)
        rows = [
            cast(Any, driver).crossfaded_member(
                self.parts, self.pts, w, seed0 + mm, _NOISE
            )
            for mm in range(m)
        ]
        return np.stack(rows)

    def tree_samples(self, m: int = 1500) -> np.ndarray:
        return self._ensemble(GmrfTreeKrigingSolve(), m)

    def chain_samples(self, m: int = 1500) -> np.ndarray:
        """Sample draws from the CHAIN driver (the validated baseline)."""
        return self._ensemble(GmrfKrigingSolve(), m, seed0=5000)

    def ref_samples(self, m: int = 1500) -> np.ndarray:
        """Single global-tile unconditional ensemble — the conservative reference for direction."""
        return np.asarray(cast(Any, self.gop).posterior_sample(self.pts, 42, m))

    @staticmethod
    def cov(samples: np.ndarray) -> np.ndarray:
        return np.asarray(np.cov(samples.T))

    def _shared_gidx(self, i: int, j: int) -> np.ndarray:
        ki = set(_node_keys(_support_points(self.parts[i].distribution.grid, _T)))
        kj = set(_node_keys(_support_points(self.parts[j].distribution.grid, _T)))
        return np.array(sorted({self.key2g[k] for k in (ki & kj)}))

    def edge_relerr(self, emp: np.ndarray, i: int, j: int) -> float:
        """Joint-cov rel-err on the shared-node block of edge (i,j) vs the global reference."""
        gi = self._shared_gidx(i, j)
        blk = np.ix_(gi, gi)
        return float(
            np.linalg.norm(emp[blk] - self.sig_g[blk]) / np.linalg.norm(self.sig_g[blk])
        )

    def edge_dir_ratio(
        self, blend_s: np.ndarray, ref_s: np.ndarray, i: int, j: int
    ) -> float:
        """Median firstdifference variance ratio (blend / single-tile ref) over seam-adjacent pairs.

        The conservative-direction detector (sample-based, the proven ``test_gmrf_blend`` form): the
        derived quantity is the gradient across the seam (grid-adjacent shared nodes), the reference
        is the single global-tile ensemble (NOT the dense near-singular Σ, whose adjacent
        firstdifference is a numerically-degenerate difference of huge correlated values). The MEDIAN
        over kept pairs is gated, not the raw min: in the near-singular short-range regime an
        individual pair's fd variance ratio is noisy (a few collapse to ~0), but a *systematic* seam
        under-dispersion — the Phase-3 disease, which crushed the ratio to 0.45 everywhere — moves the
        median. A reference-variance floor drops the degenerate checkerboard pairs. Ratio < 1 means
        the blend is under-dispersed (overconfident) at the seam.
        """
        gi = self._shared_gidx(i, j)
        gp = self.grid.points(_T)
        ref_floor = 0.1 * float(np.var(ref_s))
        ratios = []
        for a in gi:
            for b in gi:
                if a < b:
                    dlon = abs(gp[a, 0] - gp[b, 0])
                    dlat = abs(gp[a, 1] - gp[b, 1])
                    adjacent = (dlon <= 1.0 + 1e-6 and dlat < 1e-6) or (
                        dlat <= 1.0 + 1e-6 and dlon < 1e-6
                    )
                    if not adjacent:
                        continue
                    var_ref = float(np.var(ref_s[:, a] - ref_s[:, b]))
                    if var_ref >= ref_floor:
                        ratios.append(
                            float(np.var(blend_s[:, a] - blend_s[:, b])) / var_ref
                        )
        return float(np.median(ratios)) if ratios else 1.0


def make_2x2(prov: ParameterProvider | None = None) -> GateFixture:
    """A real-solved 2x2 partition of one global 0..9 grid + dense reference (one interior corner).

    Tiles overlap by FOUR nodes (lon/lat 3..6) — a wide halo so the hand-forward conditioning is
    well-posed and the dropped-edge transitive residual at the corner is small (the real ``k·corr_len``
    halo regime; minimal 2-node overlaps starve the corner and inflate the residual).
    """
    p = prov or _DEFAULT
    lo, hi = np.arange(0.0, 7.0), np.arange(3.0, 10.0)
    quads = [
        (lo, lo, 1.0, ((0.0, 4.0), (0.0, 4.0)), ((0.0, 6.0), (0.0, 6.0))),
        (hi, lo, 2.0, ((5.0, 9.0), (0.0, 4.0)), ((3.0, 9.0), (0.0, 6.0))),
        (lo, hi, 3.0, ((0.0, 4.0), (5.0, 9.0)), ((0.0, 6.0), (3.0, 9.0))),
        (hi, hi, 4.0, ((5.0, 9.0), (5.0, 9.0)), ((3.0, 9.0), (3.0, 9.0))),
    ]
    grid = GridSpec.lonlat(np.arange(0.0, 10.0), np.arange(0.0, 10.0))
    return GateFixture(quads, grid, p)


def make_chain(prov: ParameterProvider | None = None) -> GateFixture:
    """A real-solved 3-tile lon CHAIN over one global 0..9 grid (the chain-baseline reference).

    Same 4-node overlap regime as :func:`make_2x2` so the baseline is comparable.
    """
    p = prov or _DEFAULT
    lat = np.arange(0.0, 10.0)
    quads = [
        (
            np.arange(0.0, 6.0),
            lat,
            1.0,
            ((0.0, 3.0), (0.0, 9.0)),
            ((0.0, 5.0), (0.0, 9.0)),
        ),
        (
            np.arange(2.0, 8.0),
            lat,
            2.0,
            ((4.0, 5.0), (0.0, 9.0)),
            ((2.0, 7.0), (0.0, 9.0)),
        ),
        (
            np.arange(4.0, 10.0),
            lat,
            3.0,
            ((6.0, 9.0), (0.0, 9.0)),
            ((4.0, 9.0), (0.0, 9.0)),
        ),
    ]
    grid = GridSpec.lonlat(np.arange(0.0, 10.0), lat)
    return GateFixture(quads, grid, p)
