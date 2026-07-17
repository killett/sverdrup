"""Phase-9 G_pre anchor recomputation (owner obligation 5).

Reads phase9.miost.fit_run from the gate results JSON, computes G_pre from
the selection block (§7c1), assembles the anchor block with companions, and
writes it atomically to phase9.g_pre_anchor in the same JSON.

The anchor is the Phase-10 interface contract: Phase 10 (lat-varying method
parameters, invariant-12) will consume phase9.g_pre_anchor by reference.

Owner obligation 5 per spec §7c:
  - G_pre = lane-0 S-stat − winner S-stat (pooled worst-region deficit units)
  - Written at phase9.g_pre_anchor; definition verbatim from spec §7c1
  - Companions: area_weighted_std_log_s, log_s_range, clip_engagement_fraction,
    nll_gap_demoted (with dof and n_eff_note; no threshold semantics)
  - ZERO c2 touches; script only READS selection block, WRITES phase9.g_pre_anchor

Usage::

    pixi run python scripts/phase9_g_pre_anchor.py

Running twice produces a byte-identical block (deterministic, no timestamps,
no dict-order nondeterminism — json.dumps with sort_keys=False is stable
because the block dict is constructed in a fixed literal order).
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from sverdrup.distributions.calibration import CalibrationField

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_DATA_ROOT = Path("data/2021a_ssh_mapping_ose/ours")
_RESULTS = _DATA_ROOT / "stage_miost_gate_results.json"
_MASK_ARTIFACT = _DATA_ROOT / "phase8_jet_core_mask.json"
_FIELD_ARTIFACT = _DATA_ROOT / "phase9_field_miost.json"

# ---------------------------------------------------------------------------
# Spec §7c1 definition — VERBATIM from the spec file
# (do NOT paraphrase; this is the pinned wording delivered to Phase 10)
# ---------------------------------------------------------------------------

_SPEC_DEFINITION = (
    "STATISTIC: G = lane-0 S-stat − winner S-stat (pooled worst-region deficit "
    "units), computed by the standard fold/selection machinery verbatim "
    "(absolute ±0.01 band, lexicographic rule, eligibility incl. lane-0). "
    "ENTIRELY j3-side — the instrument never touches c2 (touches belong to "
    "product acceptance, not to this comparison)."
)

# Fixed challenge grid: box [295,305] + 2° halo on each side
# (same grid as harness._clip_observability — pinned for pre/post-B comparability)
_LON_GRID = np.arange(293.0, 307.01, 0.25)
_LAT_GRID = np.arange(31.0, 45.01, 0.25)

# NLL gap dof: poly winner has 5 free parameters (a0..a4)
_POLY_DOF = 5

# n_eff note (verbatim from spec §7c4, demoted with no threshold semantics)
_N_EFF_NOTE = "AIC under-penalizes ~10x at n_eff≈n/10.27 — no threshold semantics"

# ---------------------------------------------------------------------------
# Pure-function core — tested independently without artifacts
# ---------------------------------------------------------------------------


def _compute_clip_engagement(cal_json: dict[str, Any]) -> float:
    """Compute clip engagement fraction on the fixed challenge grid.

    Evaluates the RAW (pre-clip) log s for a PolyCalibration on the box+halo
    grid and returns the fraction of nodes where clipping engages.

    For non-poly kinds (piecewise, scalar) the clip is inert by construction
    (values lie within [L, U] at all grid nodes), so 0.0 is returned.

    Args:
        cal_json: Calibration dict as produced by CalibrationField.to_json().

    Returns:
        Fraction of box+halo grid nodes where the clip is active, in [0, 1].
    """
    if cal_json.get("kind") != "poly":
        return 0.0
    a0, a1, a2, a3, a4 = [float(c) for c in cal_json["coeffs"]]
    clip_lo = float(cal_json["clip"]["lo_log_s"])
    clip_hi = float(cal_json["clip"]["hi_log_s"])
    lo2d, la2d = np.meshgrid(_LON_GRID, _LAT_GRID)
    # Clamp to hull [295,305] × [33,43] — mirrors PolyCalibration._clamp_hull
    lo_c = np.clip(lo2d, 295.0, 305.0)
    la_c = np.clip(la2d, 33.0, 43.0)
    u = (lo_c - 300.0) / 5.0
    v_coord = (la_c - 38.0) / 5.0
    raw = a0 + a1 * v_coord + a2 * v_coord * v_coord + a3 * u + a4 * u * v_coord
    clipped = np.clip(raw, clip_lo, clip_hi)
    engaged = raw != clipped
    return float(np.mean(engaged))


def _compute_area_weighted_stats(
    cal_json: dict[str, Any],
) -> tuple[float, float]:
    """Compute area-weighted std and range of log s on the fixed challenge grid.

    Uses the CLIPPED (shipped) log s field, cos-lat area weighting.

    Args:
        cal_json: Calibration dict.

    Returns:
        Tuple (area_weighted_std_log_s, log_s_range) where log_s_range = max − min.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from sverdrup.distributions.calibration import calibration_from_json

    cal = calibration_from_json(cal_json)
    lo2d, la2d = np.meshgrid(_LON_GRID, _LAT_GRID)
    log_s = cal.log_s_at(lo2d, la2d)  # clipped shipped field
    # Area weights: cos(lat), normalised
    cos_lat = np.cos(np.radians(la2d))
    w = cos_lat / float(cos_lat.sum())
    mean_log_s = float(np.sum(w * log_s))
    std_log_s = float(math.sqrt(float(np.sum(w * (log_s - mean_log_s) ** 2))))
    log_s_range = float(log_s.max() - log_s.min())
    return std_log_s, log_s_range


