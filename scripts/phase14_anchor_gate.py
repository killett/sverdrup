"""Phase-14 Stage-1 ANCHOR IDENTITY GATE (Task 3) — the stage's HARD BARRIER.

SPEC §10; NOTHING downstream runs until this is green. The gate is NOT
"five green": per the owner ruling of 2026-07-26, SPEC §10 check 3 is
SPLIT into a surface-identity check that passes on its own terms and the
era no-op, which is UNRUNNABLE at Stage 1 and therefore DEFERRED. What the
block records is :data:`ACCOUNTING`: TWO checks run and passed, TWO cited
and pre-ratified at Gate 0, ONE proxy-passed with the specified check
deferred. A deferred check is neither a pass nor a fail — it never counts
toward green.

1. **Tiling identity (runs now):** the anchor tile through the generalized
   tiling path (``anchor_frame()`` → ``frame_grid`` → ``frame_obs`` →
   ``Miost(basis_domain=solve bbox km)``, full 9-window production plan,
   m=100) ≡ the signed phase-13 acceptance records, four routes: member
   coefficient arrays sha-equal vs ``phase13_winner_members.npz``; mean
   maps vs ``phase13_winner_mean.nc`` rtol 1e-12; Γ-route (chunked
   ``mean_at``, day 0 — the Phase-13 T3 precedent); variance route vs
   ``phase13_winner_var.nc`` rtol 1e-12. Obs-identity and basis-spec
   identity are asserted BEFORE the member solves (fail fast, never after
   seven hours).
2. **Loader identity (Stage-0 complete — cited):** evidence
   ``phase14.stage0.gate2_loader_identity`` (pass) + the golden-tile
   TABLED row (the lineage-sensitivity half). The block cites both nodes,
   runs nothing.
3. **SPLIT (owner ruling 2026-07-26).** ``surface_identity`` **(runs now,
   PASS ON ITS OWN TERMS):** the shipped calibration surface vs the signed
   s(x) artifact, descriptor byte-equal AND values asserted ``==`` (an
   identity, not a tolerance) — it proves no drift in the shipped
   calibration surface, and claims nothing else. ``era_noop`` **(DEFERRED):**
   the specified §10 check 3 has no Stage-1 instantiation (no era-keyed
   calibration code exists), so it is recorded ``status: "deferred"``,
   ``pass: null``, deferred to the stage that introduces era-keyed code and
   re-entering that stage's coverage walk (the T11 deferral discipline).
   The superseded proxy-pass recording rides inside it, verbatim.
4. **Cross-env (cited + pending slot):** T17 same-host CRN manifests
   (recomputed EQUAL) cited; cross-host slot recorded ``pending-T18`` per
   the Gate-0 ruling — GREEN with the slot EXPLICITLY pending, never
   silently.
5. **Score-level identity (runs now):** ``score_tile`` on the anchor maps
   ≡ ``their_eval.score`` at rtol 1e-12 on (µ, σ, λx); the gate-5
   constants PIN NOW (write-once) into ``phase14.stage1.gate5``.

PIN 23: any anchor solve leg exiting at the iteration cap over rtol is
RECORDED (never a silent stop), the script exits :data:`EXIT_PIN23`, and
that is an IMMEDIATE owner STOP separate from a plain check failure.

Zero touches: the locked tally (legacy ``c2_touch_tally`` + the phase-14
``locked_n`` ledger) is snapshotted before the run and asserted
byte-identical after every write.

Root provenance: see :data:`ROOT_NOTE` and :func:`root_conditionality`
(pin 30 — the member route proves reproduction UNDER the acceptance root,
never root-independence; variance inherits that conditionality; the mean
and Γ routes are root-independent). Recorded deviation for the owner
walk — the four-route reference store pins the phase-13 acceptance root).
"""

from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import numpy as np
import typer

if TYPE_CHECKING:
    from types import ModuleType

    from sverdrup.application.spatial_tiles import TileFrame
    from sverdrup.core.grid import GridSpec
    from sverdrup.core.observations import ObsWindow
    from sverdrup.distributions.calibration import PolyCalibration

app = typer.Typer(add_completion=False)

EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
OURS = Path("data/2021a_ssh_mapping_ose/ours")
STAGE1_DIR = OURS / "phase14_stage1"
ANCHOR_SIGNED_MAPS = STAGE1_DIR / "anchor_signed_maps.nc"
ANCHOR_MEMBER_STD = STAGE1_DIR / "anchor_member_std_maps.nc"
# This leg's own solve output (crash-resume substrate — never a reference).
OWN_STORE = STAGE1_DIR / "anchor_gate_member_store.npz"

# The signed reference records (phase-13 acceptance, T11 winner ensemble;
# evidence node phase13.miost.members names all three).
WINNER_MEAN = OURS / "phase13_winner_mean.nc"
WINNER_VAR = OURS / "phase13_winner_var.nc"
WINNER_MEMBERS = OURS / "phase13_winner_members.npz"
SIGNED_FIELD_JSON = OURS / "phase13_field_miost.json"

# T17 same-host cross-env halves (check 4 citations).
CRN_MANIFEST_A = OURS / "phase14_probe" / "crn_manifest_host1.json"
CRN_MANIFEST_B = OURS / "phase14_probe" / "crn_manifest_host1b.json"

OBS_DIR = Path("data/2021a_ssh_mapping_ose/dc_obs")
J3_TRACK = OBS_DIR / "dt_gulfstream_j3_phy_l3_20161201-20180131_285-315_23-53.nc"
# The SIX-FILE MDT list — the signed scorer's convention (the five-file
# variant shifts µ at 4e-6 and would break signed-map reproduction).
MAPPING_SIX = tuple(
    OBS_DIR / f"dt_gulfstream_{m}_phy_l3_20161201-20180131_285-315_23-53.nc"
    for m in ("alg", "h2g", "j2g", "j2n", "j3", "s3a")
)
MAPPING_FIVE = ("alg", "h2g", "j2g", "j2n", "s3a")

RESOLUTION_DEG = 0.2
M_MEMBERS = 100
ROUTE_RTOL = 1e-12
N_DAYS = 365
GAMMA_DAY = 0.0  # the Phase-13 T3 Γ-route precedent (day 0, one window)
_GAMMA_CHUNK = 100  # the recorded OOM lesson: never one whole-grid evaluate

REQUIRED_CHECKS = (
    "tiling_identity",
    "loader_identity",
    "cross_env",
    "score_identity",
    "surface_identity",
    "era_noop",
)
_STATUSES = ("pass", "fail", "cited", "deferred")
# A deferral must name where it goes and where it comes back (T11).
_DEFERRAL_KEYS = ("deferred_to", "reappears_in")
# Checks the owner ruled UNRUNNABLE here: recordable as deferred (or, if a
# future stage runs them, as a fail) but NEVER as a pass — the whole point
# of the 2026-07-26 split is that a proxy cannot masquerade as the
# specified check.
NEVER_PASS_HERE = ("era_noop",)

EXIT_FAIL = 1
EXIT_PIN23 = 3

SURFACE_IDENTITY_NAME = "shipped calibration surface identity (PASS ON ITS OWN TERMS)"
SURFACE_IDENTITY_PROVES = (
    "no drift in the shipped calibration surface through the generalized "
    "tiling path vs the signed s(x) record (phase13_field_miost.json) — "
    "exact, never a tolerance"
)

ERA_NOOP_NAME = "era-machinery no-op (SPEC §10 check 3)"
ERA_NOOP_DEFERRED_TO = (
    "the stage that introduces era-keyed code (Stage 2 per spec §3.1 fork E)"
)
ERA_NOOP_WHY = (
    "UNRUNNABLE at Stage 1: no era-keyed calibration instantiation exists "
    "(fork-e pin 1's density-factor covariate exists as design, not code). "
    "A proxy recorded as PASS becomes 'check 3 passed' three documents "
    "downstream — owner ruling 2026-07-26"
)
ERA_NOOP_REAPPEARS_IN = (
    "the introducing stage's own coverage walk (the T11 deferral "
    "discipline, established for exactly this situation)"
)
ERA_NOOP_SPEC_CITATION = "spec §10 check 3; fork-e pin 1 (density factor ≡ 1 at n_eff₀)"

