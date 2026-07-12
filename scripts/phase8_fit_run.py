"""Phase-8 fit run: fold fits, lane selection, winner refit, evidence JSON.

Executes spec §7 steps 1-3 (step 0, the covariate-alignment diagnostic, already
ran and PROMOTED the covariate lane — see gate JSON ``phase8.covariate_alignment``,
r_primary=0.8533).  This script ORCHESTRATES the tested calibration modules; it
contains no new numerics beyond thin glue (CRPS closed form, coverage counting,
pass-id segmentation, evidence assembly).

Pipeline (spec §7):
    load_track() -> measure_rho() -> run_family(t_folds) -> run_family(s_folds)
    -> select() -> refit_or_negative() -> evidence() -> write + STOP banner

Lanes evaluated per fold (held-out coverage at s(x)*v + SIGMA_OBS2):
    - lane 0: constant s* EVALUATED (never fit) — the control/baseline.
    - lane A (piecewise): Newton per fit-partition region (SW,SE,NW,NE,JET).
    - lane B (poly): L-BFGS-B on design [1, v, v^2, u, u*v].
    - covariate (promoted): (a,b) on design [1, log proxy(cell(x))].

Track-side predictive variance convention EVERYWHERE:
    var_track(x) = s(x) * v + SIGMA_OBS2
where v is the UN-inflated (raw) map variance interpolated on the track.  The
signed var maps are RAW (s* never baked in) — v comes straight from the artifact.

Scope discipline (mirrors scripts/stage_miost_gate_run.py):
    SVERDRUP_PHASE8_SCOPE=dev  -> 12-day dev fixture window; writes ONLY
                                  phase8_dev_smoke.json (NEVER the gate JSON).
    (default / full)           -> full j3 year; writes the gate JSON phase8 block.

c2 is UNTOUCHED: no c2 path is imported or loaded anywhere.  The provenance guard
(assert_scored_not_assimilated) is asserted on every map->track scoring call.

Usage:
    SVERDRUP_PHASE8_SCOPE=dev pixi run python scripts/phase8_fit_run.py
    pixi run python scripts/phase8_fit_run.py            # full (detached)
"""

from __future__ import annotations

import json
import math
import os
import tempfile
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
from sverdrup.distributions.miost_ensemble import (
    CalibrationField,
    ClipSpec,
    CovariateCalibration,
    PiecewiseCalibration,
    PolyCalibration,
    ScalarCalibration,
)

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------

ROOT = Path("data/2021a_ssh_mapping_ose/ours")
RESULTS = ROOT / "stage_miost_gate_results.json"
MEAN_NC = ROOT / "stage_b_mean_maps.nc"
VAR_NC = ROOT / "stage_b_var_maps.nc"
JET_MASK = ROOT / "phase8_jet_core_mask.json"
FIELD_OUT = ROOT / "phase8_field.json"
SMOKE_OUT = ROOT / "phase8_dev_smoke.json"
SCOPE_FIX = Path("tests/validation/fixtures/stage_a_scope.json")

EPOCH = np.datetime64("2017-01-01")
SCOPE_MODE = os.environ.get("SVERDRUP_PHASE8_SCOPE", "full")  # "dev" | "full"
if SCOPE_MODE not in {"dev", "full"}:
    raise SystemExit(
        f"SVERDRUP_PHASE8_SCOPE must be 'dev' or 'full', got {SCOPE_MODE!r}"
    )

# Full-year j3 box; dev overrides the time window from the fixture.
_FULL_TMIN, _FULL_TMAX = "2017-01-01", "2018-01-01"
# Pass segmentation: along-track cadence is ~1.08 s; inter-pass gaps are hours+.
_PASS_GAP_SEC = 60.0

# The evaluation regions and lane-A fit regions.
_EVAL_REGIONS = ("SW", "SE", "NW", "NE", "jet_core", "aggregate")
_FIT_REGIONS = ("SW", "SE", "NW", "NE", "JET")

# The scalar record from the shipped scalar (spec §6 bar 3): worst region SE.
_SCALAR_WORST_REGION = "SE"
_SCALAR_WORST_COVERAGE = 0.8267
_SCALAR_WORST_DEFICIT = 0.1440
_PHASE_PROMPT_RECORD = 0.69  # round number recorded for continuity


# ---------------------------------------------------------------------------
# Thin pure glue (only what does not already live in the tested modules)
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
# Track loader (same loaders/box/convention as diag_stage_b_localized_calibration)
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


def _jet_cell_mask() -> np.ndarray:
    """Load the pre-registered (5,5) jet-core cell mask artifact."""
    d = json.loads(JET_MASK.read_text())
    return np.asarray(d["mask"], dtype=bool)