def build_anchor_block(
    selection: dict[str, Any],
    cal_json: dict[str, Any],
    cal_key: str,
    mask_sha256: str,
    nll_gap_value: float | None = None,
) -> dict[str, Any]:
    """Assemble the phase9.g_pre_anchor block (pure function, testable w/o artifacts).

    Args:
        selection: The selection sub-dict from phase9.miost.fit_run (must have
            ``lane0_s_stat``, ``winner``, and ``table`` with per-lane s_stat rows).
        cal_json: The calibration JSON dict (from phase9_field_miost.json
            ``calibration`` key) used to compute field companions.
        cal_key: The cal_key string from the field artifact (for self-consistency
            check; the caller verifies it matches cal_json before passing).
        mask_sha256: SHA-256 hex digest of phase8_jet_core_mask.json artifact.
        nll_gap_value: Precomputed NLL gap (nll_scalar - nll_winner on full j3).
            None if not available (stored as null with demoted note).

    Returns:
        Anchor block dict ready for atomic JSON write at phase9.g_pre_anchor.
    """
    # G_pre: lane0_s_stat − winner_s_stat (§7c1)
    lane0_s = float(selection["lane0_s_stat"])
    winner_name = selection["winner"]
    winner_s = float(
        next(r["s_stat"] for r in selection["table"] if r["name"] == winner_name)
    )
    g_pre = float(lane0_s - winner_s)  # explicit float() to coerce away numpy scalars

    # Clip engagement fraction on fixed challenge grid
    clip_frac = float(_compute_clip_engagement(cal_json))

    # Area-weighted std and range of log s on fixed challenge grid
    std_log_s, log_s_range = _compute_area_weighted_stats(cal_json)

    return {
        "g_pre": g_pre,
        "definition": _SPEC_DEFINITION,
        "frame": {
            "mask": "phase8_jet_core_mask.json",
            "sha256": mask_sha256,
            "fold_seed_tuple": ["miost", "phase8", "s-folds"],
            "salt": 1,
        },
        "companions": {
            "area_weighted_std_log_s": float(std_log_s),
            "log_s_range": float(log_s_range),
            "clip_engagement_fraction": clip_frac,
            "nll_gap_demoted": {
                "value": (float(nll_gap_value) if nll_gap_value is not None else None),
                "dof": _POLY_DOF,
                "n_eff_note": _N_EFF_NOTE,
            },
        },
    }


# ---------------------------------------------------------------------------
# NLL gap computation (requires track data; separated for testability)
# ---------------------------------------------------------------------------


