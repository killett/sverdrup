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
    4. The UPGRADED one-touch / corrected-touch matrix (owner rider 3,
       2026-07-12): the corrected re-touch requires
       ``SVERDRUP_PHASE8_CORRECTED_TOUCH=1`` and is valid ONLY while the defect
       key ``phase8.c2_defect_run_20260712`` exists and ``phase8.c2_acceptance``
       is absent.  See :func:`check_touch_protocol` for the full 5-row matrix.

Scope discipline (owner rider 1, 2026-07-12 — one window/track source):
    The runner resolves ONE scope for the whole run, mirroring
    ``phase8_fit_run.py``'s ``SVERDRUP_PHASE8_SCOPE`` {dev,full} discipline.
    * ``full`` (DEFAULT) — the full challenge-year j3 box
      (``time_min="2017-01-01"`` .. ``time_max="2018-01-01"``), the SAME window
      the triplet (their_score) path evaluates.  The prior DEFECT-RUN read the
      21-day dev-window bounds from the fixture for the calibration block while
      the triplet path scored the full track — a partial-window mismatch.  Full
      scope closes that.
    * ``dev`` — REFUSED: a dev scope carries no c2 authorization semantics (the
      c2 track is touched ONCE, at full challenge scope, or not at all).  dev
      writes NOTHING to the gate JSON.

Window tripwire (owner rider 2, 2026-07-12 — pre-registered precondition):
    BEFORE any verdict computation, the loaded c2 evaluation set MUST match the
    full challenge scope: ``n_points == N_POINTS_FULL_YEAR`` (44,844 — the
    Task-19 full-year count, read from ``stage_b.c2_acceptance`` in the results
    JSON, not hard-coded) AND the loaded date range must span the challenge year
    (2017-01 .. 2017-12 within the challenge bounds).  A mismatch is a loud
    defect-STOP (record ``window_tripwire``, print banner, exit nonzero) — the
    silent partial-window class becomes a refusal, as bit-identity did for the
    framing class.

c2 loading path mirrors ``scripts/stage_miost_gate_run.py`` (the ``halo_obs``
grid-node framing per the Phase-7 fix is applied upstream to the maps being
scored; the scoring interp itself uses the shared their_eval loaders).  The
assimilation provenance guard (``assert_scored_not_assimilated``) is asserted on
every map->track scoring call.

Usage:
    SVERDRUP_MIOST_C2=1 SVERDRUP_PHASE8_CORRECTED_TOUCH=1 \
        pixi run python scripts/phase8_gate_run.py
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

# Full challenge-year j3 box time bounds (owner rider 1 — one window source).
# Mirrors phase8_fit_run._FULL_TMIN/_FULL_TMAX exactly; the triplet path already
# evaluates the whole track, so the calibration block must use the SAME window.
_FULL_TMIN, _FULL_TMAX = "2017-01-01", "2018-01-01"

# Window tripwire (owner rider 2): the loaded c2 set must span the challenge
# year — every loaded point falls in [CHALLENGE_TMIN, CHALLENGE_TMAX) AND the
# loaded min/max cover 2017-01 .. 2017-12.  A full year of j3 always straddles
# these month boundaries; a 21-day dev window cannot.
CHALLENGE_TMIN = np.datetime64("2017-01-01")
CHALLENGE_TMAX = np.datetime64("2018-01-01")
_COVER_MIN = np.datetime64("2017-01-31")  # loaded min must be <= end of Jan
_COVER_MAX = np.datetime64("2017-12-01")  # loaded max must be >= start of Dec

# The six pre-registered evaluation classes (mirror phase8_fit_run.py).
_EVAL_REGIONS = ("SW", "SE", "NW", "NE", "jet_core", "aggregate")

_ENV_FLAG = "SVERDRUP_MIOST_C2"
_SCOPE_FLAG = "SVERDRUP_PHASE8_SCOPE"
_CORRECTED_TOUCH_FLAG = "SVERDRUP_PHASE8_CORRECTED_TOUCH"

# Labeling (owner rider 3): the prior DEFECT-RUN is preserved under this key
# (context, never evidence); the corrected run writes a fresh phase8.c2_acceptance.
_DEFECT_KEY = "c2_defect_run_20260712"