def load_track() -> Track:
    """Interp the shipped mean/var maps on the j3 track and build arrays.

    Uses the exact loaders, box, and raw-variance convention of
    ``scripts/diag_stage_b_localized_calibration.py``.  The scored map carries
    an assimilation provenance guard (``assert_scored_not_assimilated``).

    Returns:
        A :class:`Track` with per-point day/lon/lat/resid/v/month/pass_id plus
        the fit-partition labels and per-point jet-core membership.
    """
    import sverdrup.validation.their_eval as te
    from sverdrup.validation.provenance_guard import assert_scored_not_assimilated

    cfg = json.loads(SCOPE_FIX.read_text())
    track = Path(cfg["val_track_path"])  # j3 validation track (c2 never loaded)
    assert_scored_not_assimilated(MEAN_NC, track)
    assert_scored_not_assimilated(VAR_NC, track)

    tmin, tmax = _FULL_TMIN, _FULL_TMAX
    if SCOPE_MODE == "dev":
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
        str(MEAN_NC), ds_at, is_circle=False, **box
    )
    _, _, _, _, var = interp_on_alongtrack(str(VAR_NC), ds_at, is_circle=False, **box)
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

    jet_cells = _jet_cell_mask()
    row, col = R.cell_index(lon, lat)
    jet_pts = jet_cells[row, col]
    labels = R.fit_partition(lon, lat, jet_pts)

    return Track(day, lon, lat, resid, v, month, pid, labels, jet_pts)


# ---------------------------------------------------------------------------
# Lane fitting on a fit-mask, evaluation on a score-mask
# ---------------------------------------------------------------------------


def _fit_lane(
    name: str, trk: Track, fit: np.ndarray, proxy: np.ndarray
) -> CalibrationField:
    """Fit a calibration field of the given lane on the fit-masked subset.

    The clip bounds used here are wide (evidence anchors come from the FULL-j3
    refit, spec §9); per-fold fits are only ever used to score coverage, and
    lane values sit far inside so the clip is inert on the folds.
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
            mask=tuple(tuple(bool(b) for b in row) for row in _jet_cell_mask()),
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
) -> dict[str, float]:
    """Return per-lane pooled-worst-region deficit over a fold family.

    For each lane, fit on every fold's fit-mask, score held-out coverage at
    ``s(x)*v + SIGMA_OBS2`` per evaluation region, pool ``(n_cov, n_tot)`` across
    folds, then take the worst |coverage - target| over the pre-registered
    evaluation regions (:func:`folds.pooled_worst_region`).  Lane 0 is the
    constant-s* control, evaluated on the identical folds.
    """
    out: dict[str, float] = {}
    for name in lanes:
        pooled: dict[str, list[int]] = {r: [0, 0] for r in _EVAL_REGIONS}
        for fit, score in fold_masks:
            if not fit.any() or not score.any():
                continue
            cal = _lane0() if name == "scalar" else _fit_lane(name, trk, fit, proxy)
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


def draw_s_layout(trk: Track) -> tuple[tuple[frozenset[int], ...], int, list[int]]:
    """Return (layout, final_salt, redraws) respecting the partition constraint."""
    salt = 0
    redraws: list[int] = []
    while True:
        layout = F.s_fold_layout(salt=salt)
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
    trk: Track, proxy: np.ndarray, winner_name: str
) -> tuple[CalibrationField, ClipSpec]:
    """Refit the winning lane on ALL of j3 with evidence-anchored clip bounds.

    Clip [L, U] = lane-A per-region log-s range ± log(CLIP_PAD).  The refit runs
    the loud ``assert_beats_scalar`` safeguard (fitted NLL vs s*-constant NLL on
    full j3).
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
            mask=tuple(tuple(bool(b) for b in row) for row in _jet_cell_mask()),
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


def _crps_per_lane(trk: Track, proxy: np.ndarray) -> dict[str, float]:
    """Return held-out CRPS per lane (full-j3 fit, evaluated on full j3)."""
    out: dict[str, float] = {}
    full = np.ones(trk.n, dtype=bool)
    for name in ("scalar", "piecewise", "poly", "covariate"):
        cal = _lane0() if name == "scalar" else _fit_lane(name, trk, full, proxy)
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


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _proxy() -> np.ndarray:
    """Return the (5,5) signal-variance proxy from the shipped mean maps."""
    with xr.open_dataset(MEAN_NC) as ds:
        return R.proxy_cells(ds)