# What the block states about itself, so a Stage-2 reader counts the checks
# the way the owner ruled them rather than reading a bare pass=True as
# "five green".
ACCOUNTING: dict[str, Any] = {
    "ruling": "owner 2026-07-26 — the gate is NOT 'five green'",
    "run_and_passed": ["tiling_identity", "score_identity"],
    "cited_and_pre_ratified_at_gate0": ["loader_identity", "cross_env"],
    "proxy_passed_specified_check_deferred": [
        "surface_identity (pass) / era_noop (deferred)"
    ],
    "statement": (
        "TWO checks run and passed (1, 5), TWO cited and pre-ratified at "
        "Gate 0 (2, 4), ONE proxy-passed with the specified check deferred "
        "(3). This accounting survives careful reading in Stage 2; 'five "
        "green' does not."
    ),
}

# The reading check 3 carried BEFORE the split — preserved (never deleted)
# inside the deferred block so the superseded claim stays auditable.
SUPERSEDED_CHECK3_READING = (
    "RECORDED READING (flagged for the owner walk): the era-keyed "
    "calibration machinery has no Stage-1 instantiation yet (fork-e pin 1's "
    "density-factor covariate exists as design, not code). Check 3 is "
    "therefore the IDENTITY of the shipped calibration surface through the "
    "generalized path vs the signed s(x) artifact phase13_field_miost.json "
    "— descriptor byte-equal AND surface values exactly equal (==, never a "
    "tolerance). This IS the n_eff0 no-op by construction: density factor "
    "== 1 at the reference epoch means era-keyed s(x) == signed s(x)."
)

ROOT_NOTE = (
    "ROOT DEVIATION RECORDED for the owner walk: the plan text names "
    "derive_seed('miost','stage-b-winner','members',0) = 4836134738817689931 "
    "(the T17 cross-env subject root), but the signed acceptance member "
    "store phase13_winner_members.npz was generated at the phase-13 "
    "acceptance root derive_seed('miost','phase13-winner','members',0) = "
    "7742201642112487637 (evidence phase13.miost.members.root_int; "
    "shipped_miost5().member_root). The four routes compare against the "
    "phase-13 acceptance artifacts, so this run uses the phase-13 "
    "acceptance root; the mean and Gamma routes are root-independent."
)

CROSS_HOST_PENDING = "pending-T18"
CHECK4_RULING = (
    "Gate-0 ruling item 2: Gate 0 closed WITH the cloud leg open — "
    "restructured as a ladder-enforced precondition on first Tier-2 "
    "production use; C0->1 ships same-host tolerances + CRN-EQUAL now; "
    "cross-host slot marked pending-T18; credentials owner-side."
)


# ---------------------------------------------------------------------------
# Pure machinery (CI-tested)
# ---------------------------------------------------------------------------


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_array(arr: np.ndarray) -> str:
    """Sha256 of an array's contiguous bytes (hash equality == byte equality).

    Args:
        arr: Array to hash.

    Returns:
        Hex digest.
    """
    return _sha_bytes(np.ascontiguousarray(arr).tobytes())


def sha256_file(path: Path) -> str:
    """Sha256 of a file's bytes.

    Args:
        path: File to hash.

    Returns:
        Hex digest.
    """
    return _sha_bytes(path.read_bytes())


def snapshot_locked_tally(evidence_path: Path) -> str:
    """Canonical serialization of every locked-tally node in the store.

    Covers the legacy top-level ``c2_touch_tally`` AND the phase-14
    locked-tier ``phase14.locked_n`` ledger — the zero-touch guarantee is
    over both.

    Args:
        evidence_path: The evidence store.

    Returns:
        A canonical JSON string (the byte-identity token).
    """
    d = json.loads(evidence_path.read_text())
    node = {
        "c2_touch_tally": d.get("c2_touch_tally"),
        "phase14.locked_n": d.get("phase14", {}).get("locked_n"),
    }
    return json.dumps(node, sort_keys=True)


def assert_tally_unchanged(before: str, evidence_path: Path) -> None:
    """Refuse if any locked tally moved since ``before`` was snapshotted.

    Args:
        before: Token from :func:`snapshot_locked_tally`.
        evidence_path: The evidence store.

    Raises:
        RuntimeError: The locked tally is not byte-identical (zero-touch
            violated — the gate run must never move it).
    """
    after = snapshot_locked_tally(evidence_path)
    if after != before:
        raise RuntimeError(
            "ZERO-TOUCH VIOLATION: the locked tally is not byte-identical "
            f"across the gate run.\nbefore: {before}\nafter:  {after}"
        )


def capped_pcg_legs(
    rows: list[dict[str, Any]], rtol: float, maxiter: int
) -> list[dict[str, Any]]:
    """PIN 23 detector: legs that exited at the iteration cap OVER rtol.

    A leg that reaches the cap but meets rtol is converged, not capped
    (the build_probe_row semantics, pinned).

    Args:
        rows: PCG convergence rows (``iterations``, ``final_rel_residual``).
        rtol: The solver rtol actually used.
        maxiter: The iteration cap actually used.

    Returns:
        The capped rows (empty = no pin-23 trip).
    """
    return [
        r
        for r in rows
        if int(r["iterations"]) >= maxiter and float(r["final_rel_residual"]) > rtol
    ]


def _validate_checks(checks: dict[str, dict[str, Any]]) -> None:
    missing = [k for k in REQUIRED_CHECKS if k not in checks]
    unknown = [k for k in checks if k not in REQUIRED_CHECKS]
    if missing or unknown:
        raise ValueError(
            f"gate block check-key mismatch: missing={missing} unknown={unknown}"
        )
    for name, c in checks.items():
        status = c.get("status")
        ok = c.get("pass")
        if status not in _STATUSES:
            raise ValueError(
                f"check {name!r}: status must be one of {_STATUSES}; got {status!r}"
            )
        if status == "deferred":
            _validate_deferred(name, c)
            continue
        if not isinstance(ok, bool):
            raise ValueError(
                f"check {name!r}: a non-deferred check must record 'pass' as "
                f"a bool (a verdict); got status={status!r} pass={ok!r}"
            )
        if (status == "fail" and ok) or (status == "pass" and not ok):
            raise ValueError(
                f"check {name!r}: inconsistent status={status!r} vs pass={ok!r}"
            )
        if name in NEVER_PASS_HERE and ok:
            raise ValueError(
                f"check {name!r}: refused — the owner ruling of 2026-07-26 "
                "forbids recording it as a pass at this stage (it is "
                "UNRUNNABLE here; a proxy must never masquerade as the "
                "specified check). Record status='deferred', pass=None."
            )


def _validate_deferred(name: str, c: dict[str, Any]) -> None:
    """Refuse a deferral that is not a real deferral (T11 discipline).

    Args:
        name: The check key.
        c: The sub-block.

    Raises:
        ValueError: The block records a verdict anyway, or does not name
            the stage it defers to and the walk it reappears in — a bare
            "deferred" is how a check gets dropped instead of moved.
    """
    if c.get("pass") is not None:
        raise ValueError(
            f"check {name!r}: a deferred check is neither a pass nor a fail "
            f"— 'pass' must be None; got {c.get('pass')!r}"
        )
    for key in _DEFERRAL_KEYS:
        if not str(c.get(key) or "").strip():
            raise ValueError(
                f"check {name!r}: deferral must record {key!r} — a deferred "
                "check that names no destination is a dropped check"
            )