class GateRefusal(SystemExit):
    """A pre-touch refusal: exits nonzero with a clear message, loads no data."""


class WindowTripwire(SystemExit):
    """A partial-window defect-STOP: the loaded c2 set is not the full year.

    Distinct from :class:`GateRefusal` — a tripwire fires AFTER the c2 touch has
    loaded the track (so it is not a pre-touch refusal), records a
    ``window_tripwire`` block, and exits nonzero.  It is a REFUSAL class in the
    same sense bit-identity is: the silent partial-window run is disqualified.
    """


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


def resolve_scope(env: dict[str, str] | None = None) -> str:
    """Resolve the ONE scope for the whole run (owner rider 1).

    Mirrors ``phase8_fit_run.py``'s ``SVERDRUP_PHASE8_SCOPE`` {dev,full}
    discipline.  ``full`` is the DEFAULT and the only scope with c2 semantics;
    ``dev`` is REFUSED because a dev scope carries no c2 authorization (the c2
    track is touched once, at full challenge scope, or not at all).

    Args:
        env: Environment mapping to read (defaults to ``os.environ``).

    Returns:
        ``"full"`` — the only scope under which the run proceeds.

    Raises:
        GateRefusal: If the scope is ``dev`` (no c2 authorization semantics) or
            any value other than ``dev``/``full``.
    """
    e = os.environ if env is None else env
    scope = e.get(_SCOPE_FLAG, "full")
    if scope == "full":
        return "full"
    if scope == "dev":
        raise GateRefusal(
            f"REFUSED: {_SCOPE_FLAG}=dev has no c2 authorization semantics — the "
            "c2 track is touched ONCE at full challenge scope, or not at all "
            "(dev writes nothing to the gate JSON). No data loaded."
        )
    raise GateRefusal(
        f"REFUSED: {_SCOPE_FLAG} must be 'dev' or 'full', got {scope!r}. "
        "No data loaded."
    )


def full_year_n_points(results: dict[str, Any]) -> int:
    """Return the Task-19 full-year c2 point count from the results JSON.

    The tripwire target is READ from the signed Stage-A record, never hard-coded
    blind: ``stage_b.c2_acceptance.calibration_at_frozen_s_star.n_points`` is the
    44,844 full-year count the Task-19 acceptance recorded on the whole c2 track.

    Args:
        results: The parsed gate results JSON.

    Returns:
        The full-year c2 point count (44,844 in the signed record).

    Raises:
        GateRefusal: If the recorded count is missing — the tripwire target
            cannot be established, so the touch must not proceed.
    """
    try:
        n = results["stage_b"]["c2_acceptance"]["calibration_at_frozen_s_star"][
            "n_points"
        ]
    except (KeyError, TypeError) as exc:
        raise GateRefusal(
            "REFUSED: full-year c2 point count "
            "(stage_b.c2_acceptance.calibration_at_frozen_s_star.n_points) "
            "missing — cannot establish the window-tripwire target. No data "
            "loaded."
        ) from exc
    return int(n)


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


