"""Generalized fit harness for per-product spatial uncertainty calibration.

Extracted from ``scripts/phase8_fit_run.py`` (Phase 9, Task 4).  The harness
runs the exact Phase-8 fit sequence parameterized by a :class:`ProductDescriptor`,
so every product (MIOST, OI, …) goes through the same pre-registered pipeline.

Pipeline:
    load_track(desc, scope) -> measure_rho(trk) -> run_family(t_folds)
    -> run_family(s_folds) -> folds.select() -> refit_winner() -> build_evidence()

Seed scoping: the fold-seed tuple is a **descriptor field**, not a module
constant.  MIOST carries the FROZEN Phase-8 tuple ``("miost", "phase8",
"s-folds")``; new products get product-scoped tuples.  The harness uses
``derive_seed(*descriptor.fold_seed_tuple, salt)`` so that MIOST bit-reproduces
Phase-8 evidence while OI has its own seed lineage.

c2 is NEVER imported or loaded in this module.  Provenance guard
(``assert_scored_not_assimilated``) is asserted on every map-to-track call.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr

from sverdrup.application.calibration import folds as F
from sverdrup.application.calibration import likelihood as L
from sverdrup.application.calibration import regions as R
from sverdrup.application.calibration.constants import (
    CLIP_PAD,
    COVERAGE_TARGET,
    COVERAGE_TOL,
    MIN_N_EFF,
    S_STAR,
    SIGMA_OBS2,
    TIE_BAND,
)
from sverdrup.core.seeding import derive_seed
from sverdrup.distributions.calibration import (
    CalibrationField,
    ClipSpec,
    CovariateCalibration,
    PiecewiseCalibration,
    PolyCalibration,
    ScalarCalibration,
)

# ---------------------------------------------------------------------------
# ProductDescriptor
# ---------------------------------------------------------------------------

_DATA_ROOT = Path("data/2021a_ssh_mapping_ose/ours")
_SCOPE_FIX = Path("tests/validation/fixtures/stage_a_scope.json")


@dataclass(frozen=True)
class ProductDescriptor:
    """Frozen descriptor carrying all product-specific paths and identifiers.

    Attributes:
        product_id: Short identifier, e.g. ``"miost"`` or ``"oi"``. Must be
            non-empty.
        mean_maps: Path to the per-product mean NetCDF maps.
        var_maps: Path to the per-product variance NetCDF maps.
        scope_config: Path to the JSON scope config (track source + time bounds).
        mask_artifact: Path to the per-product jet-core mask JSON artifact.
        evidence_key: Dot-separated key under which evidence is stored, e.g.
            ``"phase9.miost.fit_run"``. Must start with ``"phase"``.
        field_artifact: Path to the output field JSON artifact.
        fold_seed_tuple: 3-element tuple of strings threaded into
            ``derive_seed(*fold_seed_tuple, salt)`` to generate S-fold layouts.
            MIOST carries the FROZEN Phase-8 tuple ``("miost", "phase8",
            "s-folds")`` so that leaf-identical regression is satisfiable.
        covariate_promoted: Whether the covariate lane is promoted for this
            product (True = run lanes 0/A/B/covariate; False = 0/A/B only).
            Recorded in evidence.
    """

    product_id: str
    mean_maps: Path
    var_maps: Path
    scope_config: Path
    mask_artifact: Path
    evidence_key: str
    field_artifact: Path
    fold_seed_tuple: tuple[str, str, str]
    covariate_promoted: bool = True

    def __post_init__(self) -> None:
        """Validate field types and invariants.

        Raises:
            TypeError: If ``mean_maps``, ``var_maps``, ``scope_config``,
                ``mask_artifact``, or ``field_artifact`` are not :class:`Path`
                instances.
            ValueError: If ``product_id`` is empty, ``evidence_key`` does not
                start with ``"phase"``, or ``fold_seed_tuple`` is not a 3-tuple
                of strings.
        """
        for attr in (
            "mean_maps",
            "var_maps",
            "scope_config",
            "mask_artifact",
            "field_artifact",
        ):
            val = getattr(self, attr)
            if not isinstance(val, Path):
                raise TypeError(
                    f"ProductDescriptor.{attr} must be a Path, got {type(val).__name__!r}"
                )
        if not self.product_id:
            raise ValueError("ProductDescriptor.product_id must be non-empty")
        if not self.evidence_key.startswith("phase"):
            raise ValueError(
                f"ProductDescriptor.evidence_key must start with 'phase', "
                f"got {self.evidence_key!r}"
            )
        if (
            not isinstance(self.fold_seed_tuple, tuple)
            or len(self.fold_seed_tuple) != 3
            or not all(isinstance(s, str) for s in self.fold_seed_tuple)
        ):
            raise ValueError(
                "ProductDescriptor.fold_seed_tuple must be a 3-tuple of str, "
                f"got {self.fold_seed_tuple!r}"
            )


# ---------------------------------------------------------------------------
# Module-level descriptor constants
# ---------------------------------------------------------------------------

MIOST_DESCRIPTOR = ProductDescriptor(
    product_id="miost",
    mean_maps=_DATA_ROOT / "stage_b_mean_maps.nc",
    var_maps=_DATA_ROOT / "stage_b_var_maps.nc",
    scope_config=_SCOPE_FIX,
    mask_artifact=_DATA_ROOT / "phase8_jet_core_mask.json",
    evidence_key="phase9.miost.fit_run",
    field_artifact=_DATA_ROOT / "phase9_field_miost.json",
    fold_seed_tuple=("miost", "phase8", "s-folds"),  # FROZEN Phase-8 tuple
    covariate_promoted=True,
)

OI_DESCRIPTOR = ProductDescriptor(
    product_id="oi",
    mean_maps=_DATA_ROOT / "oi_mean_maps.nc",
    var_maps=_DATA_ROOT / "oi_var_maps.nc",
    scope_config=_SCOPE_FIX,
    mask_artifact=_DATA_ROOT / "phase9_jet_core_mask_oi.json",
    evidence_key="phase9.oi.fit_run",
    field_artifact=_DATA_ROOT / "phase9_field_oi.json",
    fold_seed_tuple=("oi", "phase9", "s-folds"),
    covariate_promoted=False,  # OI promotion TBD; default to no-covariate
)

# ---------------------------------------------------------------------------
# Module constants (pipeline internals)
# ---------------------------------------------------------------------------

EPOCH = np.datetime64("2017-01-01")
_FULL_TMIN, _FULL_TMAX = "2017-01-01", "2018-01-01"
_PASS_GAP_SEC = 60.0  # inter-pass gap threshold; along-track cadence ~1.08 s

_EVAL_REGIONS = ("SW", "SE", "NW", "NE", "jet_core", "aggregate")
_FIT_REGIONS = ("SW", "SE", "NW", "NE", "JET")

# The scalar record from the shipped scalar (Phase-8 spec §6 bar 3): worst SE.
_SCALAR_WORST_REGION = "SE"
_SCALAR_WORST_COVERAGE = 0.8267
_SCALAR_WORST_DEFICIT = 0.1440
_PHASE_PROMPT_RECORD = 0.69

# Phase-8 jet-core mask reference for Jaccard comparison (untracked by design).
_P8_JET_MASK_REF = _DATA_ROOT / "phase8_jet_core_mask.json"

# ---------------------------------------------------------------------------
# Thin pure glue (moved from phase8_fit_run.py — names kept)
# ---------------------------------------------------------------------------


def _norm_uv(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return normalised poly coordinates u=(lon-300)/5, v=(lat-38)/5."""
    u = (np.asarray(lon, float) - 300.0) / 5.0
    v = (np.asarray(lat, float) - 38.0) / 5.0
    return u, v