def build_gate_block(
    *,
    checks: dict[str, dict[str, Any]],
    pcg_rows: list[dict[str, Any]],
    pcg_rtol: float,
    pcg_maxiter: int,
    tally_guard: dict[str, Any],
    artifacts: dict[str, Any],
    meta: dict[str, Any],
) -> dict[str, Any]:
    """Assemble the evidence block — PURE, fail-any-fail, deferred-is-neither.

    Args:
        checks: Exactly the :data:`REQUIRED_CHECKS` sub-blocks (the §10
            checks with check 3 split per the 2026-07-26 ruling).
        pcg_rows: Per-window PCG convergence rows from the real leg.
        pcg_rtol: Solver rtol actually used.
        pcg_maxiter: Solver iteration cap actually used.
        tally_guard: The zero-touch guard record.
        artifacts: Written-artifact paths + shas.
        meta: Run metadata (seal_sha, date, m, n_obs, wall, peak, ...).

    Returns:
        The ``phase14.stage1.anchor_gate`` block; ``pass`` is True only if
        EVERY check carrying a verdict passes, at least one does, every
        remaining check is EXPLICITLY deferred, and no PCG leg tripped pin
        23. A deferred check is neither a pass nor a fail: it never
        contributes green, and it never turns the gate red either.

    Raises:
        ValueError: Missing/unknown check keys or an inconsistent
            sub-block (fail-closed — never assemble a partial gate).
    """
    _validate_checks(checks)
    capped = capped_pcg_legs(pcg_rows, rtol=pcg_rtol, maxiter=pcg_maxiter)
    tripped = bool(capped)
    verdicts = [c for c in checks.values() if c.get("status") != "deferred"]
    all_pass = bool(verdicts) and all(bool(c["pass"]) for c in verdicts) and not tripped
    return {
        "label": "ANCHOR-IDENTITY-GATE",
        "pass": all_pass,
        "checks": {k: checks[k] for k in REQUIRED_CHECKS},
        "pcg": {
            "rtol": pcg_rtol,
            "maxiter": pcg_maxiter,
            "rows": pcg_rows,
        },
        "pin23": {
            "tripped": tripped,
            "capped_legs": capped,
            "rule": (
                "any anchor solve leg at the iteration cap over rtol = "
                "IMMEDIATE owner STOP (recorded, exit nonzero, separate "
                "from the normal walk)"
            ),
        },
        "tally_guard": tally_guard,
        "artifacts": artifacts,
        **meta,
        "accounting": deepcopy(ACCOUNTING),
    }


def gate_exit_code(block: dict[str, Any]) -> int:
    """Exit code for a gate block: 0 green, pin-23 distinct, else fail.

    Args:
        block: A block from :func:`build_gate_block`.

    Returns:
        0 (green), :data:`EXIT_PIN23` (capped-leg owner STOP) or
        :data:`EXIT_FAIL`.
    """
    if block["pin23"]["tripped"]:
        return EXIT_PIN23
    return 0 if block["pass"] else EXIT_FAIL


def root_conditionality(root_int: int) -> dict[str, str]:
    """PIN 30: what each of the four routes is — and is not — conditional on.

    The member route reproduces the signed member draws, which exist only
    under one root, so it proves reproduction UNDER THAT ROOT and never
    root-independence. Variance is computed from the same draws and
    inherits that conditionality; the mean and Γ routes are
    root-independent.

    Args:
        root_int: The member root the run actually used.

    Returns:
        The ``root_conditionality`` sub-block of check 1.
    """
    return {
        "ruling": "owner pin 30, 2026-07-26",
        "member_route": (
            f"CONDITIONAL on shipped_miost5().member_root ({root_int}) — the "
            "route proves REPRODUCTION UNDER THAT ROOT (the reference "
            "members were drawn with it), never root-independence"
        ),
        "mean_and_gamma_routes": "root-independent",
        "variance_route": (
            "computed from the same member draws — inherits the member "
            "route's root conditionality"
        ),
        "plan_text_was_wrong": (
            "the plan named derive_seed('miost','stage-b-winner','members',0) "
            "= 4836134738817689931; the reference store forces the phase-13 "
            "acceptance root; plan text corrected 2026-07-26"
        ),
    }


def check_surface_identity(
    cal: PolyCalibration,
    signed: dict[str, Any],
    lon: np.ndarray,
    lat: np.ndarray,
) -> dict[str, Any]:
    """Shipped calibration surface ≡ signed s(x) — EXACTLY (``==``).

    Descriptor (``cal.key()``) byte-equal to the artifact's ``cal_key`` AND
    ``log_s``/``sqrt_s`` surface values exactly equal on the probe points.
    Never a tolerance (an identity, not a hope).

    This is the RUN half of the 2026-07-26 check-3 split, and it claims
    exactly what it proves: no drift in the shipped calibration surface.
    It is NOT the era no-op — see :func:`build_era_noop_deferred`.

    Args:
        cal: The calibration surface the generalized-path product carries.
        signed: The signed s(x) artifact dict (``phase13_field_miost.json``
            schema: ``calibration`` + ``cal_key``).
        lon: Probe longitudes [deg east].
        lat: Probe latitudes [deg north].

    Returns:
        The ``surface_identity`` sub-block.
    """
    from sverdrup.distributions.calibration import (  # noqa: PLC0415
        PolyCalibration as _Poly,
    )

    ref = _Poly.from_json(signed["calibration"])
    lon2, lat2 = np.meshgrid(np.asarray(lon, float), np.asarray(lat, float))
    lo, la = lon2.ravel(), lat2.ravel()
    surface_exact = bool(
        np.array_equal(cal.log_s_at(lo, la), ref.log_s_at(lo, la))
        and np.array_equal(cal.sqrt_s_at(lo, la), ref.sqrt_s_at(lo, la))
    )
    signed_key = str(signed.get("cal_key", ref.key()))
    key_equal = cal.key() == signed_key
    ok = key_equal and surface_exact
    return {
        "status": "pass" if ok else "fail",
        "pass": ok,
        "name": SURFACE_IDENTITY_NAME,
        "cal_key": cal.key(),
        "signed_cal_key": signed_key,
        "cal_key_equal": key_equal,
        "surface_exact_equal": surface_exact,
        "n_points": int(lo.size),
        "equality": "exact (==), by construction — never a tolerance",
        "what_it_proves": SURFACE_IDENTITY_PROVES,
    }


def superseded_check3_recording(
    surface: dict[str, Any], artifact: dict[str, Any]
) -> dict[str, Any]:
    """The pre-split check-3 recording, rebuilt from the same computation.

    Preserved (never deleted) inside the deferred ``era_noop`` block so the
    superseded claim — the proxy recorded as a PASS of check 3 — stays
    auditable next to the ruling that superseded it.

    Args:
        surface: The block from :func:`check_surface_identity`.
        artifact: The signed s(x) artifact pointer (``path`` + ``sha256``).

    Returns:
        The superseded sub-block, in its original key shape and wording.
    """
    return {
        "status": surface["status"],
        "pass": surface["pass"],
        "cal_key": surface["cal_key"],
        "signed_cal_key": surface["signed_cal_key"],
        "cal_key_equal": surface["cal_key_equal"],
        "surface_exact_equal": surface["surface_exact_equal"],
        "n_points": surface["n_points"],
        "equality": surface["equality"],
        "reading": SUPERSEDED_CHECK3_READING,
        "artifact": artifact,
    }