def check_touch_protocol(
    results: dict[str, Any], env: dict[str, str] | None = None
) -> None:
    """Enforce the UPGRADED one-touch / corrected-touch matrix (owner rider 3).

    The prior DEFECT-RUN spent a touch; the corrected re-touch is authorized
    ONLY via ``SVERDRUP_PHASE8_CORRECTED_TOUCH=1`` and only while the defect key
    ``phase8.c2_defect_run_20260712`` exists and ``phase8.c2_acceptance`` is
    absent.  The full matrix (``C`` = corrected-touch flag set,
    ``A`` = c2_acceptance present, ``D`` = defect key present):

    ==========  =====  =====  ==================================================
    C           A      D      outcome
    ==========  =====  =====  ==================================================
    unset       yes    -      REFUSE — unchanged one-touch (defect run recorded)
    unset       no     -      REFUSE — one-touch: no bare re-invocation sanctioned
    set         yes    no     PROCEED — MIGRATE then re-evaluate (the current
                              real state: defect-run c2_acceptance is renamed to
                              the defect key, then a fresh evaluation runs)
    set         no     yes    PROCEED — the resume path (migration already done)
    set         yes    yes    REFUSE — third invocation (corrected already done)
    set         no     no     REFUSE — flag invalid without a recorded defect
    ==========  =====  =====  ==================================================

    This validates the touch *protocol* only; the deterministic migration (rename
    ``c2_acceptance`` -> ``phase8.c2_defect_run_20260712``) is applied by
    :func:`migrate_defect_run` on the PROCEED rows.

    Args:
        results: The parsed gate results JSON.
        env: Environment mapping to read (defaults to ``os.environ``).

    Raises:
        GateRefusal: On every REFUSE row above.
    """
    e = os.environ if env is None else env
    corrected = e.get(_CORRECTED_TOUCH_FLAG) == "1"
    phase8 = results.get("phase8", {})
    acceptance = "c2_acceptance" in phase8
    defect = _DEFECT_KEY in phase8

    if not corrected:
        # Unchanged one-touch: without the corrected flag, ANY existing
        # c2_acceptance refuses; a bare re-invocation without the flag is not
        # the sanctioned corrected path.
        if acceptance:
            raise GateRefusal(
                "REFUSED: phase8.c2_acceptance already exists — c2 has been "
                "touched once already. A corrected re-touch requires "
                f"{_CORRECTED_TOUCH_FLAG}=1 (owner rider 3, 2026-07-12); a bare "
                "re-invocation is owner-gated. No data loaded."
            )
        raise GateRefusal(
            f"REFUSED: {_CORRECTED_TOUCH_FLAG}=1 required — the corrected touch "
            "(touch 2) is the only sanctioned c2 invocation now (owner rider 3, "
            "2026-07-12). No data loaded."
        )

    # corrected flag is set from here.
    if not acceptance and not defect:
        raise GateRefusal(
            f"REFUSED: {_CORRECTED_TOUCH_FLAG}=1 is invalid without a recorded "
            f"defect — neither phase8.c2_acceptance nor phase8.{_DEFECT_KEY} "
            "exists, so there is nothing to correct. No data loaded."
        )
    if acceptance and defect:
        raise GateRefusal(
            "REFUSED: phase8.c2_acceptance already exists alongside "
            f"phase8.{_DEFECT_KEY} — the corrected touch has already run; a "
            "third invocation is owner-gated. No data loaded."
        )
    # Remaining PROCEED rows:
    #   acceptance & not defect  -> migrate then evaluate
    #   not acceptance & defect  -> resume (migration already applied)


def migrate_defect_run(results: dict[str, Any]) -> bool:
    """Rename the defect-run ``c2_acceptance`` to the defect key (owner rider 3).

    Deterministic migration applied on the corrected-touch PROCEED path: when a
    ``phase8.c2_acceptance`` exists but the defect key does not, the defect-run
    block is moved (in place, in *results*) to ``phase8.c2_defect_run_20260712``
    with a recorded defect note, freeing ``phase8.c2_acceptance`` for the fresh
    corrected evaluation.  Idempotent: if the defect key already exists (resume
    path), it is a no-op.

    Args:
        results: The parsed gate results JSON (mutated in place).

    Returns:
        True if a migration was applied; False if it was a no-op.
    """
    phase8 = results.setdefault("phase8", {})
    if _DEFECT_KEY in phase8 or "c2_acceptance" not in phase8:
        return False
    defect_block = phase8.pop("c2_acceptance")
    if isinstance(defect_block, dict):
        defect_block["defect"] = (
            "partial-window calibration (dev-scope time bounds); numbers are "
            "context, never evidence"
        )
        defect_block["defect_recorded"] = "2026-07-12"
    phase8[_DEFECT_KEY] = defect_block
    return True


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