def _poly_design(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Return lane-B design matrix columns [1, v, v^2, u, u*v]."""
    u, v = _norm_uv(lon, lat)
    return np.column_stack([np.ones_like(u), v, v * v, u, u * v])


def _covariate_design(
    lon: np.ndarray, lat: np.ndarray, proxy: np.ndarray
) -> np.ndarray:
    """Return covariate-lane design [1, log proxy(cell(x))]."""
    row, col = R.cell_index(lon, lat)
    pv = np.asarray([proxy[int(r), int(c)] for r, c in zip(row, col, strict=True)])
    return np.column_stack([np.ones_like(pv, dtype=float), np.log(pv)])


def _pass_id(day: np.ndarray) -> np.ndarray:
    """Return a deterministic along-track pass id from the time ordering.

    The interp output is time-monotonic with a regular ~1.08 s cadence; a new
    pass starts wherever the gap to the previous point exceeds ``_PASS_GAP_SEC``.
    This is the pass grouping used for the ρ̂ along-track autocorrelation.
    """
    sec = np.asarray(day, float) * 86400.0
    gap = np.diff(sec) > _PASS_GAP_SEC
    return np.concatenate([[0], np.cumsum(gap)]).astype(int)


def _coverage_count(resid: np.ndarray, var_track: np.ndarray) -> tuple[int, int]:
    """Return (n_covered, n_total) at the 1σ band |resid| <= sqrt(var_track)."""
    band = np.sqrt(var_track)
    return int(np.count_nonzero(np.abs(resid) <= band)), int(resid.size)


def _gaussian_crps(resid: np.ndarray, var_track: np.ndarray) -> float:
    """Mean Gaussian CRPS closed form for zero-mean predictive N(0, var_track).

    CRPS(N(0,σ²), y) = σ·[ z(2Φ(z)-1) + 2φ(z) - 1/√π ], with z = y/σ.
    """
    sigma = np.sqrt(np.asarray(var_track, float))
    z = np.asarray(resid, float) / sigma
    phi = np.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
    cdf = 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2.0)))
    crps = sigma * (z * (2.0 * cdf - 1.0) + 2.0 * phi - 1.0 / math.sqrt(math.pi))
    return float(np.mean(crps))


def _var_track(
    cal: CalibrationField, lon: np.ndarray, lat: np.ndarray, v: np.ndarray
) -> np.ndarray:
    """Return s(x)·v + SIGMA_OBS2 for a calibration field on the track."""
    s = cal.sqrt_s_at(lon, lat) ** 2
    out: np.ndarray = s * np.asarray(v, float) + SIGMA_OBS2
    return out


# ---------------------------------------------------------------------------
# Track loader
# ---------------------------------------------------------------------------


class Track:
    """Loaded j3 track arrays after finite/positive-var masking."""

    def __init__(
        self,
        day: np.ndarray,
        lon: np.ndarray,
        lat: np.ndarray,
        resid: np.ndarray,
        v: np.ndarray,
        month: np.ndarray,
        pass_id: np.ndarray,
        labels: np.ndarray,
        jet_pts: np.ndarray,
    ) -> None:
        """Store per-point arrays; derive r2 and n from resid."""
        self.day = day
        self.lon = lon
        self.lat = lat
        self.resid = resid
        self.r2 = resid**2
        self.v = v
        self.month = month
        self.pass_id = pass_id
        self.labels = labels
        self.jet_pts = jet_pts
        self.n = int(resid.size)

    def eval_masks(self) -> dict[str, np.ndarray]:
        """Return the 6 pre-registered evaluation-class point masks."""
        return R.evaluation_masks(self.lon, self.lat, self.jet_pts)


def _jet_cell_mask(mask_artifact: Path) -> np.ndarray:
    """Load the (5,5) jet-core cell mask from a JSON artifact.

    Args:
        mask_artifact: Path to the jet-core mask JSON (``{"mask": ...}``).

    Returns:
        Boolean (5,5) ndarray; True = jet-core cell.
    """
    d = json.loads(mask_artifact.read_text())
    return np.asarray(d["mask"], dtype=bool)


def load_track(desc: ProductDescriptor, scope: str) -> Track:
    """Interp the product mean/var maps on the j3 track and build arrays.

    Uses the exact loaders, box, and raw-variance convention of
    ``scripts/diag_stage_b_localized_calibration.py``.  The scored map carries
    an assimilation provenance guard (``assert_scored_not_assimilated``).

    Args:
        desc: The :class:`ProductDescriptor` for the product being calibrated.
        scope: ``"dev"`` for the 12-day dev window (from scope_config);
            ``"full"`` for the full challenge year (2017-01-01 to 2018-01-01).

    Returns:
        A :class:`Track` with per-point day/lon/lat/resid/v/month/pass_id plus
        the fit-partition labels and per-point jet-core membership.
    """
    import sverdrup.validation.their_eval as te
    from sverdrup.validation.provenance_guard import assert_scored_not_assimilated

    cfg = json.loads(desc.scope_config.read_text())
    track = Path(cfg["val_track_path"])  # j3 validation track (c2 never loaded)
    assert_scored_not_assimilated(desc.mean_maps, track)
    assert_scored_not_assimilated(desc.var_maps, track)

    tmin, tmax = _FULL_TMIN, _FULL_TMAX
    if scope == "dev":
        tmin, tmax = cfg["time_min"], cfg["time_max"]

    te._prepare_imports()
    from src.mod_inout import read_l3_dataset
    from src.mod_interp import interp_on_alongtrack

    box = dict(
        lon_min=295.0,
        lon_max=305.0,
        lat_min=33.0,
        lat_max=43.0,
        time_min=tmin,
        time_max=tmax,
    )
    ds_at = read_l3_dataset(str(track), **box)
    t_a, lat_a, lon_a, ssh, mu = interp_on_alongtrack(
        str(desc.mean_maps), ds_at, is_circle=False, **box
    )
    _, _, _, _, var = interp_on_alongtrack(
        str(desc.var_maps), ds_at, is_circle=False, **box
    )
    ssh, mu, var = (np.asarray(a, float) for a in (ssh, mu, var))
    lat_a, lon_a = np.asarray(lat_a, float), np.asarray(lon_a, float)
    t_a = np.asarray(t_a)
    day = (t_a - EPOCH) / np.timedelta64(1, "D")
    ok = np.isfinite(ssh) & np.isfinite(mu) & np.isfinite(var) & (var > 0)

    day, lon, lat, resid, v = (
        np.asarray(a)[ok] for a in (day, lon_a, lat_a, ssh - mu, var)
    )
    month = np.array(
        [(EPOCH + np.timedelta64(int(d), "D")).astype("datetime64[M]") for d in day]
    )
    month = np.array([str(m)[5:7] for m in month])  # "01".."12"
    pid = _pass_id(day)

    jet_cells = _jet_cell_mask(desc.mask_artifact)
    row, col = R.cell_index(lon, lat)
    jet_pts = jet_cells[row, col]
    labels = R.fit_partition(lon, lat, jet_pts)

    return Track(day, lon, lat, resid, v, month, pid, labels, jet_pts)


# ---------------------------------------------------------------------------
# Lane fitting on a fit-mask, evaluation on a score-mask
# ---------------------------------------------------------------------------


def _fit_lane(
    name: str,
    trk: Track,
    fit: np.ndarray,
    proxy: np.ndarray,
    jet_mask: np.ndarray,
) -> CalibrationField:
    """Fit a calibration field of the given lane on the fit-masked subset.

    The clip bounds used here are wide (evidence anchors come from the FULL-j3
    refit, spec §9); per-fold fits are only ever used to score coverage, and
    lane values sit far inside so the clip is inert on the folds.

    Args:
        name: Lane name: ``"piecewise"``, ``"poly"``, or ``"covariate"``.
        trk: The loaded :class:`Track`.
        fit: Boolean mask selecting the fit-side points.
        proxy: (5,5) signal-variance proxy array from the product mean maps.
        jet_mask: (5,5) boolean jet-core mask.

    Returns:
        A fitted :class:`CalibrationField`.
    """
    lon, lat = trk.lon[fit], trk.lat[fit]
    r2, v = trk.r2[fit], trk.v[fit]
    wide = ClipSpec(lo_log_s=-20.0, hi_log_s=20.0)

    if name == "piecewise":
        labels = trk.labels[fit]
        by_region: dict[str, float] = {}
        for reg in _FIT_REGIONS:
            m = labels == reg
            if not m.any():
                by_region[reg] = math.log(S_STAR)
                continue
            by_region[reg] = L.fit_region_newton(r2[m], v[m]).log_s_hat
        return PiecewiseCalibration(
            lon_mid=R.LON_MID,
            lat_mid=R.LAT_MID,
            mask=tuple(tuple(bool(b) for b in row) for row in jet_mask),
            log_s_by_region=by_region,
            clip=wide,
            fit_id="phase8-fold-newton",
        )
    if name == "poly":
        theta, fit_id = L.fit_poly_lbfgsb(_poly_design(lon, lat), r2, v)
        return PolyCalibration(coeffs=tuple(theta), clip=wide, fit_id=fit_id)
    if name == "covariate":
        theta, fit_id = L.fit_poly_lbfgsb(_covariate_design(lon, lat, proxy), r2, v)
        a, b = float(theta[0]), float(theta[1])
        return CovariateCalibration(
            proxy_cells=tuple(tuple(float(x) for x in r) for r in proxy),
            a=a,
            b=b,
            clip=wide,
            fit_id=fit_id,
        )
    raise ValueError(f"unknown lane {name!r}")


def _lane0() -> ScalarCalibration:
    """Return the lane-0 control field: constant s* (evaluated, never fit)."""
    return ScalarCalibration(S_STAR)


def run_family(
    trk: Track,
    proxy: np.ndarray,
    fold_masks: list[tuple[np.ndarray, np.ndarray]],
    lanes: tuple[str, ...],
    jet_mask: np.ndarray,
) -> dict[str, float]:
    """Return per-lane pooled-worst-region deficit over a fold family.

    For each lane, fit on every fold's fit-mask, score held-out coverage at
    ``s(x)*v + SIGMA_OBS2`` per evaluation region, pool ``(n_cov, n_tot)`` across
    folds, then take the worst |coverage - target| over the pre-registered
    evaluation regions (:func:`folds.pooled_worst_region`).  Lane 0 is the
    constant-s* control, evaluated on the identical folds.

    Args:
        trk: The loaded :class:`Track`.
        proxy: (5,5) proxy array for the covariate lane.
        fold_masks: List of (fit_mask, score_mask) pairs from a fold family.
        lanes: Lane names to evaluate, e.g. ``("scalar", "piecewise", "poly")``.
        jet_mask: (5,5) boolean jet-core mask for piecewise lane construction.

    Returns:
        Dict mapping lane name to the pooled-worst-region coverage deficit.
    """
    out: dict[str, float] = {}
    for name in lanes:
        pooled: dict[str, list[int]] = {r: [0, 0] for r in _EVAL_REGIONS}
        for fit, score in fold_masks:
            if not fit.any() or not score.any():
                continue
            cal = (
                _lane0()
                if name == "scalar"
                else _fit_lane(name, trk, fit, proxy, jet_mask)
            )
            vt = _var_track(cal, trk.lon[score], trk.lat[score], trk.v[score])
            resid_s = trk.resid[score]
            masks = R.evaluation_masks(
                trk.lon[score], trk.lat[score], trk.jet_pts[score]
            )
            for reg in _EVAL_REGIONS:
                mm = masks[reg]
                if not mm.any():
                    continue
                nc, nt = _coverage_count(resid_s[mm], vt[mm])
                pooled[reg][0] += nc
                pooled[reg][1] += nt
        cov = {r: (pooled[r][0], pooled[r][1]) for r in _EVAL_REGIONS}
        worst, _table = F.pooled_worst_region(cov)
        out[name] = worst
    return out


# ---------------------------------------------------------------------------
# ρ̂ / n_eff / merge (measured ONCE on full j3 at frozen s*)
# ---------------------------------------------------------------------------


def measure_rho(trk: Track) -> dict[str, Any]:
    """Return the ρ̂ evidence record measured once on full j3 at frozen s*.

    Normalised residuals are z = resid / sqrt(s*·v + SIGMA_OBS2); ρ̂ and the
    inflation factor come from :func:`folds.rho_hat` grouped by along-track pass.

    Args:
        trk: The loaded :class:`Track`.

    Returns:
        Dict with keys ``rhos_used``, ``n_lags_retained``, ``inflation_factor``,
        ``n_passes``, ``frozen_s_star``, ``convention``.
    """
    vt = _var_track(_lane0(), trk.lon, trk.lat, trk.v)
    z = trk.resid / np.sqrt(vt)
    rhos, factor = F.rho_hat(z, trk.day, trk.pass_id)
    return {
        "rhos_used": [float(x) for x in rhos],
        "n_lags_retained": int(len(rhos)),
        "inflation_factor": float(factor),
        "n_passes": int(len(np.unique(trk.pass_id))),
        "frozen_s_star": S_STAR,
        "convention": "z = resid / sqrt(s*·v + SIGMA_OBS2); grouped by pass",
    }


def _n_eff_per_block(trk: Track, rhos: np.ndarray) -> dict[int, float]:
    """Return per-block n_eff using the single measured ρ̂ inflation factor."""
    block = np.asarray(R.cell_index(trk.lon, trk.lat))
    block = block[0] * 5 + block[1]
    out: dict[int, float] = {}
    for b in range(25):
        n = int(np.count_nonzero(block == b))
        out[b] = F.n_eff(float(n), rhos) if n else 0.0
    return out


# ---------------------------------------------------------------------------
# S-fold salt draw (re-draw while layout_respects_partition fails)
# ---------------------------------------------------------------------------


_S_FOLD_N_BLOCKS = 25
_S_FOLD_SIZES = (7, 6, 6, 6)  # matches folds._S_FOLD_SIZES (invariant)


def draw_s_layout(
    trk: Track, fold_seed_tuple: tuple[str, str, str]
) -> tuple[tuple[frozenset[int], ...], int, list[int]]:
    """Return (layout, final_salt, redraws) respecting the partition constraint.

    Uses ``derive_seed(*fold_seed_tuple, salt)`` so that each product has its own
    seed lineage.  MIOST's ``fold_seed_tuple = ("miost", "phase8", "s-folds")``
    exactly matches the Phase-8 ``S_FOLD_SEED_ARGS``, guaranteeing bit-identical
    reproduction of the Phase-8 evidence.

    Args:
        trk: The loaded :class:`Track`.
        fold_seed_tuple: 3-tuple of strings from the product descriptor.

    Returns:
        Tuple of (layout, final_salt, redraws_list).
    """
    salt = 0
    redraws: list[int] = []
    while True:
        seed = derive_seed(*fold_seed_tuple, salt)
        rng = np.random.default_rng(seed)
        perm = rng.permutation(_S_FOLD_N_BLOCKS)
        folds_out: list[frozenset[int]] = []
        start = 0
        for size in _S_FOLD_SIZES:
            folds_out.append(frozenset(int(b) for b in perm[start : start + size]))
            start += size
        layout = tuple(folds_out)
        if F.layout_respects_partition(trk.lon, trk.lat, trk.labels, layout):
            return layout, salt, redraws
        redraws.append(salt)
        salt += 1
        if salt > 1000:  # pragma: no cover - defensive
            raise RuntimeError("S-fold layout never respected partition")


# ---------------------------------------------------------------------------
# Winner refit on full j3 + clip bounds + safeguard
# ---------------------------------------------------------------------------


def _lane_a_log_s_range(trk: Track) -> tuple[float, float]:
    """Return (min, max) lane-A per-region MLE log-s over the 5 fit regions."""
    vals = []
    for reg in _FIT_REGIONS:
        m = trk.labels == reg
        if m.any():
            vals.append(L.fit_region_newton(trk.r2[m], trk.v[m]).log_s_hat)
    return (min(vals), max(vals))


def refit_winner(
    trk: Track, proxy: np.ndarray, winner_name: str, jet_mask: np.ndarray
) -> tuple[CalibrationField, ClipSpec]:
    """Refit the winning lane on ALL of j3 with evidence-anchored clip bounds.

    Clip [L, U] = lane-A per-region log-s range ± log(CLIP_PAD).  The refit runs
    the loud ``assert_beats_scalar`` safeguard (fitted NLL vs s*-constant NLL on
    full j3).

    Args:
        trk: The loaded :class:`Track`.
        proxy: (5,5) proxy array for the covariate lane.
        winner_name: Name of the winning lane (``"piecewise"``, ``"poly"``,
            or ``"covariate"``).
        jet_mask: (5,5) boolean jet-core mask for piecewise lane construction.

    Returns:
        Tuple of (fitted_field, clip_spec).
    """
    lo_r, hi_r = _lane_a_log_s_range(trk)
    pad = math.log(CLIP_PAD)
    clip = ClipSpec(lo_log_s=lo_r - pad, hi_log_s=hi_r + pad)

    if winner_name == "piecewise":
        by_region: dict[str, float] = {}
        for reg in _FIT_REGIONS:
            m = trk.labels == reg
            v = (
                L.fit_region_newton(trk.r2[m], trk.v[m]).log_s_hat
                if m.any()
                else math.log(S_STAR)
            )
            by_region[reg] = float(np.clip(v, clip.lo_log_s, clip.hi_log_s))
        cal: CalibrationField = PiecewiseCalibration(
            lon_mid=R.LON_MID,
            lat_mid=R.LAT_MID,
            mask=tuple(tuple(bool(b) for b in row) for row in jet_mask),
            log_s_by_region=by_region,
            clip=clip,
            fit_id="phase8-refit-newton",
        )
    elif winner_name == "poly":
        theta, fit_id = L.fit_poly_lbfgsb(_poly_design(trk.lon, trk.lat), trk.r2, trk.v)
        cal = PolyCalibration(coeffs=tuple(theta), clip=clip, fit_id=fit_id)
    elif winner_name == "covariate":
        theta, fit_id = L.fit_poly_lbfgsb(
            _covariate_design(trk.lon, trk.lat, proxy), trk.r2, trk.v
        )
        cal = CovariateCalibration(
            proxy_cells=tuple(tuple(float(x) for x in r) for r in proxy),
            a=float(theta[0]),
            b=float(theta[1]),
            clip=clip,
            fit_id=fit_id,
        )
    else:
        raise ValueError(f"unknown winner {winner_name!r}")

    # Safeguard: fitted NLL vs s*-constant NLL on full j3 (design = ones column).
    ones = np.ones((trk.n, 1))
    nll_star = L.nll(np.array([math.log(S_STAR)]), ones, trk.r2, trk.v)
    log_s_fit = np.log(cal.sqrt_s_at(trk.lon, trk.lat) ** 2)
    tot = np.exp(log_s_fit) * trk.v + SIGMA_OBS2
    nll_fit = float(0.5 * np.sum(np.log(tot) + trk.r2 / tot))
    L.assert_beats_scalar(nll_fit=nll_fit, nll_s_star=nll_star)

    return cal, clip


# ---------------------------------------------------------------------------
# Evidence blocks (spec §6)
# ---------------------------------------------------------------------------


def _region_coverage(cal: CalibrationField, trk: Track) -> dict[str, dict[str, float]]:
    """Return per-eval-region coverage + reduced chi2 for a field on full j3."""
    vt = _var_track(cal, trk.lon, trk.lat, trk.v)
    masks = trk.eval_masks()
    out: dict[str, dict[str, float]] = {}
    for reg, mm in masks.items():
        if not mm.any():
            continue
        nc, nt = _coverage_count(trk.resid[mm], vt[mm])
        out[reg] = {
            "n": nt,
            "coverage": nc / nt,
            "deficit": abs(nc / nt - COVERAGE_TARGET),
            "reduced_chi2": float(np.mean(trk.r2[mm] / vt[mm])),
        }
    return out


def _monthly_table(cal: CalibrationField, trk: Track) -> dict[str, dict[str, float]]:
    """Return per-month held-out fitted-vs-s* coverage/chi2 + delta + residual."""
    vt_fit = _var_track(cal, trk.lon, trk.lat, trk.v)
    vt_star = _var_track(_lane0(), trk.lon, trk.lat, trk.v)
    out: dict[str, dict[str, float]] = {}
    for mm in sorted(set(trk.month.tolist())):
        m = trk.month == mm
        if not m.any():
            continue
        ncf, ntf = _coverage_count(trk.resid[m], vt_fit[m])
        ncs, _ = _coverage_count(trk.resid[m], vt_star[m])
        cov_fit, cov_star = ncf / ntf, ncs / ntf
        out[mm] = {
            "n": ntf,
            "coverage_fitted": cov_fit,
            "coverage_s_star": cov_star,
            "delta": cov_fit - cov_star,
            "residual_deficit": abs(cov_fit - COVERAGE_TARGET),
            "chi2_fitted": float(np.mean(trk.r2[m] / vt_fit[m])),
            "chi2_s_star": float(np.mean(trk.r2[m] / vt_star[m])),
        }
    return out


def _clip_observability(cal: CalibrationField, clip: ClipSpec) -> dict[str, float]:
    """Return fraction of box+halo grid nodes where the clip engages + max excursion."""
    lon = np.arange(293.0, 307.01, 0.25)  # box [295,305] + 2deg halo
    lat = np.arange(31.0, 45.01, 0.25)
    lo2d, la2d = np.meshgrid(lon, lat)
    # Recompute raw (unclipped) log s from the field parameters.
    if isinstance(cal, PolyCalibration):
        u, v = _norm_uv(*_clamp(lo2d, la2d))
        a0, a1, a2, a3, a4 = cal.coeffs
        raw = a0 + a1 * v + a2 * v * v + a3 * u + a4 * u * v
    elif isinstance(cal, CovariateCalibration):
        row, col = R.cell_index(*_clamp(lo2d.ravel(), la2d.ravel()))
        pv = np.array(
            [cal.proxy_cells[int(r)][int(c)] for r, c in zip(row, col, strict=True)]
        ).reshape(lo2d.shape)
        raw = cal.a + cal.b * np.log(pv)
    else:
        # Piecewise / scalar are within [L,U] by construction — clip inert.
        return {"fraction_engaged": 0.0, "max_excursion": 0.0}
    clipped = np.clip(raw, clip.lo_log_s, clip.hi_log_s)
    engaged = raw != clipped
    return {
        "fraction_engaged": float(np.mean(engaged)),
        "max_excursion": float(np.max(np.abs(raw - clipped))) if engaged.any() else 0.0,
    }


def _clamp(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Clamp coordinates to the box hull [295,305]x[33,43]."""
    return np.clip(lon, 295.0, 305.0), np.clip(lat, 33.0, 43.0)


def _off_track_bound(cal: CalibrationField) -> dict[str, float]:
    """Return max|∇log s| over the box + implied max inter-track s excursion."""
    lon = np.arange(295.0, 305.01, 0.25)
    lat = np.arange(33.0, 43.01, 0.25)
    lo2d, la2d = np.meshgrid(lon, lat)
    log_s = np.log(cal.sqrt_s_at(lo2d, la2d) ** 2)
    gy, gx = np.gradient(log_s, lat, lon)  # d/dlat, d/dlon per degree
    grad_mag = np.sqrt(gx**2 + gy**2)
    max_grad = float(np.max(grad_mag))
    # Inter-track excursion: tracks ~1-3deg apart; bound |Δlog s| <= max_grad*3.
    return {
        "max_grad_log_s_per_deg": max_grad,
        "max_intertrack_log_s_excursion_3deg": max_grad * 3.0,
        "max_intertrack_s_ratio_3deg": float(math.exp(max_grad * 3.0)),
    }


def _shat_reconciliation(trk: Track) -> dict[str, object]:
    """Return the constant-lane fit ŝ (WITH floor) vs shipped s* (§2 reconciliation)."""
    res = L.fit_region_newton(trk.r2, trk.v)
    s_hat = math.exp(res.log_s_hat)
    return {
        "s_hat_floored": s_hat,
        "s_star_shipped": S_STAR,
        "gap": s_hat - S_STAR,
        "note": (
            "s* was reduced_chi2(mu,var,ssh) with NO noise term (absorbed the "
            "floor); ŝ here is the constant-lane MLE WITH SIGMA_OBS2 — they differ "
            "by construction (spec §2)."
        ),
    }


def _cell_coverage_table(
    cal: CalibrationField, trk: Track
) -> dict[str, dict[str, float]]:
    """Return the 2°-cell coverage table (per block id 0..24) for a field."""
    vt = _var_track(cal, trk.lon, trk.lat, trk.v)
    row, col = R.cell_index(trk.lon, trk.lat)
    block = row * 5 + col
    out: dict[str, dict[str, float]] = {}
    for b in range(25):
        m = block == b
        if not m.any():
            continue
        nc, nt = _coverage_count(trk.resid[m], vt[m])
        out[str(b)] = {"n": nt, "coverage": nc / nt}
    return out


def _crps_per_lane(
    trk: Track, proxy: np.ndarray, lanes: tuple[str, ...], jet_mask: np.ndarray
) -> dict[str, float]:
    """Return held-out CRPS per lane (full-j3 fit, evaluated on full j3).

    Args:
        trk: The loaded :class:`Track`.
        proxy: (5,5) proxy array.
        lanes: Lane names to evaluate (including ``"scalar"``).
        jet_mask: (5,5) boolean jet-core mask.

    Returns:
        Dict mapping lane name to mean CRPS.
    """
    out: dict[str, float] = {}
    full = np.ones(trk.n, dtype=bool)
    for name in lanes:
        cal = (
            _lane0()
            if name == "scalar"
            else _fit_lane(name, trk, full, proxy, jet_mask)
        )
        vt = _var_track(cal, trk.lon, trk.lat, trk.v)
        out[name] = _gaussian_crps(trk.resid, vt)
    return out


def _bars(
    cal: CalibrationField, region_cov: dict[str, dict[str, float]]
) -> dict[str, Any]:
    """Return the pre-registered §6 bars (1-4) outcomes for the fitted field."""
    agg = region_cov["aggregate"]["coverage"]
    lo, hi = COVERAGE_TARGET - COVERAGE_TOL, COVERAGE_TARGET + COVERAGE_TOL
    per_region_in_band = {
        r: (lo <= region_cov[r]["coverage"] <= hi)
        for r in _EVAL_REGIONS
        if r in region_cov
    }
    worst_region = max(
        (r for r in region_cov if r != "aggregate"),
        key=lambda r: region_cov[r]["deficit"],
    )
    worst_deficit = region_cov[worst_region]["deficit"]
    return {
        "bar1_aggregate_in_band": bool(lo <= agg <= hi),
        "bar1_aggregate_coverage": agg,
        "bar2_every_region_in_band": bool(all(per_region_in_band.values())),
        "bar2_per_region_in_band": per_region_in_band,
        "bar3_worst_region": worst_region,
        "bar3_worst_deficit": worst_deficit,
        "bar3_strictly_improved_vs_scalar_record": bool(
            worst_deficit < _SCALAR_WORST_DEFICIT
        ),
        "bar3_scalar_record": {
            "worst_region": _SCALAR_WORST_REGION,
            "worst_coverage": _SCALAR_WORST_COVERAGE,
            "worst_deficit": _SCALAR_WORST_DEFICIT,
            "phase_prompt_round_record": _PHASE_PROMPT_RECORD,
            "note": (
                "Bar 3 subsumed by bar 2 (0.10 < 0.144); kept for continuity, "
                "NOT independently binding."
            ),
        },
        "bar4_no_region_regressing_out_of_band": bool(all(per_region_in_band.values())),
        "band": [lo, hi],
        "DISCLOSED": (
            "bars 1-4 computed on j3, which the final field was fit on; guards "
            "are held-out-fold selection (§5) and independent c2 reading (§7)."
        ),
    }


def _jaccard_vs_p8(mask: np.ndarray) -> dict[str, object]:
    """Return Jaccard similarity of the product mask vs the Phase-8 reference mask.

    If the Phase-8 reference mask artifact is absent (untracked by design) the
    entry is recorded as ``null`` with a note.  This is a report-only row —
    EXCLUDED from the leaf-identical gate for MIOST (self-referential, Jaccard=1).

    Args:
        mask: (5,5) boolean mask for the current product.

    Returns:
        Dict with ``jaccard``, ``n_intersection``, ``n_union``, ``note``.
    """
    if not _P8_JET_MASK_REF.exists():
        return {
            "jaccard": None,
            "note": "Phase-8 mask reference absent (data/ours/ untracked); skipped.",
        }
    d = json.loads(_P8_JET_MASK_REF.read_text())
    ref = np.asarray(d["mask"], dtype=bool)
    inter = int(np.count_nonzero(mask & ref))
    union = int(np.count_nonzero(mask | ref))
    return {
        "jaccard": float(inter) / float(union) if union else 1.0,
        "n_intersection": inter,
        "n_union": union,
        "note": "Jaccard(product_mask, phase8_mask); 1.0 for MIOST (self-referential).",
    }


def _jet_core_ref_p8() -> dict[str, object]:
    """Return a reference record pointing at the Phase-8 jet-core mask.

    Report-only row — EXCLUDED from the leaf-identical gate for MIOST.

    Returns:
        Dict with ``path``, ``cells``, ``note``; cells is null if artifact absent.
    """
    if not _P8_JET_MASK_REF.exists():
        return {
            "path": str(_P8_JET_MASK_REF),
            "cells": None,
            "note": "Phase-8 mask reference absent (data/ours/ untracked); skipped.",
        }
    d = json.loads(_P8_JET_MASK_REF.read_text())
    ref = np.asarray(d["mask"], dtype=bool)
    cells = [(int(r), int(c)) for r, c in zip(*np.where(ref), strict=True)]
    return {
        "path": str(_P8_JET_MASK_REF),
        "cells": cells,
        "note": "Phase-8 reference mask cells for Jaccard drift monitoring.",
    }


# ---------------------------------------------------------------------------
# Proxy loader
# ---------------------------------------------------------------------------


def _proxy(desc: ProductDescriptor) -> np.ndarray:
    """Return the (5,5) signal-variance proxy from the product mean maps.

    Args:
        desc: The :class:`ProductDescriptor` for the current product.

    Returns:
        (5,5) float ndarray of per-cell proxy values.
    """
    with xr.open_dataset(desc.mean_maps) as ds:
        return R.proxy_cells(ds)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def build_evidence(
    desc: ProductDescriptor,
    trk: Track,
    proxy: np.ndarray,
    scope: str,
) -> dict[str, Any]:
    """Run the full fit/select/refit pipeline and assemble the §6 evidence JSON.

    This is the EXACT Phase-8 sequence extracted from ``phase8_fit_run.py``,
    parameterized by the descriptor.  No math is forked or rewritten.

    Args:
        desc: The :class:`ProductDescriptor` driving the run.
        trk: The loaded :class:`Track`.
        proxy: (5,5) proxy array from the product mean maps.
        scope: ``"dev"`` or ``"full"`` (recorded in evidence).

    Returns:
        Evidence dict matching the Phase-8 ``fit_run`` structure, plus new
        per-product rows ``jet_core_ref_p8``, ``jaccard_vs_p8``, and
        ``promotion_record``.
    """
    # Mask-predates-fit ordering guard (spec §5 + Task-7 AC 1a):
    # The mask artifact MUST exist before any lane fit runs.  Build it with
    # scripts/build_jet_core_mask.py before running the harness.
    if not desc.mask_artifact.exists():
        raise FileNotFoundError(
            f"Jet-core mask artifact missing (mask must be built before fit): "
            f"{desc.mask_artifact}\n"
            "Run: pixi run python scripts/build_jet_core_mask.py "
            f"--mean-maps <product_mean_maps> --out {desc.mask_artifact}"
        )
    jet_mask = _jet_cell_mask(desc.mask_artifact)

    # ρ̂ once at frozen s*; n_eff per block + merge rule on the S-fold layout.
    rho = measure_rho(trk)
    rhos = np.asarray(rho["rhos_used"])
    layout, salt, redraws = draw_s_layout(trk, desc.fold_seed_tuple)
    n_eff_block = _n_eff_per_block(trk, rhos)
    merged_layout, merge_map = F.merge_small_blocks(layout, n_eff_block)

    # Lanes: always 0/A/B; covariate iff promoted.
    base_lanes: tuple[str, ...] = ("piecewise", "poly")
    lanes: tuple[str, ...] = base_lanes + (
        ("covariate",) if desc.covariate_promoted else ()
    )

    # T family and S family pooled-worst-region per lane (+ lane-0 control).
    t_masks = list(F.t_folds(trk.month))
    s_masks = F.s_folds(trk.lon, trk.lat, trk.labels, merged_layout)
    t_stats = run_family(trk, proxy, t_masks, ("scalar",) + lanes, jet_mask)
    s_stats = run_family(trk, proxy, s_masks, ("scalar",) + lanes, jet_mask)

    # Lane records for folds.select (lanes[0] = lane-0 baseline).
    lane_records: list[dict[str, Any]] = [
        {"name": "scalar", "s_stat": s_stats["scalar"], "t_stat": t_stats["scalar"]}
    ]
    for nm in lanes:
        lane_records.append({"name": nm, "s_stat": s_stats[nm], "t_stat": t_stats[nm]})

    winner, table = F.select(lane_records)

    # Recompute + record per-lane eligibility (folds.select returns lanes as-is).
    l0_s, l0_t = s_stats["scalar"], t_stats["scalar"]
    eligibility: dict[str, dict[str, Any]] = {}
    for rec in lane_records[1:]:
        nm = str(rec["name"])
        beats_primary = rec["s_stat"] < l0_s - TIE_BAND
        no_worse_secondary = rec["t_stat"] <= l0_t + TIE_BAND
        elig = bool(beats_primary and no_worse_secondary)
        reasons = []
        if not beats_primary:
            reasons.append("does not beat lane-0 S-stat beyond ±0.01 absolute band")
        if not no_worse_secondary:
            reasons.append("worse than lane-0 T-stat beyond band")
        eligibility[nm] = {
            "eligible": elig,
            "s_stat": rec["s_stat"],
            "t_stat": rec["t_stat"],
            "beats_primary": beats_primary,
            "no_worse_secondary": no_worse_secondary,
            "reasons": reasons or ["eligible"],
        }

    evidence: dict[str, Any] = {
        "scope": scope,
        "n_track_points": trk.n,
        "selection": {
            "table": table,
            "lane0_s_stat": l0_s,
            "lane0_t_stat": l0_t,
            "eligibility": eligibility,
            "tie_band_rule": (
                "ABSOLUTE ±0.01 band on the selection statistic (owner ruling "
                "2026-07-11: band ≈ 2×pooled-coverage-SE ≈ 0.01; relative "
                "reading rejected); candidate beats baseline iff candidate < "
                "baseline − TIE_BAND; lower is better."
            ),
            "combination_rule": (
                "PRIMARY S-fold pooled-worst-region deficit; ties -> T-fold; "
                "ties -> smooth preference poly>covariate>piecewise."
            ),
        },
        "folds": {
            "s_salt_final": salt,
            "s_salt_redraws": redraws,
            "s_layout": [sorted(f) for f in layout],
            "s_layout_merged": [sorted(f) for f in merged_layout],
            "merge_mapping": {str(k): v for k, v in merge_map.items()},
            "n_eff_per_block": {str(k): v for k, v in n_eff_block.items()},
            "min_n_eff": MIN_N_EFF,
            "t_folds_pooled_worst": t_stats,
            "s_folds_pooled_worst": s_stats,
        },
        "rho_hat": rho,
        "shat_reconciliation": _shat_reconciliation(trk),
        # Per-product promotion record (new in Phase 9).
        "promotion_record": {
            "product_id": desc.product_id,
            "covariate_promoted": desc.covariate_promoted,
            "fold_seed_tuple": list(desc.fold_seed_tuple),
        },
    }

    if winner is None:
        evidence["selection"]["negative_result"] = True
        evidence["selection"]["stop_banner"] = (
            "NEGATIVE RESULT: no fit lane beats lane-0 under the pre-registered "
            "eligibility rule. Shipping the scalar; NO field artifact written; "
            "NO c2 touch. Tasks 11-12 do not execute; Task 13 closes."
        )
        return evidence

    winner_name = str(winner["name"])
    evidence["selection"]["negative_result"] = False
    evidence["selection"]["winner"] = winner_name

    cal, clip = refit_winner(trk, proxy, winner_name, jet_mask)
    region_cov = _region_coverage(cal, trk)
    region_cov_star = _region_coverage(_lane0(), trk)

    s_hat_full = L.fit_region_newton(trk.r2, trk.v).log_s_hat
    tail_ratio, tail_flag = L.tail_diagnostic(trk.r2, trk.v, math.exp(s_hat_full))

    all_lane_names = ("scalar",) + lanes
    evidence["winner_field"] = {
        "kind": winner_name,
        "to_json": cal.to_json(),
        "cal_key": cal.key(),
        "clip": {"lo_log_s": clip.lo_log_s, "hi_log_s": clip.hi_log_s},
    }
    evidence["bars"] = _bars(cal, region_cov)
    evidence["regional_table"] = {
        r: {
            "fitted": region_cov.get(r, {}),
            "s_star": region_cov_star.get(r, {}),
        }
        for r in _EVAL_REGIONS
    }
    evidence["monthly_table"] = _monthly_table(cal, trk)
    evidence["per_region_chi2"] = {
        "by_region": {
            r: {
                "fitted": region_cov.get(r, {}).get("reduced_chi2"),
                "s_star": region_cov_star.get(r, {}).get("reduced_chi2"),
            }
            for r in _EVAL_REGIONS
        },
        "jet_core_note": (
            "jet-core post-fit chi2 named as a recorded outcome (motivated the "
            "phase; coverage remains the only bar)."
        ),
    }
    evidence["tail_diagnostic"] = {
        "ratio": tail_ratio,
        "flagged": bool(tail_flag),
        "note": "median(chi2)/CHI2_1_MEDIAN; ratio>=1.5 flags under-dispersion.",
    }
    evidence["clip_observability"] = _clip_observability(cal, clip)
    evidence["off_track_bound"] = _off_track_bound(cal)
    evidence["cell_coverage_table"] = {
        "fitted": _cell_coverage_table(cal, trk),
        "s_star": _cell_coverage_table(_lane0(), trk),
    }
    evidence["crps_per_lane"] = _crps_per_lane(trk, proxy, all_lane_names, jet_mask)
    # Regions fork (§11.1): per-product mask gate frame — report-only rows.
    # EXCLUDED from leaf-identical gate (jet_core_ref_p8: self-referential for MIOST;
    # jaccard_vs_p8: Jaccard=1.0 for MIOST).  Do NOT simplify away the EXCLUDED
    # set in the test — it documents which new rows are expected.
    evidence["jet_core_ref_p8"] = _jet_core_ref_p8()
    evidence["jaccard_vs_p8"] = _jaccard_vs_p8(jet_mask)
    return evidence


# ---------------------------------------------------------------------------
# Atomic write helper
# ---------------------------------------------------------------------------


def _default(o: object) -> object:
    """JSON serialiser for numpy scalars/arrays."""
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not serialisable: {type(o)!r}")


def atomic_write_json(path: Path, data: object) -> None:
    """Write *data* as JSON to *path* atomically (POSIX os.replace).

    Writes to a sibling temp file in the same directory, then renames over
    the target.  A crash mid-write therefore never truncates the existing file.

    Args:
        path: Destination path.
        data: JSON-serialisable object (numpy scalars/arrays supported).
    """
    text = json.dumps(data, indent=2, default=_default)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        os.write(fd, text.encode())
        os.close(fd)
        os.replace(tmp, path)
    except Exception:
        os.close(fd)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Top-level run entry point (called by CLI scripts)
# ---------------------------------------------------------------------------


def run_harness(desc: ProductDescriptor, scope: str) -> dict[str, Any]:
    """Run the complete fit harness for a product and return the evidence dict.

    Args:
        desc: The :class:`ProductDescriptor` for the product to calibrate.
        scope: ``"dev"`` or ``"full"``.

    Returns:
        The evidence dict (same structure as Phase-8 ``fit_run``, plus new
        Phase-9 rows ``jet_core_ref_p8``, ``jaccard_vs_p8``,
        ``promotion_record``).
    """
    trk = load_track(desc, scope)
    proxy = _proxy(desc)
    return build_evidence(desc, trk, proxy, scope)