def build_era_noop_deferred(*, superseded: dict[str, Any]) -> dict[str, Any]:
    """SPEC §10 check 3 as the owner ruled it: DEFERRED, never proxy-passed.

    No era-keyed calibration instantiation exists at Stage 1, so the
    specified check is unrunnable here. It is recorded with no verdict
    (``pass: None``), named to the stage that introduces era-keyed code,
    and re-entered into that stage's coverage walk.

    Args:
        superseded: The prior recording from
            :func:`superseded_check3_recording` — preserved verbatim.

    Returns:
        The deferred ``era_noop`` sub-block.
    """
    return {
        "status": "deferred",
        "pass": None,
        "name": ERA_NOOP_NAME,
        "deferred_to": ERA_NOOP_DEFERRED_TO,
        "why": ERA_NOOP_WHY,
        "reappears_in": ERA_NOOP_REAPPEARS_IN,
        "spec_citation": ERA_NOOP_SPEC_CITATION,
        "superseded_recording": superseded,
    }


def build_check2(
    gate2_node: dict[str, Any], golden_node: dict[str, Any]
) -> dict[str, Any]:
    """Check 2 citation block: Stage-0 loader identity + golden-tile TABLED.

    Cites both halves, runs nothing (Stage-0 complete).

    Args:
        gate2_node: ``phase14.stage0.gate2_loader_identity``.
        golden_node: ``phase14.stage0.golden_tile``.

    Returns:
        The cited check-2 sub-block.

    Raises:
        RuntimeError: The recorded gate-2 verdict is not a pass, or the
            golden-tile lineage-sensitivity row is not TABLED — citing
            either as green would be a fabrication.
    """
    if gate2_node.get("pass") is not True:
        raise RuntimeError(
            "check 2 refuses to cite: evidence gate2_loader_identity does "
            f"not record pass=True (got {gate2_node.get('pass')!r})"
        )
    row = golden_node.get("dc2021a_vs_cmems_my") or {}
    if row.get("tabled_for_owner") is not True:
        raise RuntimeError(
            "check 2 refuses to cite: the golden-tile lineage-sensitivity "
            "row is not recorded TABLED for the owner"
        )
    return {
        "status": "cited",
        "pass": True,
        "runs": "nothing — Stage-0 complete halves cited by evidence pointer",
        "citations": {
            "gate2_loader_identity": {
                "node": "phase14.stage0.gate2_loader_identity",
                "pass": True,
                "manifest_sha": gate2_node.get("manifest_sha"),
                "date": gate2_node.get("date"),
            },
            "golden_tile": {
                "node": "phase14.stage0.golden_tile",
                "tabled_for_owner": True,
                "mu_delta": row.get("mu_delta"),
                "note": row.get("note"),
                "date": row.get("date"),
            },
        },
    }


def build_check4(
    *,
    crn_manifests: list[dict[str, Any]],
    crn_equal: bool,
    cross_host: str,
) -> dict[str, Any]:
    """Check 4: T17 same-host halves cited; cross-host slot EXPLICIT.

    Args:
        crn_manifests: The two same-host CRN manifest pointers (path+sha).
        crn_equal: The RECOMPUTED manifest equality (never only cited).
        cross_host: Must be the explicit ``pending-T18`` marker (the
            Gate-0 ruling: green with the slot pending, never silently).

    Returns:
        The check-4 sub-block.

    Raises:
        ValueError: A silent/empty cross_host slot.
    """
    if cross_host != CROSS_HOST_PENDING:
        raise ValueError(
            "check 4 cross_host slot must be EXPLICIT "
            f"({CROSS_HOST_PENDING!r} per the Gate-0 ruling); got "
            f"{cross_host!r} — a silent slot is forbidden"
        )
    return {
        "status": "cited" if crn_equal else "fail",
        "pass": bool(crn_equal),
        "same_host": {
            "recorded_at": "Stage-0 T17 (db06c2b + 129cc66)",
            "crn_manifests": list(crn_manifests),
            "crn_equal_recomputed": bool(crn_equal),
            "solve_manifests": (
                "T17 solve/compare-solve halves recorded same-host "
                "(REPORT-only deltas; tolerance recorded at T18)"
            ),
        },
        "cross_host": cross_host,
        "ruling": CHECK4_RULING,
    }


# ---------------------------------------------------------------------------
# Evidence writes (seal-gated, atomic — the stage1_run ceremony)
# ---------------------------------------------------------------------------


def _seal_gated_store(evidence_path: Path) -> dict[str, Any]:
    from sverdrup.validation import phase14_seal  # noqa: PLC0415

    phase14_seal.verify_current_seal()
    return json.loads(evidence_path.read_text()) if evidence_path.exists() else {}


def record_gate5(constants: dict[str, Any], evidence_path: Path = EVIDENCE) -> None:
    """Pin the gate-5 constants at ``phase14.stage1.gate5`` — WRITE-ONCE.

    Args:
        constants: The (µ, σ, λx) block from the anchor run.
        evidence_path: The evidence store (tmp path in tests).

    Raises:
        RuntimeError: The node already exists (the pin never moves).
        sverdrup.validation.phase14_seal.SealError: No verified seal.
    """
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    results = _seal_gated_store(evidence_path)
    node = results.setdefault("phase14", {}).setdefault("stage1", {})
    if "gate5" in node:
        raise RuntimeError(
            "phase14.stage1.gate5 already recorded — the gate-5 constants "
            "are write-once (pinned at the first anchor run; they never move)"
        )
    node["gate5"] = dict(constants)
    atomic_write_json(evidence_path, results)


def record_anchor_gate(block: dict[str, Any], evidence_path: Path = EVIDENCE) -> None:
    """Record the gate block at ``phase14.stage1.anchor_gate``.

    Deliberately NOT write-once: a re-walk after a RED records the latest
    gate reading; the write-once pin lives in :func:`record_gate5`.

    Args:
        block: The block from :func:`build_gate_block`.
        evidence_path: The evidence store (tmp path in tests).

    Raises:
        sverdrup.validation.phase14_seal.SealError: No verified seal.
    """
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    results = _seal_gated_store(evidence_path)
    results.setdefault("phase14", {}).setdefault("stage1", {})["anchor_gate"] = block
    atomic_write_json(evidence_path, results)


# ---------------------------------------------------------------------------
# Heavy-leg helpers (data-touching; lazy imports throughout)
# ---------------------------------------------------------------------------


def _stage1_run_module() -> ModuleType:
    """Import the sibling Stage-1 driver script (scripts/ is not a package)."""
    import importlib.util  # noqa: PLC0415
    import sys  # noqa: PLC0415

    name = "phase14_stage1_run"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - loader exists
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def anchor_size_model() -> dict[str, float]:
    """Task-22 sizing arithmetic at the ANCHOR geometry, m=100, 9 windows.

    Mirrors the driver's ``preflight`` geometry WITHOUT the ladder
    predicate so the launch wrapper can derive its RAM-gate threshold
    (2 × ``peak_model_mib``) while the box is still busy.

    Returns:
        The ``size_tile`` model dict.
    """
    from sverdrup.application.spatial_tiles import (  # noqa: PLC0415
        anchor_frame,
        frame_grid,
    )
    from sverdrup.methods.miost import PHASE13_WINNER_PARAMS  # noqa: PLC0415
    from sverdrup.methods.miost_basis import N_DIR  # noqa: PLC0415
    from sverdrup.methods.miost_sizing import (  # noqa: PLC0415
        BOX_W0_OBS_BASIS,
        KM_PER_DEG,
        size_tile,
    )
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415

    frame = anchor_frame()
    grid = frame_grid(frame, RESOLUTION_DEG)
    solve = frame.solve_bbox
    mid_lat = 0.5 * (solve.lat_min + solve.lat_max)
    d_x_km = (
        (solve.lon_max - solve.lon_min) * KM_PER_DEG * math.cos(math.radians(mid_lat))
    )
    d_y_km = (solve.lat_max - solve.lat_min) * KM_PER_DEG
    plan = WindowPlan()
    lam_min = float(_stage1_run_module()._SIZING_LAM_MIN_KM)  # noqa: SLF001
    return size_tile(
        d_x_km=d_x_km,
        d_y_km=d_y_km,
        n_grid_nodes=int(grid.x.size * grid.y.size),
        window_days=plan.w_days,
        n_windows=len(plan.windows),
        m_members=M_MEMBERS,
        n_obs=int(BOX_W0_OBS_BASIS),  # anchor solve area == the signed box
        alpha=float(PHASE13_WINNER_PARAMS["spacing_alpha"]),
        n_dir=N_DIR,
        lam_min=lam_min,
    )