def _compute_nll_gap() -> float:
    """Compute the raw NLL gap (nll_scalar - nll_poly) on the full j3 track.

    This requires loading the track from disk.  The result has no threshold
    semantics (per spec §7c4: AIC under-penalizes ~10x at n_eff ≈ n/10.27).

    Returns:
        NLL gap = nll_lane0 - nll_winner (scalar − poly, positive = poly wins).
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from sverdrup.application.calibration import likelihood as L
    from sverdrup.application.calibration.constants import S_STAR, SIGMA_OBS2
    from sverdrup.application.calibration.harness import MIOST_DESCRIPTOR, load_track
    from sverdrup.distributions.calibration import calibration_from_json

    # Load track (scope = full, same as the fit run)
    trk = load_track(MIOST_DESCRIPTOR, scope="full")

    # NLL for lane-0 (scalar constant s*)
    log_s_star = math.log(S_STAR)
    ones = np.ones((trk.n, 1))
    nll_scalar = L.nll(np.array([log_s_star]), ones, trk.r2, trk.v)

    # NLL for winner (poly field): load from phase9_field_miost.json
    with open(_FIELD_ARTIFACT) as f:
        field_d = json.load(f)
    cal = calibration_from_json(field_d["calibration"])
    log_s_fit = np.log(cal.sqrt_s_at(trk.lon, trk.lat) ** 2)
    tot = np.exp(log_s_fit) * trk.v + SIGMA_OBS2
    nll_winner = float(0.5 * np.sum(np.log(tot) + trk.r2 / tot))

    return float(nll_scalar - nll_winner)


# ---------------------------------------------------------------------------
# Grid-drift guard (Phase-10 contract safety)
# ---------------------------------------------------------------------------


def _assert_grid_matches_harness(
    cal: CalibrationField, computed_clip_fraction: float
) -> None:
    """Assert this script's grid + hull literals have not drifted from the harness.

    The harness's ``_clip_observability`` builds its challenge grid inline (no
    exported constant), so drift is guarded two ways:

    1. HULL: probe points pushed through ``harness._clamp`` must equal the
       same points clamped with this script's hull literals (295/305, 33/43).
    2. GRID (functional): the locally computed clip engagement fraction must
       exactly equal ``harness._clip_observability`` evaluated on the same
       shipped field — any grid-extent/step drift between the two
       implementations changes the node set and hence the fraction.

    Args:
        cal: The shipped CalibrationField (poly winner; carries its ClipSpec).
        computed_clip_fraction: Fraction computed by _compute_clip_engagement.

    Raises:
        RuntimeError: If either check fails — grid drift must fail loudly,
            never silently desync the anchor from the harness.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from sverdrup.application.calibration import harness as H
    from sverdrup.distributions.calibration import PolyCalibration

    if not isinstance(cal, PolyCalibration):
        raise RuntimeError(
            f"Drift guard expects the poly winner field, got {type(cal).__name__} — "
            f"the anchor's companion path is pinned to the shipped poly field."
        )

    probe_lon = np.array([0.0, 293.0, 295.0, 300.0, 305.0, 307.0, 999.0])
    probe_lat = np.array([0.0, 31.0, 33.0, 38.0, 43.0, 45.0, 99.0])
    h_lon, h_lat = H._clamp(probe_lon, probe_lat)
    local_lon = np.clip(probe_lon, 295.0, 305.0)
    local_lat = np.clip(probe_lat, 33.0, 43.0)
    if not (np.array_equal(h_lon, local_lon) and np.array_equal(h_lat, local_lat)):
        raise RuntimeError(
            "Hull literals drifted from harness._clamp — update this script's "
            "hull constants (295/305, 33/43) to match the harness before "
            "writing the anchor."
        )

    ref = H._clip_observability(cal, cal.clip)["fraction_engaged"]
    if ref != computed_clip_fraction:
        raise RuntimeError(
            f"Challenge-grid drift: local clip_engagement_fraction "
            f"{computed_clip_fraction!r} != harness._clip_observability "
            f"{ref!r} — the fixed grid or engagement path has desynced "
            f"from the harness."
        )


# ---------------------------------------------------------------------------
# Atomic write helper (re-exported from harness for this script)
# ---------------------------------------------------------------------------