def build_evidence(trk: Track, proxy: np.ndarray) -> dict[str, Any]:
    """Run the full fit/select/refit pipeline and assemble the §6 evidence JSON."""
    # ρ̂ once at frozen s*; n_eff per block + merge rule on the S-fold layout.
    rho = measure_rho(trk)
    rhos = np.asarray(rho["rhos_used"])
    layout, salt, redraws = draw_s_layout(trk)
    n_eff_block = _n_eff_per_block(trk, rhos)
    merged_layout, merge_map = F.merge_small_blocks(layout, n_eff_block)

    lanes = ("piecewise", "poly", "covariate")

    # T family and S family pooled-worst-region per lane (+ lane-0 control).
    t_masks = list(F.t_folds(trk.month))
    s_masks = F.s_folds(trk.lon, trk.lat, trk.labels, merged_layout)
    t_stats = run_family(trk, proxy, t_masks, ("scalar",) + lanes)
    s_stats = run_family(trk, proxy, s_masks, ("scalar",) + lanes)

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
        "scope": SCOPE_MODE,
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

    cal, clip = refit_winner(trk, proxy, winner_name)
    region_cov = _region_coverage(cal, trk)
    region_cov_star = _region_coverage(_lane0(), trk)

    s_hat_full = L.fit_region_newton(trk.r2, trk.v).log_s_hat
    tail_ratio, tail_flag = L.tail_diagnostic(trk.r2, trk.v, math.exp(s_hat_full))

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
    evidence["crps_per_lane"] = _crps_per_lane(trk, proxy)
    return evidence


def _default(o: object) -> object:
    """JSON serialiser for numpy scalars/arrays."""
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not serialisable: {type(o)!r}")


def _atomic_write_json(path: Path, data: object) -> None:
    """Write *data* as JSON to *path* atomically (POSIX os.replace).

    Writes to a sibling temp file in the same directory, then renames over
    the target.  A crash mid-write therefore never truncates the existing file.
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


def main() -> None:
    """Run the fit pipeline, write scope-appropriate artifacts, print the banner."""
    trk = load_track()
    proxy = _proxy()
    evidence = build_evidence(trk, proxy)

    negative = evidence["selection"].get("negative_result", False)

    if SCOPE_MODE == "dev":
        # Dev smoke: structure-completeness only; NEVER the gate JSON, NEVER field.
        _atomic_write_json(SMOKE_OUT, evidence)
        print(
            f"[dev smoke] scope=dev n={trk.n} points; "
            f"negative_result={negative}; wrote {SMOKE_OUT}"
        )
        _print_banner(evidence, negative)
        return

    # Full scope: write the gate JSON phase8 block (preserve existing content).
    results = json.loads(RESULTS.read_text())
    results.setdefault("phase8", {})  # preserves covariate_alignment
    results["phase8"]["fit_run"] = evidence
    _atomic_write_json(RESULTS, results)

    if not negative:
        cal_json = evidence["winner_field"]["to_json"]
        _atomic_write_json(
            FIELD_OUT,
            {
                "calibration": cal_json,
                "cal_key": evidence["winner_field"]["cal_key"],
            },
        )
        print(f"[full] wrote field artifact {FIELD_OUT}")
    else:
        print("[full] NEGATIVE RESULT — no field artifact written.")
    print(f"[full] wrote phase8.fit_run into {RESULTS}")
    _print_banner(evidence, negative)


def _print_banner(evidence: dict[str, Any], negative: bool) -> None:
    """Print the STOP banner + selection/bars summary."""
    sel = evidence["selection"]
    print("=" * 72)
    if negative:
        print("STOP — NEGATIVE RESULT (spec §3 path)")
        print(sel["stop_banner"])
        print("=" * 72)
        return
    print("STOP — owner reviews j3-side evidence (spec §7 step 4)")
    print(f"winner: {sel['winner']}")
    print(f"lane-0 S/T stat: {sel['lane0_s_stat']:.4f} / {sel['lane0_t_stat']:.4f}")
    for nm, e in sel["eligibility"].items():
        print(
            f"  {nm:10s} S={e['s_stat']:.4f} T={e['t_stat']:.4f} "
            f"eligible={e['eligible']}"
        )
    b = evidence["bars"]
    print(
        f"bar1 agg={b['bar1_aggregate_coverage']:.4f} in_band={b['bar1_aggregate_in_band']}"
    )
    print(f"bar2 every_region_in_band={b['bar2_every_region_in_band']}")
    print(
        f"bar3 worst={b['bar3_worst_region']} deficit={b['bar3_worst_deficit']:.4f} "
        f"improved={b['bar3_strictly_improved_vs_scalar_record']}"
    )
    print(
        f"salt={evidence['folds']['s_salt_final']} "
        f"tail_flag={evidence['tail_diagnostic']['flagged']}"
    )
    print("=" * 72)


if __name__ == "__main__":
    main()