def _load_generalized_obs() -> tuple[TileFrame, GridSpec, ObsWindow]:
    """The generalized tiling path: frame, grid, framed dc2021a obs."""
    from sverdrup.adapters.altimetry.contract import BBox  # noqa: PLC0415
    from sverdrup.adapters.altimetry.dc2021a import Dc2021aSource  # noqa: PLC0415
    from sverdrup.application.spatial_tiles import (  # noqa: PLC0415
        anchor_frame,
        frame_grid,
        frame_obs,
    )

    frame = anchor_frame()
    grid = frame_grid(frame, RESOLUTION_DEG)
    obs = Dc2021aSource().load(
        BBox(0.0, 360.0, -90.0, 90.0),
        np.datetime64("2016-11-01"),
        np.datetime64("2018-03-01"),
        missions=MAPPING_FIVE,
    )
    framed = frame_obs(obs, frame, RESOLUTION_DEG)
    return frame, grid, framed


def _legacy_train(grid: GridSpec) -> ObsWindow:
    """The SIGNED box obs path (T11 recipe): 6-file load, split, halo cut."""
    from sverdrup.application.splits import make_splits  # noqa: PLC0415
    from sverdrup.validation.input_adapter import load_mapping_obs  # noqa: PLC0415
    from sverdrup.validation.params import baseline_config  # noqa: PLC0415
    from sverdrup.validation.run import _subset, halo_obs  # noqa: PLC0415

    provider, _, _ = baseline_config()
    obs_all = load_mapping_obs([Path(p) for p in MAPPING_SIX], provider)
    split = make_splits(
        obs_all, by="mission", locked_missions=["c2"], validation_missions=["j3"]
    )
    return halo_obs(_subset(obs_all, split.train_idx), grid)


def obs_identity_route(framed: ObsWindow, legacy: ObsWindow) -> dict[str, Any]:
    """Byte-compare the generalized obs table against the signed path.

    Runs BEFORE the member solves: an obs mismatch fails the gate in
    minutes, not after seven hours of solves. Missions compared by VALUE
    (the recorded U2/U3 dtype-promotion gotcha).

    Args:
        framed: Generalized-path framed obs.
        legacy: Signed-path train obs.

    Returns:
        Route diagnostics (``equal`` + per-array shas and counts).
    """
    ca, cb = framed.coords(), legacy.coords()
    va, vb = framed.values(), legacy.values()
    ma = [str(s) for s in np.asarray(framed.mission)]
    mb = [str(s) for s in np.asarray(legacy.mission)]
    equal = (
        ca.shape == cb.shape
        and bool(np.array_equal(ca, cb))
        and bool(np.array_equal(va, vb))
        and ma == mb
    )
    return {
        "equal": equal,
        "n_generalized": int(ca.shape[0]),
        "n_signed_path": int(cb.shape[0]),
        "coords_sha": {"generalized": sha256_array(ca), "signed": sha256_array(cb)},
        "values_sha": {"generalized": sha256_array(va), "signed": sha256_array(vb)},
    }


def _basis_domain_km(frame: TileFrame) -> tuple[float, float, float, float]:
    """The tile solve bbox in the shared km plane (the driver's convention)."""
    from sverdrup.methods.miost_basis import lonlat_to_km  # noqa: PLC0415

    solve = frame.solve_bbox
    xs, ys = lonlat_to_km(
        np.array([solve.lon_min, solve.lon_max]),
        np.array([solve.lat_min, solve.lat_max]),
    )
    x0, y0 = float(xs[0]), float(ys[0])
    return (x0, y0, float(xs[1]) - x0, float(ys[1]) - y0)


def _mem_available_mib() -> float:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return float(line.split()[1]) / 1024.0
    return float("nan")  # pragma: no cover - MemAvailable always present


def _attach_label(path: Path, label: str) -> None:
    """Attach the internal label attr in place (Stage-1 map convention)."""
    import netCDF4  # noqa: PLC0415

    with netCDF4.Dataset(path, "a") as ds:
        ds.setncattr("label", label)


# ---------------------------------------------------------------------------
# The real leg
# ---------------------------------------------------------------------------


def _fail_check(reason: str) -> dict[str, Any]:
    return {"status": "fail", "pass": False, "reason": reason}