def _atomic_write_json(path: Path, data: object) -> None:
    """Write data as JSON to path atomically.

    Delegates to the harness's atomic_write_json (same semantics).

    Args:
        path: Destination path.
        data: JSON-serialisable object.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from sverdrup.application.calibration.harness import atomic_write_json

    atomic_write_json(path, data)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Recompute G_pre anchor from phase9.miost.fit_run and write to gate JSON.

    Steps:
      1. Load gate results JSON; assert phase9.miost.fit_run exists (STOP if not).
      2. Assert phase9_field_miost.json is byte-identical to phase8_field.json
         (leaf-identical regression check; cal_key self-consistency).
      3. Compute G_pre from selection block.
      4. Compute companions from the shipped clipped field on fixed grid.
      5. Compute NLL gap on full j3 (demoted, no threshold).
      6. Assemble anchor block and write atomically to phase9.g_pre_anchor.
    """
    # Step 1: load gate results and check phase9.miost.fit_run
    results = json.loads(_RESULTS.read_text())
    try:
        fit_run = results["phase9"]["miost"]["fit_run"]
    except KeyError:
        print(
            "NEEDS_CONTEXT: phase9.miost.fit_run absent from gate results JSON.\n"
            "Run: SVERDRUP_PHASE9_SCOPE=full pixi run python scripts/phase9_fit_run.py"
        )
        sys.exit(1)

    # Step 2: assert phase9_field_miost.json is byte-identical to phase8_field.json
    field_d = json.loads(_FIELD_ARTIFACT.read_text())
    phase8_field_d = json.loads((_DATA_ROOT / "phase8_field.json").read_text())
    if field_d != phase8_field_d:
        raise RuntimeError(
            "phase9_field_miost.json is NOT byte-identical to phase8_field.json — "
            "leaf-identical regression violated"
        )

    # Cal key self-consistency check
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from sverdrup.distributions.calibration import calibration_from_json

    cal = calibration_from_json(field_d["calibration"])
    cal_key = field_d["cal_key"]
    recomputed_key = cal.key()
    if recomputed_key != cal_key:
        raise RuntimeError(
            f"cal_key self-consistency FAILED:\n"
            f"  stored:     {cal_key!r}\n"
            f"  recomputed: {recomputed_key!r}"
        )
    print(f"cal_key self-consistent: {cal_key}")

    # Mask artifact SHA-256 — an input to the step-6 anchor block.  (Steps
    # 3-4, G_pre and companions, run inside build_anchor_block below.)
    mask_sha256 = hashlib.sha256(_MASK_ARTIFACT.read_bytes()).hexdigest()

    # Step 5: compute NLL gap on full j3
    print("Computing NLL gap on full j3 track...")
    nll_gap = _compute_nll_gap()
    print(f"  NLL gap (nll_scalar - nll_poly): {nll_gap:.6f}")

    # Step 6: assemble anchor block
    selection = fit_run["selection"]
    anchor = build_anchor_block(
        selection=selection,
        cal_json=field_d["calibration"],
        cal_key=cal_key,
        mask_sha256=mask_sha256,
        nll_gap_value=nll_gap,
    )

    # Drift guard: grid/hull literals must match the harness (fail loudly —
    # the anchor is the Phase-10 interface contract).
    _assert_grid_matches_harness(cal, anchor["companions"]["clip_engagement_fraction"])

    g_pre = anchor["g_pre"]
    print(f"\nG_pre = lane0_s_stat - winner_s_stat = {g_pre:.10f}")
    print(f"  lane0_s_stat = {float(selection['lane0_s_stat']):.10f}")
    winner = selection["winner"]
    winner_s = next(r["s_stat"] for r in selection["table"] if r["name"] == winner)
    print(f"  winner ({winner}) s_stat = {float(winner_s):.10f}")

    # Atomic write: set phase9.g_pre_anchor
    results["phase9"]["g_pre_anchor"] = anchor
    _atomic_write_json(_RESULTS, results)

    print(f"\n[OK] phase9.g_pre_anchor written to {_RESULTS}")
    print(
        f"  clip_engagement_fraction = "
        f"{anchor['companions']['clip_engagement_fraction']:.10f}"
    )
    print(
        f"  area_weighted_std_log_s  = "
        f"{anchor['companions']['area_weighted_std_log_s']:.10f}"
    )
    print(f"  log_s_range              = {anchor['companions']['log_s_range']:.10f}")
    print(
        f"  nll_gap_demoted.value    = "
        f"{anchor['companions']['nll_gap_demoted']['value']:.6f}"
    )


if __name__ == "__main__":
    main()
