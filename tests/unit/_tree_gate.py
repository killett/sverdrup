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

    def __init__(self, parts: list[BlendInput], grid: GridSpec, gop: object) -> None:
        self.grid = grid
        self.parts = parts
        self.gop = gop  # single global-tile operator (the conservative reference)
        self.sig_g = np.asarray(np.linalg.inv(cast(Any, gop).q_post.toarray()))
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
        return _max_overlap_spanning_tree(
            _tile_adjacency(self.parts),
            len(self.parts),
        )

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

    def matched_chain_edge_baseline(
        self,
        tree_edges: set[tuple[int, int]],
        parent: dict[int, int | None],
        m: int = 1200,
    ) -> float:
        """Per-tile CONDITIONING-MATCHED chain baseline: max over tree edges of the 2-tile chain
        edge residual for that ``(parent, child)`` pair.

        The honest reference for assertion (1): each tree edge conditions a specific child tile, so
        compare its residual against the residual the plain CHAIN incurs conditioning that SAME tile
        at its SAME eigmin — a near-singular tile is gated against a near-singular tile's chain cost,
        not against an easier well-conditioned chain. ``tree_edge == chain_edge`` at equal
        conditioning, so a shallow eigmin-rooted tree matches this with equality; a multi-hop tree
        whose child is conditioned on an already-corrected parent would exceed it (the real defect
        this gate draws the line at).
        """
        worst = 0.0
        for a, b in tree_edges:
            child = b if parent.get(b) == a else a
            par = a if child == b else b
            parts = [self.parts[par], self.parts[child]]
            w = partition_weights([x.tile for x in parts], self.pts)
            s = np.stack(
                [
                    GmrfKrigingSolve().crossfaded_member(parts, self.pts, w, k, _NOISE)
                    for k in range(m)
                ]
            )
            gi = self._shared_gidx(par, child)
            blk = np.ix_(gi, gi)
            emp = np.cov(s.T)
            worst = max(
                worst,
                float(
                    np.linalg.norm(emp[blk] - self.sig_g[blk])
                    / np.linalg.norm(self.sig_g[blk])
                ),
            )
        return worst

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

    def sigma_contract(self) -> np.ndarray:
        """Reported marginal std field (Σ_i w_i σ_i) over output points."""
        w = partition_weights([p.tile for p in self.parts], self.pts)  # (T, n)
        sig = np.zeros((len(self.parts), self.pts.shape[0]))
        for i, p in enumerate(self.parts):
            mv = np.ravel(cast(Any, p.distribution).marginal_variance())
            for nn, k in enumerate(
                _node_keys(_support_points(p.distribution.grid, _T))
            ):
                g = self.key2g.get((round(k[0], 6), round(k[1], 6)))
                if g is not None:
                    sig[i, g] = np.sqrt(max(float(mv[nn]), 0.0))
        return np.asarray((w * sig).sum(axis=0))

    def marginal_contract_ratios(self, samples: np.ndarray) -> np.ndarray:
        """sample variance / (Σwσ)² at seam nodes with non-trivial reported variance.

        The "non-trivial" floor is RELATIVE to the seam's own variance scale (1e-3 of the
        median reported contract), not an absolute constant. The GMRF prior marginal
        variance is now correctly normalised to ≈τ (it was ~10³× inflated by a missing
        SPDE ``1/(4πκ²·A_cell)`` normalisation in ``matern_precision``); an absolute floor
        calibrated to that inflated scale would wrongly empty the seam set. The ratio
        ``sv/contract`` is scale-invariant under the per-node normalisation, so this
        selection — and the strict-min it feeds — is unchanged; only the filter scale moved.
        """
        contract = self.sigma_contract() ** 2
        sv = samples.var(axis=0)
        adj = _tile_adjacency(self.parts)
        seam = sorted({int(x) for (i, j) in adj for x in self._shared_gidx(i, j)})
        seam_contract = np.array([contract[g] for g in seam])
        floor = 1e-3 * float(np.median(seam_contract)) if seam_contract.size else 0.0
        return np.array([sv[g] / contract[g] for g in seam if contract[g] > floor])

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


