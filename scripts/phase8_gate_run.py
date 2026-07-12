"""Phase-8 OWNER GATE: the single c2 touch of the FROZEN spatial field.

Spec §7 step 5 / plan Task 11.  This runner scores the field-calibrated shipped
MIOST product on the LOCKED c2 track EXACTLY ONCE, applies the owner's
pre-registered reading verbatim, and records ``phase8.c2_acceptance`` into the
gate JSON.  It refits NOTHING: the calibration field is loaded byte-exact from
``phase8_field.json`` (its ``cal_key`` asserted self-consistent), and the frozen
poly winner is what gets scored.

Owner protocol (PROGRESS.md top banner, PROCEED-TO-TOUCH ruling 2026-07-11):
    * The (µ, σ, λx) triplet is calibration-INERT (the mean path is untouched by
      the √s seam), so it MUST reproduce the signed Stage-A values
      BIT-IDENTICALLY.  ANY deviation is a defect — write the record, print the
      DEFECT-STOP banner, exit nonzero.  The reference triplet is read at
      full precision from the gate JSON (stage_b.c2_acceptance), not hard-coded.
    * Aggregate c2 coverage at ``s(x)·v + SIGMA_OBS2`` (v = RAW c2-interp
      variance) within 0.6827±0.10 -> verdict SIGN-OFF; outside -> verdict HOLD
      (recorded, NO refit, exit 0 — owner call).
    * Regional c2 coverage breakdown (6 evaluation classes), reduced chi2, and
      CRPS are report-only — NEVER gating.

Refusal discipline (ALL checks fire BEFORE any c2 / track data is loaded):
    1. ``SVERDRUP_MIOST_C2`` must equal "1" (fresh owner authorization; the
       Task-10 PROCEED does not pre-authorize).  Without it: refuse, exit
       nonzero, load NOTHING.
    2. ``phase8_field.json`` must exist; its ``cal_key`` must pass the
       self-consistency check ``calibration_from_json(to_json).key() == cal_key``.
    3. The evidence JSON must not record
       ``phase8.fit_run.selection.negative_result: true``.
    4. ``phase8.c2_acceptance`` must NOT already exist — one-touch discipline; a
       second invocation refuses (owner adjudication required).

c2 loading path mirrors ``scripts/stage_miost_gate_run.py`` (the ``halo_obs``
grid-node framing per the Phase-7 fix is applied upstream to the maps being
scored; the scoring interp itself uses the shared their_eval loaders).  The
assimilation provenance guard (``assert_scored_not_assimilated``) is asserted on
every map->track scoring call.

Usage:
    SVERDRUP_MIOST_C2=1 pixi run python scripts/phase8_gate_run.py
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from sverdrup.application.calibration import regions as R
from sverdrup.application.calibration.constants import (
    COVERAGE_TARGET,
    COVERAGE_TOL,
    SIGMA_OBS2,
)
from sverdrup.distributions.miost_ensemble import (
    CalibrationField,
    calibration_from_json,
)

# ---------------------------------------------------------------------------
# Paths / constants (module-level so tests can monkeypatch them)
# ---------------------------------------------------------------------------

ROOT = Path("data/2021a_ssh_mapping_ose/ours")
RESULTS = ROOT / "stage_miost_gate_results.json"
MEAN_NC = ROOT / "stage_b_mean_maps.nc"
VAR_NC = ROOT / "stage_b_var_maps.nc"
JET_MASK = ROOT / "phase8_jet_core_mask.json"
FIELD_IN = ROOT / "phase8_field.json"
SCOPE_FIX = Path("tests/validation/fixtures/stage_a_scope.json")

EPOCH = np.datetime64("2017-01-01")

# The six pre-registered evaluation classes (mirror phase8_fit_run.py).
_EVAL_REGIONS = ("SW", "SE", "NW", "NE", "jet_core", "aggregate")

_ENV_FLAG = "SVERDRUP_MIOST_C2"


class GateRefusal(SystemExit):
    """A pre-touch refusal: exits nonzero with a clear message, loads no data."""


# ---------------------------------------------------------------------------
# Refusal checks (pure — no data load; fire BEFORE any c2 touch)
# ---------------------------------------------------------------------------


def check_authorized(env: dict[str, str] | None = None) -> None:
    """Require fresh owner authorization via ``SVERDRUP_MIOST_C2=1``.

    Args:
        env: Environment mapping to read (defaults to ``os.environ``).

    Raises:
        GateRefusal: If the flag is not exactly "1".  Task-10 PROCEED does not
            pre-authorize — the flag is the fresh, per-touch authorization.
    """
    e = os.environ if env is None else env
    if e.get(_ENV_FLAG) != "1":
        raise GateRefusal(
            f"REFUSED: {_ENV_FLAG}=1 required (fresh owner authorization for the "
            "single c2 touch; Task-10 PROCEED does not pre-authorize). No data "
            "loaded."
        )


def check_field_self_consistent(field_path: Path) -> dict[str, Any]:
    """Load ``phase8_field.json`` and assert its ``cal_key`` is self-consistent.

    The field is loaded byte-exact: the persisted ``calibration`` block is
    round-tripped through ``calibration_from_json`` and its recomputed key must
    equal the recorded ``cal_key`` (``from_json(to_json).key() == cal_key``).

    Args:
        field_path: Path to the winner field artifact.

    Returns:
        The parsed field dict (``{"calibration": ..., "cal_key": ...}``).

    Raises:
        GateRefusal: If the file is absent, malformed, or the key mismatches.
    """
    if not field_path.exists():
        raise GateRefusal(
            f"REFUSED: winner field {field_path} absent — nothing to score. "
            "No data loaded."
        )
    try:
        field = json.loads(field_path.read_text())
        cal_json = field["calibration"]
        cal_key = field["cal_key"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise GateRefusal(
            f"REFUSED: winner field {field_path} malformed ({exc!r}). No data loaded."
        ) from exc
    cal = calibration_from_json(cal_json)
    recomputed = cal.key()
    if recomputed != cal_key:
        raise GateRefusal(
            "REFUSED: winner field cal_key is not self-consistent — "
            f"calibration_from_json(to_json).key()={recomputed!r} != recorded "
            f"cal_key={cal_key!r}. No data loaded."
        )
    result: dict[str, Any] = field
    return result


def check_not_negative_result(results: dict[str, Any]) -> None:
    """Refuse if the fit run recorded a NEGATIVE RESULT.

    Args:
        results: The parsed gate results JSON.

    Raises:
        GateRefusal: If ``phase8.fit_run.selection.negative_result`` is true —
            there is no winner to accept; Task 13 closes instead.
    """
    negative = (
        results.get("phase8", {})
        .get("fit_run", {})
        .get("selection", {})
        .get("negative_result", False)
    )
    if negative:
        raise GateRefusal(
            "REFUSED: phase8.fit_run.selection.negative_result is true — no "
            "winner field to accept on c2; Task 13 closes the phase. No data "
            "loaded."
        )


def check_not_already_touched(results: dict[str, Any]) -> None:
    """Enforce one-touch discipline: refuse a second c2 acceptance.

    Args:
        results: The parsed gate results JSON.

    Raises:
        GateRefusal: If ``phase8.c2_acceptance`` already exists.  A second
            invocation must not silently re-touch c2 — owner adjudication is
            required.
    """
    if "c2_acceptance" in results.get("phase8", {}):
        raise GateRefusal(
            "REFUSED: phase8.c2_acceptance already exists — c2 has been touched "
            "once already. A second touch is owner-gated (no standing "
            "authorization); owner adjudication required. No data loaded."
        )


def stage_a_reference_triplet(results: dict[str, Any]) -> list[float]:
    """Return the signed Stage-A (µ, σ, λx) triplet at full precision.

    The signed acceptance triplet is stored in ``stage_b.c2_acceptance`` (the
    Stage-A/Task-19 acceptance).  Its ``stage_a_reference`` field carries the
    canonical full-precision floats; the mean path is calibration-inert, so the
    Phase-8 c2 triplet must reproduce THESE exactly.

    Args:
        results: The parsed gate results JSON.

    Returns:
        ``[mu, sigma, lambda_x]`` as stored, full precision (never rounded).

    Raises:
        GateRefusal: If the reference triplet is missing.
    """
    try:
        ref = results["stage_b"]["c2_acceptance"]["stage_a_reference"]
    except (KeyError, TypeError) as exc:
        raise GateRefusal(
            "REFUSED: signed Stage-A reference triplet "
            "(stage_b.c2_acceptance.stage_a_reference) missing — cannot apply "
            "the bit-identity reading. No data loaded."
        ) from exc
    return [float(x) for x in ref]


# ---------------------------------------------------------------------------
# Thin pure glue (mirrors phase8_fit_run.py — same conventions, same numerics)
# ---------------------------------------------------------------------------


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


def coverage_verdict(aggregate_coverage: float) -> str:
    """Apply the pre-registered coverage reading: SIGN-OFF vs HOLD.

    Args:
        aggregate_coverage: Aggregate 1σ c2 coverage at s(x)·v + SIGMA_OBS2.

    Returns:
        "SIGN-OFF" iff coverage is within COVERAGE_TARGET±COVERAGE_TOL, else
        "HOLD".
    """
    if abs(aggregate_coverage - COVERAGE_TARGET) <= COVERAGE_TOL:
        return "SIGN-OFF"
    return "HOLD"


# ---------------------------------------------------------------------------
# c2 track loader (mirrors phase8_fit_run.load_track / stage_miost_gate_run)
# ---------------------------------------------------------------------------


def _jet_cell_mask() -> np.ndarray:
    """Load the pre-registered (5,5) jet-core cell mask artifact."""
    d = json.loads(JET_MASK.read_text())
    return np.asarray(d["mask"], dtype=bool)


class Track:
    """Loaded c2 track arrays after finite/positive-var masking."""

    def __init__(
        self,
        lon: np.ndarray,
        lat: np.ndarray,
        resid: np.ndarray,
        v: np.ndarray,
        jet_pts: np.ndarray,
    ) -> None:
        """Store per-point arrays; derive r2 and n from resid."""
        self.lon = lon
        self.lat = lat
        self.resid = resid
        self.r2 = resid**2
        self.v = v
        self.jet_pts = jet_pts
        self.n = int(resid.size)

    def eval_masks(self) -> dict[str, np.ndarray]:
        """Return the 6 pre-registered evaluation-class point masks."""
        return R.evaluation_masks(self.lon, self.lat, self.jet_pts)


def load_c2_track() -> Track:
    """Interp the shipped mean/var maps on the LOCKED c2 track and build arrays.

    Mirrors the loaders, box, and RAW-variance convention of
    ``scripts/stage_miost_gate_run.py::_interp_mean_var_on_track`` and
    ``phase8_fit_run.load_track``.  The scored maps carry the assimilation
    provenance guard (``assert_scored_not_assimilated``) on BOTH the mean and
    var interp — this is the single, authorized c2 touch.

    Returns:
        A :class:`Track` with per-point lon/lat/resid/v plus per-point jet-core
        membership.
    """
    import sverdrup.validation.their_eval as te
    from sverdrup.validation.provenance_guard import assert_scored_not_assimilated

    cfg = json.loads(SCOPE_FIX.read_text())
    c2_track = Path(cfg["c2_track_path"])  # LOCKED c2 — touched ONCE, here.
    assert_scored_not_assimilated(MEAN_NC, c2_track)
    assert_scored_not_assimilated(VAR_NC, c2_track)

    te._prepare_imports()
    from src.mod_inout import read_l3_dataset
    from src.mod_interp import interp_on_alongtrack

    box = dict(
        lon_min=295.0,
        lon_max=305.0,
        lat_min=33.0,
        lat_max=43.0,
        time_min=cfg["time_min"],
        time_max=cfg["time_max"],
    )
    ds_at = read_l3_dataset(str(c2_track), **box)
    _, lat_a, lon_a, ssh, mu = interp_on_alongtrack(
        str(MEAN_NC), ds_at, is_circle=False, **box
    )
    _, _, _, _, var = interp_on_alongtrack(str(VAR_NC), ds_at, is_circle=False, **box)
    ssh, mu, var = (np.asarray(a, float) for a in (ssh, mu, var))
    lat_a, lon_a = np.asarray(lat_a, float), np.asarray(lon_a, float)
    ok = np.isfinite(ssh) & np.isfinite(mu) & np.isfinite(var) & (var > 0)

    lon, lat, resid, v = (np.asarray(a)[ok] for a in (lon_a, lat_a, ssh - mu, var))

    jet_cells = _jet_cell_mask()
    row, col = R.cell_index(lon, lat)
    jet_pts = jet_cells[row, col]

    return Track(lon, lat, resid, v, jet_pts)


def _regional_table(cal: CalibrationField, trk: Track) -> dict[str, dict[str, float]]:
    """Return per-eval-region c2 coverage + reduced chi2 + CRPS (report-only)."""
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
            "crps": _gaussian_crps(trk.resid[mm], vt[mm]),
        }
    return out


# ---------------------------------------------------------------------------
# Atomic JSON write (mirrors phase8_fit_run._atomic_write_json)
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


def _atomic_write_json(path: Path, data: object) -> None:
    """Write *data* as JSON to *path* atomically (POSIX os.replace)."""
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
# Orchestration
# ---------------------------------------------------------------------------


def _run_refusal_checks() -> tuple[dict[str, Any], dict[str, Any], list[float]]:
    """Run every refusal check BEFORE any data load.

    Returns:
        (results, field, stage_a_reference_triplet) once all checks pass.

    Raises:
        GateRefusal: On the first failing check (nonzero exit, no data loaded).
    """
    check_authorized()
    field = check_field_self_consistent(FIELD_IN)
    results = json.loads(RESULTS.read_text())
    check_not_negative_result(results)
    check_not_already_touched(results)
    ref = stage_a_reference_triplet(results)
    return results, field, ref


def main() -> None:
    """Run the owner-gated single c2 touch; write phase8.c2_acceptance."""
    # --- Refusal gate FIRST: cheap, pure, loads no c2 / track data. ---------
    results, field, stage_a_ref = _run_refusal_checks()
    cal = calibration_from_json(field["calibration"])
    cal_key = field["cal_key"]

    # --- The single c2 touch: score the frozen field-calibrated product. ----
    from sverdrup.validation.their_eval import score as their_score

    cfg = json.loads(SCOPE_FIX.read_text())
    c2_track = Path(cfg["c2_track_path"])

    # The (µ, σ, λx) triplet is calibration-inert; scored via their_eval.
    triplet = [float(x) for x in their_score(MEAN_NC, c2_track)]
    bit_identical = triplet == stage_a_ref

    # Held-out c2 coverage / chi2 / CRPS on s(x)·v + SIGMA_OBS2 for the field.
    trk = load_c2_track()
    vt = _var_track(cal, trk.lon, trk.lat, trk.v)
    nc, nt = _coverage_count(trk.resid, vt)
    aggregate_coverage = nc / nt
    aggregate_chi2 = float(np.mean(trk.r2 / vt))
    aggregate_crps = _gaussian_crps(trk.resid, vt)
    regional = _regional_table(cal, trk)

    if not bit_identical:
        verdict = "DEFECT-STOP"
    else:
        verdict = coverage_verdict(aggregate_coverage)

    acceptance = {
        "cal_key": cal_key,
        "mu_sigma_lambda_x": triplet,
        "stage_a_reference": stage_a_ref,
        "reproduces_stage_a": bit_identical,
        "aggregate_coverage_1sigma": aggregate_coverage,
        "aggregate_reduced_chi2": aggregate_chi2,
        "aggregate_crps": aggregate_crps,
        "n_points": int(nt),
        "coverage_target": COVERAGE_TARGET,
        "coverage_tol": COVERAGE_TOL,
        "regional_table": regional,
        "verdict": verdict,
        "semantics": (
            "the ONE Phase-8 c2 touch (owner-authorized; poly field frozen from "
            "j3 evidence; NOTHING refit on c2; triplet is calibration-inert so "
            "must reproduce signed Stage-A bit-identically; coverage read at "
            "s(x)·v + SIGMA_OBS2)"
        ),
    }

    # Write the record atomically REGARDLESS of verdict (defect is recorded too).
    results.setdefault("phase8", {})
    results["phase8"]["c2_acceptance"] = acceptance
    _atomic_write_json(RESULTS, results)

    _print_banner(acceptance)

    if verdict == "DEFECT-STOP":
        raise SystemExit(
            f"DEFECT-STOP: c2 triplet {triplet} deviates from signed Stage-A "
            f"{stage_a_ref} — mean path is calibration-inert, so any deviation "
            "is a defect. Record written; owner must adjudicate."
        )
    # SIGN-OFF and HOLD both exit 0 (HOLD is an owner call, not a failure).


def _print_banner(acceptance: dict[str, Any]) -> None:
    """Print the human summary table + verdict banner."""
    v = acceptance["verdict"]
    print("=" * 72)
    print("PHASE-8 c2 ACCEPTANCE — the single owner-gated touch")
    print("=" * 72)
    print(f"cal_key: {acceptance['cal_key']}")
    t = acceptance["mu_sigma_lambda_x"]
    r = acceptance["stage_a_reference"]
    print(f"triplet (mu,sigma,lambda_x): {t}")
    print(f"stage-A reference          : {r}")
    print(f"reproduces_stage_a (bit-identical): {acceptance['reproduces_stage_a']}")
    print(
        f"aggregate coverage: {acceptance['aggregate_coverage_1sigma']:.4f} "
        f"(target {acceptance['coverage_target']}±{acceptance['coverage_tol']}) "
        f"chi2_red={acceptance['aggregate_reduced_chi2']:.4f} "
        f"crps={acceptance['aggregate_crps']:.6f} n={acceptance['n_points']}"
    )
    print("-" * 72)
    print(
        f"{'region':>10} {'n':>7} {'coverage':>10} {'deficit':>9} "
        f"{'chi2_red':>9} {'crps':>9}"
    )
    for reg in _EVAL_REGIONS:
        row = acceptance["regional_table"].get(reg)
        if row is None:
            continue
        print(
            f"{reg:>10} {row['n']:>7} {row['coverage']:>10.4f} "
            f"{row['deficit']:>9.4f} {row['reduced_chi2']:>9.4f} "
            f"{row['crps']:>9.6f}"
        )
    print("-" * 72)
    if v == "DEFECT-STOP":
        print("VERDICT: DEFECT-STOP — triplet not bit-identical; owner adjudication.")
    elif v == "SIGN-OFF":
        print("VERDICT: SIGN-OFF — aggregate c2 coverage within pre-registered band.")
    else:
        print("VERDICT: HOLD — coverage outside band; recorded, NO refit, owner call.")
    print("=" * 72)


if __name__ == "__main__":
    try:
        main()
    except GateRefusal as exc:
        print(str(exc), file=sys.stderr)
        raise