def window_tripwire(
    n_points: int, times: np.ndarray, n_expected: int
) -> dict[str, Any]:
    """Assert the loaded c2 set is the FULL challenge year (owner rider 2).

    Called BEFORE any verdict computation.  Two pre-registered preconditions:

    1. ``n_points == n_expected`` — the loaded count equals the Task-19 recorded
       full-year count (44,844, READ from the results JSON, never hard-coded).
    2. The loaded date range spans the challenge year: every loaded time falls in
       ``[CHALLENGE_TMIN, CHALLENGE_TMAX)`` AND the loaded min/max cover
       2017-01 .. 2017-12 (min <= end-of-Jan, max >= start-of-Dec).  A 21-day
       dev window cannot satisfy the span; the DEFECT-RUN's 2,353 points cannot
       satisfy the count.

    Args:
        n_points: The loaded c2 point count.
        times: The loaded per-point times (datetime64).
        n_expected: The Task-19 full-year count read from the results JSON.

    Returns:
        A ``window_tripwire`` record (``{"passed": True, ...}``) when both
        preconditions hold — suitable for embedding in the acceptance block.

    Raises:
        WindowTripwire: On ANY mismatch — a loud defect-STOP (partial-window
            class becomes a refusal).  The message carries the record.
    """
    tt = np.asarray(times, dtype="datetime64[ns]")
    has_pts = bool(tt.size)
    tmin = tt.min() if has_pts else None
    tmax = tt.max() if has_pts else None
    in_bounds = (
        has_pts
        and bool((tt >= CHALLENGE_TMIN).all())
        and bool((tt < CHALLENGE_TMAX).all())
    )
    spans_year = (
        has_pts and bool(tt.min() <= _COVER_MIN) and bool(tt.max() >= _COVER_MAX)
    )
    n_ok = n_points == n_expected
    record: dict[str, Any] = {
        "passed": bool(n_ok and in_bounds and spans_year),
        "n_points_loaded": int(n_points),
        "n_points_expected": int(n_expected),
        "n_points_match": bool(n_ok),
        "loaded_time_min": str(tmin) if tmin is not None else None,
        "loaded_time_max": str(tmax) if tmax is not None else None,
        "challenge_time_min": str(CHALLENGE_TMIN),
        "challenge_time_max": str(CHALLENGE_TMAX),
        "in_challenge_bounds": in_bounds,
        "spans_challenge_year": spans_year,
        "semantics": (
            "owner rider 2 (2026-07-12): the loaded c2 set must be the FULL "
            "challenge year; a partial window is a defect-STOP (silent "
            "partial-window class becomes a refusal, as bit-identity did for "
            "the framing class)"
        ),
    }
    if not record["passed"]:
        raise WindowTripwire(
            "WINDOW-TRIPWIRE defect-STOP: the loaded c2 evaluation set is NOT "
            f"the full challenge year — n_points={n_points} (expected "
            f"{n_expected}), n_match={n_ok}, in_bounds={in_bounds}, "
            f"spans_year={spans_year}, loaded range {tmin}..{tmax}. This is the "
            "partial-window defect class; record written, exit nonzero."
        )
    return record


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
        time: np.ndarray,
    ) -> None:
        """Store per-point arrays; derive r2 and n from resid."""
        self.lon = lon
        self.lat = lat
        self.resid = resid
        self.r2 = resid**2
        self.v = v
        self.jet_pts = jet_pts
        self.time = np.asarray(time, dtype="datetime64[ns]")
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

    # Owner rider 1 — ONE window source: the FULL challenge-year bounds (the
    # SAME window the triplet/their_score path scores), NOT the 21-day dev-window
    # time bounds the fixture carries. The fixture's time_min/time_max are the dev
    # window that spent the DEFECT-RUN; they are used ONLY behind the dev flag,
    # which this runner refuses for c2 (see resolve_scope).
    box = dict(
        lon_min=295.0,
        lon_max=305.0,
        lat_min=33.0,
        lat_max=43.0,
        time_min=_FULL_TMIN,
        time_max=_FULL_TMAX,
    )
    ds_at = read_l3_dataset(str(c2_track), **box)
    time_a, lat_a, lon_a, ssh, mu = interp_on_alongtrack(
        str(MEAN_NC), ds_at, is_circle=False, **box
    )
    _, _, _, _, var = interp_on_alongtrack(str(VAR_NC), ds_at, is_circle=False, **box)
    ssh, mu, var = (np.asarray(a, float) for a in (ssh, mu, var))
    lat_a, lon_a = np.asarray(lat_a, float), np.asarray(lon_a, float)
    time_a = np.asarray(time_a)
    ok = np.isfinite(ssh) & np.isfinite(mu) & np.isfinite(var) & (var > 0)

    lon, lat, resid, v, tt = (
        np.asarray(a)[ok] for a in (lon_a, lat_a, ssh - mu, var, time_a)
    )

    jet_cells = _jet_cell_mask()
    row, col = R.cell_index(lon, lat)
    jet_pts = jet_cells[row, col]

    return Track(lon, lat, resid, v, jet_pts, tt)


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