def _build(quads: list[_Quad], grid: GridSpec, prov: ParameterProvider) -> GateFixture:
    """Solve each quad (obs windowed to its extended window) + the global reference."""
    olon, olat, oval = _scattered_obs()
    parts = []
    for lon, lat, _val, core, ext in quads:
        tgrid = GridSpec.lonlat(lon, lat)
        dist = MaternGMRF().solve(_obs_in(olon, olat, oval, ext), tgrid, prov, _T)
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
        parts.append(BlendInput(pd, tile))
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
    return GateFixture(parts, grid, gdist.cov_op)


def make_2x2(prov: ParameterProvider | None = None) -> GateFixture:
    """A real-solved 2x2 partition of one global 0..9 grid + dense reference (one interior corner).

    Tiles overlap by FOUR nodes (lon/lat 3..6) — a wide halo so the hand-forward conditioning is
    well-posed and the dropped-edge transitive residual at the corner is small (the real ``k·corr_len``
    halo regime; minimal 2-node overlaps starve the corner and inflate the residual).
    """
    lo, hi = np.arange(0.0, 7.0), np.arange(3.0, 10.0)
    quads: list[_Quad] = [
        (lo, lo, 1.0, ((0.0, 4.0), (0.0, 4.0)), ((0.0, 6.0), (0.0, 6.0))),
        (hi, lo, 2.0, ((5.0, 9.0), (0.0, 4.0)), ((3.0, 9.0), (0.0, 6.0))),
        (lo, hi, 3.0, ((0.0, 4.0), (5.0, 9.0)), ((0.0, 6.0), (3.0, 9.0))),
        (hi, hi, 4.0, ((5.0, 9.0), (5.0, 9.0)), ((3.0, 9.0), (3.0, 9.0))),
    ]
    grid = GridSpec.lonlat(np.arange(0.0, 10.0), np.arange(0.0, 10.0))
    return _build(quads, grid, prov or _DEFAULT)