def _run_real_leg(evidence_path: Path) -> int:  # noqa: PLR0915
    """Checks 1/3/5 executed + 2/4 cited; block recorded; exit code returned."""
    import gc  # noqa: PLC0415
    import resource  # noqa: PLC0415
    import threading  # noqa: PLC0415
    import time  # noqa: PLC0415

    import xarray as xr  # noqa: PLC0415

    import sverdrup.methods.miost as miost_mod  # noqa: PLC0415
    from sverdrup.application.spatial_tiles import anchor_frame  # noqa: PLC0415
    from sverdrup.core.parameters import ConstantProvider  # noqa: PLC0415
    from sverdrup.core.seeding import derive_seed  # noqa: PLC0415
    from sverdrup.distributions.miost_ensemble import (  # noqa: PLC0415
        mean_fields,
        merged_members,
        std_fields,
    )
    from sverdrup.methods.miost import (  # noqa: PLC0415
        PHASE13_DELTAS,
        PHASE13_WINNER_PARAMS,
        Miost,
        MiostPointDistribution,
        shipped_miost5,
    )
    from sverdrup.methods.miost_rspec import RSpec  # noqa: PLC0415
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415
    from sverdrup.validation import their_eval  # noqa: PLC0415
    from sverdrup.validation.input_adapter import load_mdt_grid  # noqa: PLC0415
    from sverdrup.validation.output_adapter import write_map  # noqa: PLC0415
    from sverdrup.validation.params import baseline_config  # noqa: PLC0415
    from sverdrup.validation.pertile_scoring import score_tile  # noqa: PLC0415

    def _echo(msg: str) -> None:
        print(f"[anchor-gate] {msg}", flush=True)

    t_wall = time.monotonic()
    store = json.loads(evidence_path.read_text())
    stage1 = store.get("phase14", {}).get("stage1", {})

    # SINGLE-WRITER ORDERING: the pin-23(a) converged-probe evidence write
    # lands before this leg starts (plan execution note).
    if "probe_converged" not in stage1:
        _echo(
            "REFUSED: phase14.stage1.probe_converged not recorded — the "
            "pin-23(a) converged probe re-run's evidence write must land "
            "BEFORE the anchor gate's real leg (single-writer ordering)."
        )
        return EXIT_FAIL

    # Missing signed references = a hard refusal naming every absentee.
    refs = [WINNER_MEAN, WINNER_VAR, WINNER_MEMBERS, SIGNED_FIELD_JSON, J3_TRACK]
    absent = [str(p) for p in refs if not p.exists()]
    if absent:
        _echo(f"REFUSED: signed reference artifact(s) absent: {absent}")
        return EXIT_FAIL

    tally_before = snapshot_locked_tally(evidence_path)
    seal_sha = str(store["phase14"]["stage0"]["seal"]["sha"])

    # Tier-1 ladder BEFORE any load (driver's preflight, fork-g pin 4).
    stage1_run = _stage1_run_module()
    model = stage1_run.preflight("anchor", M_MEMBERS)
    _echo("preflight model: " + json.dumps({k: round(v, 1) for k, v in model.items()}))

    # Root provenance: the signed member store's root, tied to the shipped
    # config and the derive_seed convention — never a restated literal.
    members_node = store["phase13"]["miost"]["members"]
    root = int(members_node["root_int"])
    derived = int(derive_seed("miost", "phase13-winner", "members", 0))
    shipped = shipped_miost5()
    shipped_root = int(shipped.member_root) if shipped.member_root is not None else -1
    if root != derived or root != shipped_root:
        _echo(
            f"REFUSED: root mismatch — store {root}, derive_seed {derived}, "
            f"shipped {shipped_root}"
        )
        return EXIT_FAIL
    maxiter = int(members_node["maxiter_used"])  # the signed cap (500)

    # Heartbeat so the stall watcher sees steady log growth between the
    # ~45-minute window-solve lines.
    stop_beat = threading.Event()

    def _beat() -> None:
        while not stop_beat.wait(300.0):
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
            _echo(
                f"heartbeat {datetime.now(UTC).isoformat()} "
                f"peak_rss={rss:.0f}MiB mem_avail={_mem_available_mib():.0f}MiB"
            )

    threading.Thread(target=_beat, daemon=True).start()

    try:
        # ---- generalized path substrate --------------------------------
        frame, grid, framed = _load_generalized_obs()
        base_grid = baseline_config()[1]
        grid_identical = bool(
            np.array_equal(grid.x, base_grid.x) and np.array_equal(grid.y, base_grid.y)
        )
        _echo(f"grid identity vs signed box: {grid_identical}")

        provider = ConstantProvider(dict(PHASE13_WINNER_PARAMS))
        rspec = RSpec(deltas=dict(PHASE13_DELTAS))
        basis = _basis_domain_km(frame)
        plan = WindowPlan()
        # Crash-durable member-batch PCG checkpoints (bit-identical resume
        # after a kill — the documented MiostSolver contract; the phase-13
        # T3 external legs ran the same way). A harness-level process-group
        # kill took the first launch of this leg down mid-window.
        ckpt_dir = STAGE1_DIR / "anchor_gate_pcg_ckpt"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        method = Miost(
            plan=plan,
            pcg_maxiter=maxiter,
            rspec=rspec,
            basis_domain=basis,
            member_solve_checkpoint_dir=ckpt_dir,
        )
        spec_gen = method._spec_from(provider, grid)  # noqa: SLF001
        spec_sig = Miost(plan=plan, pcg_maxiter=maxiter, rspec=rspec)._spec_from(  # noqa: SLF001
            provider, grid
        )
        spec_identical = spec_gen == spec_sig
        _echo(f"basis-spec identity (generalized vs signed default): {spec_identical}")

        # ---- fail-fast obs identity (minutes, not hours) ---------------
        legacy = _legacy_train(grid)
        obs_route = obs_identity_route(framed, legacy)
        del legacy
        gc.collect()
        _echo(f"obs identity: {obs_route['equal']} (n={obs_route['n_generalized']})")

        pcg_rows: list[dict[str, Any]] = []
        check1: dict[str, Any]
        check5: dict[str, Any]

        if not (grid_identical and spec_identical and obs_route["equal"]):
            check1 = _fail_check("substrate identity failed before solves")
            check1.update(
                {
                    "grid_identical": grid_identical,
                    "basis_spec_identical": spec_identical,
                    "obs_identity": obs_route,
                    "basis_domain_km": list(basis),
                }
            )
            check5 = _fail_check("not run — check-1 substrate identity failed")
        else:
            # ---- the m=100 full-2017 anchor solve (the seven-hour leg) --
            # Crash-durable at the LEG level: the solve output (etas/anoms/
            # starts + the pcg rows) persists to this leg's OWN store right
            # after the solves, and a re-run resumes from it (the phase-13
            # T3 leg-cache pattern after this host's oom_kill events;
            # clearing the store forces a full recompute — the gate
            # re-validation path).
            days = [float(d) for d in range(N_DAYS)]
            resumed = OWN_STORE.exists()
            if resumed:
                _echo(f"RESUME: loading this leg's own member store {OWN_STORE}")
                with np.load(OWN_STORE, allow_pickle=False) as z:
                    wids = [str(w) for w in np.asarray(z["window_ids"])]
                    etas_a = {w: np.asarray(z[f"eta_{w}"]) for w in wids}
                    anoms = {w: np.asarray(z[f"anom_{w}"]) for w in wids}
                    starts = {w: float(z[f"start_{w}"]) for w in wids}
                    pcg_rows = json.loads(str(z["pcg_rows"][()]))
                    solve_wall_s = float(z["solve_wall_s"])
                spec = method._spec_from(provider, grid)  # noqa: SLF001
            else:
                t_solve0 = time.monotonic()
                log_start = len(miost_mod.CONVERGENCE_LOG)
                spec, etas_a, anoms, starts = merged_members(
                    method,
                    framed,
                    grid,
                    provider,
                    M_MEMBERS,
                    root,
                    on_window=lambda wid, day: _echo(
                        f"window {wid} solved (day {day:.0f}); "
                        f"{time.monotonic() - t_wall:.0f}s"
                    ),
                )
                pcg_rows = [dict(r) for r in miost_mod.CONVERGENCE_LOG[log_start:]]
                solve_wall_s = time.monotonic() - t_solve0
                STAGE1_DIR.mkdir(parents=True, exist_ok=True)
                payload: dict[str, Any] = {
                    "window_ids": np.array(sorted(anoms)),
                    "pcg_rows": json.dumps(pcg_rows),
                    "solve_wall_s": solve_wall_s,
                    "label": (
                        "ANCHOR-GATE-LEG member store (this leg's own solve "
                        "output; crash-resume substrate, never a reference)"
                    ),
                }
                for w in anoms:
                    payload[f"eta_{w}"] = etas_a[w]
                    payload[f"anom_{w}"] = anoms[w]
                    payload[f"start_{w}"] = starts[w]
                np.savez(OWN_STORE, **payload)
                _echo(f"member store persisted: {OWN_STORE}")
            _echo(f"solves done: {len(pcg_rows)} pcg rows (resumed={resumed})")

            # ---- route 1: member coefficient arrays sha-equal ----------
            member_windows: dict[str, Any] = {}
            member_ok = True
            with np.load(WINNER_MEMBERS) as z:
                ref_wids = sorted(str(w) for w in np.asarray(z["window_ids"]))
                got_wids = sorted(anoms)
                if ref_wids != got_wids:
                    member_ok = False
                for wid in got_wids:
                    row: dict[str, Any] = {
                        "eta_sha": sha256_array(etas_a[wid]),
                        "anom_sha": sha256_array(anoms[wid]),
                    }
                    if f"eta_{wid}" in z.files:
                        row["ref_eta_sha"] = sha256_array(np.asarray(z[f"eta_{wid}"]))
                        row["ref_anom_sha"] = sha256_array(np.asarray(z[f"anom_{wid}"]))
                        row["equal"] = (
                            row["eta_sha"] == row["ref_eta_sha"]
                            and row["anom_sha"] == row["ref_anom_sha"]
                        )
                    else:
                        row["equal"] = False
                    member_ok = member_ok and bool(row["equal"])
                    member_windows[wid] = row
            _echo(f"route member-sha: {member_ok}")

            # ---- routes 2/4 substrate: blended day fields ---------------
            means = mean_fields(spec, starts, etas_a, grid, plan, days)
            stds = std_fields(spec, starts, anoms, grid, plan, days)
            # anoms (~1.4 GB) is done after std_fields — free it before the
            # compare/Γ phase (the compare-phase OOM lesson from launch 2).
            del anoms
            gc.collect()
            mdt = np.asarray(load_mdt_grid([Path(p) for p in MAPPING_SIX], grid))
            mean_stack = np.stack([mn.reshape(grid.shape) for mn in means]) + mdt[None]
            std_stack = np.stack([sd.reshape(grid.shape) for sd in stds])
            var_stack = std_stack**2
            del stds
            gc.collect()

            with xr.open_dataset(WINNER_MEAN) as ds:
                ref_mean = np.asarray(ds["ssh"].values)
            with xr.open_dataset(WINNER_VAR) as ds:
                ref_var = np.asarray(ds["ssh"].values)

            mean_bit = bool(np.array_equal(mean_stack, ref_mean))
            mean_max = float(np.max(np.abs(mean_stack - ref_mean)))
            mean_ok = mean_bit or bool(
                np.allclose(mean_stack, ref_mean, rtol=ROUTE_RTOL, atol=1e-15)
            )
            _echo(f"route mean: {mean_ok} (bit={mean_bit}, max|d|={mean_max:.3e})")

            var_bit = bool(np.array_equal(var_stack, ref_var))
            var_max = float(np.max(np.abs(var_stack - ref_var)))
            var_ok = var_bit or bool(
                np.allclose(var_stack, ref_var, rtol=ROUTE_RTOL, atol=1e-18)
            )
            _echo(f"route variance: {var_ok} (bit={var_bit}, max|d|={var_max:.3e})")
            del var_stack, ref_var
            gc.collect()

            # ---- route 3: Γ-path day 0 (chunked mean_at) ----------------
            # from_etas evaluates its construction grid's mean via ONE
            # whole-grid mean_at — a dense (n_pts, n_elem) ~4 GB evaluate,
            # the exact recorded Phase-13 OOM (it killed launch 2 of this
            # leg). Build on a 1x1 grid; the REAL grid points go through
            # chunked mean_at below (transient capped at ~150 MB).
            from sverdrup.core.grid import GridSpec as _GridSpec  # noqa: PLC0415

            wid0 = plan.windows[0].id
            tiny = _GridSpec.lonlat(
                np.asarray([float(grid.x[0])]), np.asarray([float(grid.y[0])])
            )
            dist = MiostPointDistribution.from_etas(
                tiny,
                GAMMA_DAY,
                spec,
                {wid0: etas_a[wid0]},
                {wid0: starts[wid0]},
                w_days=plan.w_days,
            )
            lon2d, lat2d = np.meshgrid(grid.x, grid.y)
            pts = np.column_stack(
                [lon2d.ravel(), lat2d.ravel(), np.full(lon2d.size, GAMMA_DAY)]
            )
            gamma_vals = np.concatenate(
                [
                    np.asarray(dist.mean_at(pts[i : i + _GAMMA_CHUNK]))
                    for i in range(0, pts.shape[0], _GAMMA_CHUNK)
                ]
            )
            gamma_map = gamma_vals.reshape(grid.shape) + mdt
            gamma_max = float(np.max(np.abs(gamma_map - ref_mean[0])))
            gamma_ok = bool(
                np.allclose(gamma_map, ref_mean[0], rtol=ROUTE_RTOL, atol=1e-15)
            )
            _echo(f"route gamma (day 0): {gamma_ok} (max|d|={gamma_max:.3e})")

            check1_pass = member_ok and mean_ok and var_ok and gamma_ok
            check1 = {
                "status": "pass" if check1_pass else "fail",
                "pass": check1_pass,
                # Owner pin 62: pin 42's required schema field, discharged
                # EXACTLY here rather than probabilistically. This is the
                # gate guarding the highest-risk change in the stage.
                "pin42": {
                    "ruling": (
                        "docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md"
                    ),
                    "pin": "62 — check-1's pin-42 fields",
                    "kind": "exact, not probabilistic",
                    "pass_condition": (
                        "the lattice is unmoved: under pin 31(a) the global "
                        "origin is congruent to the anchor's own (x0_km, "
                        "y0_km) modulo the rung spacing, so element centres "
                        "are unchanged BY CONSTRUCTION, member draws are "
                        "unchanged, and all four routes are bit-identical"
                    ),
                    "fail_condition": (
                        "the lattice MOVES — and only then. Element "
                        "identities change, CRN draws change, and member "
                        "sha-equality against phase13_winner_members.npz "
                        "breaks on the affected windows"
                    ),
                    "both_outcomes_reachable": True,
                    "why_not_probabilistic": (
                        "the routes are bit-identical comparisons; rtol "
                        f"{ROUTE_RTOL} is a guard, not the criterion. There "
                        "is no null and no alternative to state"
                    ),
                    "self_witnessing": (
                        "each reference route records reference_sha256 inline "
                        "(pin 58d), so the record shows WHAT was compared "
                        "against, not merely that it matched"
                    ),
                },
                "grid_identical": grid_identical,
                "basis_spec_identical": spec_identical,
                "basis_domain_km": list(basis),
                "obs_identity": obs_route,
                "routes": {
                    "member_sha": {"pass": member_ok, "windows": member_windows},
                    # Owner pin 58(d): a route that records only the
                    # comparison OUTCOME witnesses nothing about the
                    # artifact it compared against — substituting that
                    # artifact later would simply re-pass. These three
                    # routes now record the reference sha inline.
                    "mean_vs_acceptance": {
                        "pass": mean_ok,
                        "bit_identical": mean_bit,
                        "max_abs_diff_m": mean_max,
                        "rtol": ROUTE_RTOL,
                        "reference": str(WINNER_MEAN),
                        "reference_sha256": sha256_file(WINNER_MEAN),
                    },
                    "gamma_route": {
                        "pass": gamma_ok,
                        "day": GAMMA_DAY,
                        "max_abs_diff_m": gamma_max,
                        "rtol": ROUTE_RTOL,
                        "reference": str(WINNER_MEAN),
                        "reference_sha256": sha256_file(WINNER_MEAN),
                        "reference_note": (
                            "the Gamma route compares against the same "
                            "acceptance mean map as mean_vs_acceptance "
                            "(ref_mean[0]); it previously recorded neither "
                            "the path nor a sha"
                        ),
                    },
                    "variance": {
                        "pass": var_ok,
                        "bit_identical": var_bit,
                        "max_abs_diff_m2": var_max,
                        "rtol": ROUTE_RTOL,
                        "reference": str(WINNER_VAR),
                        "reference_sha256": sha256_file(WINNER_VAR),
                    },
                },
                "reference_store": {
                    "member_store": str(WINNER_MEMBERS),
                    "member_store_sha": sha256_file(WINNER_MEMBERS),
                    "root_int": root,
                    "m": M_MEMBERS,
                    "root_note": ROOT_NOTE,
                },
                "own_member_store": {
                    "path": str(OWN_STORE),
                    "resumed_from_own_store": resumed,
                    "solve_wall_s": solve_wall_s,
                },
                "root_conditionality": root_conditionality(root),
            }

            # ---- persist the anchor maps (+ member-std: the T1 follow-on)
            STAGE1_DIR.mkdir(parents=True, exist_ok=True)
            assimilated = tuple(sorted({str(s) for s in np.asarray(framed.mission)}))
            epoch = np.datetime64("2017-01-01")
            times = epoch + np.asarray(days, dtype="int64") * np.timedelta64(1, "D")
            write_map(
                times,
                grid.y,
                grid.x,
                mean_stack,
                ANCHOR_SIGNED_MAPS,
                assimilated_missions=assimilated,
            )
            write_map(
                times,
                grid.y,
                grid.x,
                std_stack,
                ANCHOR_MEMBER_STD,
                assimilated_missions=assimilated,
            )
            for p in (ANCHOR_SIGNED_MAPS, ANCHOR_MEMBER_STD):
                _attach_label(p, "STAGE1-EVIDENCE")
            _echo(f"maps written: {ANCHOR_SIGNED_MAPS} + {ANCHOR_MEMBER_STD}")

            # ---- check 5: score-level identity + gate-5 pin -------------
            ours = score_tile(anchor_frame(), ANCHOR_SIGNED_MAPS, J3_TRACK)
            mu, sigma, lambda_x = their_eval.score(ANCHOR_SIGNED_MAPS, J3_TRACK)
            score_ok = bool(
                np.isclose(ours.mu, mu, rtol=ROUTE_RTOL, atol=0.0)
                and np.isclose(ours.sigma, sigma, rtol=ROUTE_RTOL, atol=0.0)
                and np.isclose(ours.lambda_x, lambda_x, rtol=ROUTE_RTOL, atol=0.0)
            )
            _echo(
                f"check 5 score identity: {score_ok} "
                f"(mu={mu!r}, sigma={sigma!r}, lambda_x={lambda_x!r})"
            )
            constants = {
                "mu": float(mu),
                "sigma": float(sigma),
                "lambda_x": float(lambda_x),
                "n_scored_points": int(ours.n_scored_points),
                "lineage": "compute_stats (vendored area-binned; gate-0 deviation note)",
                "map": str(ANCHOR_SIGNED_MAPS),
                "map_sha": sha256_file(ANCHOR_SIGNED_MAPS),
                "track": str(J3_TRACK),
                "date": datetime.now(UTC).date().isoformat(),
            }
            gate5_status = "pinned"
            try:
                record_gate5(constants, evidence_path=evidence_path)
            except RuntimeError:
                prior = json.loads(evidence_path.read_text())["phase14"]["stage1"][
                    "gate5"
                ]
                same = all(
                    prior.get(k) == constants[k] for k in ("mu", "sigma", "lambda_x")
                )
                gate5_status = "already-pinned; values identical"
                if not same:
                    score_ok = False
                    gate5_status = "CONFLICT: node already pinned with DIFFERENT values"
            check5 = {
                "status": "pass" if score_ok else "fail",
                "pass": score_ok,
                "ours": {
                    "mu": float(ours.mu),
                    "sigma": float(ours.sigma),
                    "lambda_x": float(ours.lambda_x),
                    "n_scored_points": int(ours.n_scored_points),
                },
                "theirs": {
                    "mu": float(mu),
                    "sigma": float(sigma),
                    "lambda_x": float(lambda_x),
                },
                "rtol": ROUTE_RTOL,
                "gate5": gate5_status,
            }

        # ---- check 3 SPLIT (owner ruling 2026-07-26) ---------------------
        # The surface identity RUNS and passes on its own terms; the era
        # no-op is UNRUNNABLE here and is recorded DEFERRED, carrying the
        # superseded proxy-pass recording.
        cal = cast(
            "PolyCalibration",
            shipped._calibration,  # noqa: SLF001 - the shipped s(x) surface
        )
        signed_field = json.loads(SIGNED_FIELD_JSON.read_text())
        surface = check_surface_identity(cal, signed_field, grid.x, grid.y)
        era_noop = build_era_noop_deferred(
            superseded=superseded_check3_recording(
                surface,
                artifact={
                    "path": str(SIGNED_FIELD_JSON),
                    "sha256": sha256_file(SIGNED_FIELD_JSON),
                },
            )
        )
        _echo(
            f"surface identity: {surface['pass']}; "
            f"era no-op (SPEC §10 check 3): {era_noop['status']}"
        )

        # ---- checks 2 and 4 (citations) ---------------------------------
        stage0 = store["phase14"]["stage0"]
        check2 = build_check2(stage0["gate2_loader_identity"], stage0["golden_tile"])
        ma = json.loads(CRN_MANIFEST_A.read_text())
        mb = json.loads(CRN_MANIFEST_B.read_text())
        crn_equal = ma["axes"] == mb["axes"] and ma["root"] == mb["root"]
        check4 = build_check4(
            crn_manifests=[
                {"path": str(CRN_MANIFEST_A), "sha256": sha256_file(CRN_MANIFEST_A)},
                {"path": str(CRN_MANIFEST_B), "sha256": sha256_file(CRN_MANIFEST_B)},
            ],
            crn_equal=crn_equal,
            cross_host=CROSS_HOST_PENDING,
        )
        _echo(f"check 2 cited: {check2['pass']}; check 4 cited: {check4['pass']}")

        wall_s = time.monotonic() - t_wall
        peak_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        artifacts = {
            "anchor_signed_maps": {
                "path": str(ANCHOR_SIGNED_MAPS),
                "sha256": (
                    sha256_file(ANCHOR_SIGNED_MAPS)
                    if ANCHOR_SIGNED_MAPS.exists()
                    else None
                ),
            },
            "anchor_member_std_maps": {
                "path": str(ANCHOR_MEMBER_STD),
                "sha256": (
                    sha256_file(ANCHOR_MEMBER_STD)
                    if ANCHOR_MEMBER_STD.exists()
                    else None
                ),
            },
        }
        block = build_gate_block(
            checks={
                "tiling_identity": check1,
                "loader_identity": check2,
                "cross_env": check4,
                "score_identity": check5,
                "surface_identity": surface,
                "era_noop": era_noop,
            },
            pcg_rows=pcg_rows,
            pcg_rtol=float(method.pcg_rtol),
            pcg_maxiter=int(method.pcg_maxiter),
            tally_guard={"before": tally_before},
            artifacts=artifacts,
            meta={
                "seal_sha": seal_sha,
                "tile": "anchor",
                "source": "dc2021a",
                "m": M_MEMBERS,
                "root_int": root,
                "n_obs": int(framed.coords().shape[0]),
                "window_plan": {
                    "starts": [float(s) for s in plan.starts],
                    "w_days": float(plan.w_days),
                    "n_windows": len(plan.windows),
                },
                "wall_s": wall_s,
                "peak_rss_mib": peak_mib,
                "date": datetime.now(UTC).date().isoformat(),
            },
        )
        # Zero-touch assert BEFORE the block records (covers every prior
        # write: gate-5 pin, maps); the verified flag then rides INSIDE the
        # recorded block. The block write itself cannot touch tally keys,
        # and the post-record assert below refuses loudly if that ever
        # stops being true.
        assert_tally_unchanged(tally_before, evidence_path)
        block["tally_guard"]["byte_identical"] = True
        record_anchor_gate(block, evidence_path=evidence_path)
        assert_tally_unchanged(tally_before, evidence_path)

        code = gate_exit_code(block)
        _echo(json.dumps(block, indent=1, default=str))
        if code == EXIT_PIN23:
            _echo(
                "PIN-23 STOP: anchor solve leg(s) exited at the iteration "
                "cap over rtol — recorded above; IMMEDIATE owner STOP, "
                "separate from the normal gate walk."
            )
        elif code == 0:
            _echo(
                "GATE GREEN — TWO checks run and passed (tiling, score), TWO "
                "cited and pre-ratified at Gate 0 (loader, cross-env), ONE "
                "proxy-passed (surface identity) with the specified check "
                "(era no-op, SPEC §10 check 3) DEFERRED. Not 'five green'."
            )
        else:
            _echo("GATE RED — the stage STOPS here (block recorded)")
        return code
    finally:
        stop_beat.set()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@app.command()
def sizing() -> None:
    """Print the anchor sizing model + the 2x RAM-gate threshold (no data)."""
    model = anchor_size_model()
    typer.echo(
        json.dumps(
            {
                "model": {k: round(v, 1) for k, v in model.items()},
                "threshold_mib": round(2.0 * model["peak_model_mib"], 1),
                "rule": "launch gate: MemAvailable >= 2 x peak_model_mib",
            }
        )
    )


@app.command()
def run() -> None:
    """Run the ANCHOR IDENTITY GATE (checks 1/5 + surface identity, cites 2/4).

    The era no-op (SPEC §10 check 3) is recorded DEFERRED, never run and
    never proxy-passed (owner ruling 2026-07-26).

    Raises:
        typer.Exit: Nonzero on ANY failing check (the stage stops) and
            :data:`EXIT_PIN23` on a capped solve leg (pin-23 owner STOP).
    """
    code = _run_real_leg(EVIDENCE)
    if code != 0:
        raise typer.Exit(code=code)


if __name__ == "__main__":
    app()