def _run_refusal_checks() -> tuple[dict[str, Any], dict[str, Any], list[float], int]:
    """Run every refusal check BEFORE any data load.

    Order (all pure, no c2 / track data touched):
        1. ``SVERDRUP_MIOST_C2=1`` (fresh authorization).
        2. Scope resolution — full is the ONLY scope with c2 semantics; dev
           refuses (owner rider 1).
        3. Field presence + cal_key self-consistency.
        4. ``negative_result`` guard.
        5. The upgraded corrected-touch protocol matrix (owner rider 3).
        6. Read the Task-19 full-year count (the window-tripwire target).
        7. Read the signed Stage-A reference triplet.

    Returns:
        (results, field, stage_a_reference_triplet, n_expected_full_year).

    Raises:
        GateRefusal: On the first failing check (nonzero exit, no data loaded).
    """
    check_authorized()
    resolve_scope()  # refuses dev; only full carries c2 authorization semantics
    field = check_field_self_consistent(FIELD_IN)
    results = json.loads(RESULTS.read_text())
    check_not_negative_result(results)
    check_touch_protocol(results)
    n_expected = full_year_n_points(results)
    ref = stage_a_reference_triplet(results)
    return results, field, ref, n_expected


def main() -> None:
    """Run the owner-gated corrected c2 touch; write phase8.c2_acceptance."""
    # --- Refusal gate FIRST: cheap, pure, loads no c2 / track data. ---------
    results, field, stage_a_ref, n_expected = _run_refusal_checks()

    # Deterministic migration (owner rider 3): rename the DEFECT-RUN
    # c2_acceptance to the defect key BEFORE the fresh evaluation writes a new
    # c2_acceptance. No-op on the resume path (defect key already present).
    migrated = migrate_defect_run(results)
    if migrated:
        _atomic_write_json(RESULTS, results)

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

    # --- WINDOW TRIPWIRE (owner rider 2) — BEFORE any verdict computation. ---
    # A partial window (dev bounds / DEFECT-RUN counts) is a loud defect-STOP.
    try:
        tripwire = window_tripwire(trk.n, trk.time, n_expected)
    except WindowTripwire as exc:
        record = {
            "window_tripwire": {
                "passed": False,
                "n_points_loaded": int(trk.n),
                "n_points_expected": int(n_expected),
                "loaded_time_min": str(trk.time.min()) if trk.n else None,
                "loaded_time_max": str(trk.time.max()) if trk.n else None,
                "message": str(exc),
            }
        }
        results.setdefault("phase8", {})
        results["phase8"]["c2_acceptance"] = {
            "verdict": "WINDOW-TRIPWIRE",
            **record,
            "semantics": (
                "owner rider 2 defect-STOP: loaded c2 set is not the full "
                "challenge year; numbers are NOT gate evidence"
            ),
        }
        _atomic_write_json(RESULTS, results)
        print("=" * 72)
        print("PHASE-8 c2 WINDOW-TRIPWIRE — DEFECT-STOP")
        print("=" * 72)
        print(str(exc))
        print("=" * 72)
        raise

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
        "window_tripwire": tripwire,
        "coverage_target": COVERAGE_TARGET,
        "coverage_tol": COVERAGE_TOL,
        "regional_table": regional,
        "verdict": verdict,
        "semantics": (
            "the corrected Phase-8 c2 touch (owner-authorized 2026-07-12, touch "
            "2; poly field frozen from j3 evidence; NOTHING refit on c2; triplet "
            "is calibration-inert so must reproduce signed Stage-A bit-identically; "
            "coverage read at s(x)·v + SIGMA_OBS2 over the FULL challenge year)"
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
    except (GateRefusal, WindowTripwire) as exc:
        print(str(exc), file=sys.stderr)
        raise