def make_chain(prov: ParameterProvider | None = None) -> GateFixture:
    """A real-solved 3-tile lon CHAIN over one global 0..9 grid (the chain-baseline reference).

    Same 4-node overlap regime as :func:`make_2x2` so the baseline is comparable.
    """
    lat = np.arange(0.0, 10.0)
    quads: list[_Quad] = [
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
    return _build(quads, grid, prov or _DEFAULT)


_NATL60_PARAMS = {"range": 300.0, "variance": 0.05, "temporal_taper_scale": 10.0}


class _LatVaryingRange:
    """Latitude-varying range field (nonstationary κ, C4') for the gate's nonstationary case."""

    def resolve(self, name: str, grid: GridSpec) -> object:
        if name == "range":
            _, lat = grid._lonlat_nodes()
            c = np.cos(np.deg2rad(lat))
            return np.asarray(100.0 + 700.0 * c)
        return _NATL60_PARAMS[name]

    def params_key(self) -> str:
        return "latrange(eq=800,pole=100)"


def make_natl60(
    n_lon: int,
    n_lat: int,
    nonstationary: bool = False,
    *,
    source: Any | None = None,
    lon_range: tuple[float, float] = (-64.0, -56.0),
    lat_range: tuple[float, float] = (34.0, 42.0),
) -> GateFixture:
    """Real natl60_tiny tiles (the near-singular short-range regime) via the pipeline spine.

    The decisive Stage-B regime: sparse nadir obs leave the ``(κ²−Δ)²`` low-frequency mode
    under-determined (global ``Q_post`` eigmin ~1e-7), exactly where the synthesized-field sampler
    blew up 376x. ``nonstationary`` swaps in a latitude-varying κ field (C4').

    Args:
        source: Optional obs source override. Defaults to the committed ``natl60_tiny``
            FixtureSource. Pass a larger-domain FixtureSource to grow the domain at fixed
            tile core-size (constant-core tile-count sweep). OSSE ``_prepare`` never touches
            the ref grid, so an obs-only source with ``ref_path=None`` is sufficient.
        lon_range: Domain longitude extent. Grow it in lockstep with ``n_lon`` to hold the
            per-tile core span (``span / n_lon``) constant across a sweep.
        lat_range: Domain latitude extent. Grow it in lockstep with ``n_lat`` likewise.
    """
    from sverdrup.adapters.odc.fixtures import FixtureSource
    from sverdrup.application.pipeline import (
        PipelineInputs,
        _grid,
        _obs_in_window,
        _prepare,
    )
    from sverdrup.application.tiling import LonLatPartition, ScaleAwareHalo

    prov: ParameterProvider = cast(
        ParameterProvider,
        _LatVaryingRange() if nonstationary else ConstantProvider(_NATL60_PARAMS),
    )
    inp = PipelineInputs(
        mode="OSSE",
        method_name="gmrf",
        source=source
        or FixtureSource(
            "tests/fixtures/natl60_tiny.nc",
            ref_path="tests/fixtures/natl60_ref_tiny.nc",
        ),
        out_url="file:///tmp/x",
        lon_range=lon_range,
        lat_range=lat_range,
        grid_resolution_deg=1.0,
        time_range=(0.0, 5.0),
        output_times=[2.0],
        params=_NATL60_PARAMS,
        executor=cast(Any, None),
        rank=20,
    )
    grid = _grid(inp)
    obs = cast(Any, inp.source).window(
        lon_range=inp.lon_range, lat_range=inp.lat_range, time_range=inp.time_range
    )
    train, _, _ = _prepare(inp, obs)

    def tiles(nl: int, na: int) -> list[Any]:
        return list(
            LonLatPartition(
                nl,
                na,
                ScaleAwareHalo(1.0),
                ConstantProvider({"correlation_length": 300.0}),
                10.0,
            ).tiles(grid)
        )

    parts = []
    for tl in tiles(n_lon, n_lat):
        d = MaternGMRF().solve(
            _obs_in_window(train, tl.extended_window), tl.grid, prov, _T
        )
        u = GMRFPrecisionReduction().reduce(d, tl.grid.points(_T), None, rank=0, seed=3)
        parts.append(
            BlendInput(
                PrecisionDistribution(
                    tl.grid, cast(PrecisionFields, u.base_fields), d.provenance, _T
                ),
                tl,
            )
        )
    gtl = tiles(1, 1)[0]
    gop = (
        MaternGMRF()
        .solve(_obs_in_window(train, gtl.extended_window), grid, prov, _T)
        .cov_op
    )
    return GateFixture(parts, grid, gop)


def _scattered_obs_over(
    lon: np.ndarray, lat: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A deterministic obs lattice spanning the domain so every tile has seam data."""
    glon, glat = np.meshgrid(
        np.linspace(lon[0] + 1, lon[-1] - 1, 12),
        np.linspace(lat[0] + 1, lat[-1] - 1, 6),
    )
    olon, olat = glon.ravel(), glat.ravel()
    oval = np.sin(0.3 * olon) + np.cos(0.4 * olat)
    return olon, olat, oval


def make_grid_diagonal(n_lon: int, n_lat: int, range_km: float = 150.0) -> GateFixture:
    """A real-solved n_lon x n_lat partition with GRID+DIAGONAL adjacency (not K_n).

    Larger domain + short-enough range so each tile's extended window overlaps only its
    grid/diagonal neighbours (maxdeg ~5-8), unlike the 8 deg / K_n natl60 fixtures. ``range_km``
    is swept by the certification gate (short range -> more near-improper).
    """
    lon = np.arange(0.0, 36.0)
    lat = np.arange(30.0, 42.0)
    grid = GridSpec.lonlat(lon, lat)
    from sverdrup.application.tiling import LonLatPartition, ScaleAwareHalo

    prov = ConstantProvider(
        {"range": range_km, "variance": 0.05, "temporal_taper_scale": 10.0}
    )
    tiles = list(
        LonLatPartition(
            n_lon,
            n_lat,
            ScaleAwareHalo(1.0),
            ConstantProvider({"correlation_length": range_km}),
            10.0,
        ).tiles(grid)
    )
    olon, olat, oval = _scattered_obs_over(lon, lat)
    parts = []
    for tl in tiles:
        d = MaternGMRF().solve(
            _obs_in(
                olon,
                olat,
                oval,
                (tl.extended_window.lon_range, tl.extended_window.lat_range),
            ),
            tl.grid,
            prov,
            _T,
        )
        u = GMRFPrecisionReduction().reduce(d, tl.grid.points(_T), None, rank=0, seed=3)
        parts.append(
            BlendInput(
                PrecisionDistribution(
                    tl.grid, cast(PrecisionFields, u.base_fields), d.provenance, _T
                ),
                tl,
            )
        )
    gop = (
        MaternGMRF()
        .solve(
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
        .cov_op
    )
    return GateFixture(parts, grid, gop)
