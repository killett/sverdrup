"""Phase-13 Task-13: the ONE c2 touch (owner-authorized fresh 2026-07-21).

Ceremony order (template verbatim; Phase-12 ``15b09c3`` precedent):
authorization (exact-string env) -> one-invocation protocol matrix ->
provenance tripwire (content-hash of every gate-reviewed artifact,
BEFORE the c2 file opens; never a re-solve) -> c2 load with the
provenance guard -> window tripwire (n = 44,844 + year-span) -> the
sealed reading -> ONE write of ``phase13.miost.c2_acceptance``.

Substrate: the chain-lane-D winner acceptance artifacts
(phase13_winner_mean.nc / _var.nc / _members.npz) + the REFIT s(x)
field (phase13_field_miost.json, reconstructed byte-deterministically
from the recorded ``phase13.miost.refit.winner_field`` — the miost5
field is NOT transferable across an R change).

``--record-provenance`` (pre-touch, no c2 access): writes the field
artifact from the refit evidence and records the content hashes the
touch's tripwire recomputes against.

Tally arithmetic on this touch: {miost5: 2 -> 3, miost6: 1}.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np

_OURS = Path("data/2021a_ssh_mapping_ose/ours")
_RESULTS = _OURS / "stage_miost_gate_results.json"
_MEAN = _OURS / "phase13_winner_mean.nc"
_VAR = _OURS / "phase13_winner_var.nc"
_STORE = _OURS / "phase13_winner_members.npz"
_FIELD = _OURS / "phase13_field_miost.json"
_C2_TRACK = Path(
    "data/2021a_ssh_mapping_ose/dc_obs/"
    "dt_gulfstream_c2_phy_l3_20161201-20180131_285-315_23-53.nc"
)

_PREFIX = "phase13.miost"
_DEFECT_KEY_PREFIX = "c2_defect_run_"
_C2_CORRECTED_FLAG = "SVERDRUP_MIOST_C2_CORRECTED"
#: Tally AFTER this touch (the miost5 five-mission lineage takes it).
_TALLY = {"miost5": 3, "miost6": 1}


def _p12() -> Any:  # noqa: ANN401 — dynamic script module (established pattern)
    """Load the Phase-12 touch module (ceremony helpers reused verbatim)."""
    spec = importlib.util.spec_from_file_location(
        "phase12_miost6_run", Path("scripts/phase12_miost6_run.py")
    )
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load scripts/phase12_miost6_run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_results() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_RESULTS.read_text()))


def _write_evidence(key_path: str, value: object) -> None:
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    results = _read_results()
    node: dict[str, Any] = results
    keys = key_path.split(".")
    for k in keys[:-1]:
        node = node.setdefault(k, {})
    node[keys[-1]] = value
    atomic_write_json(_RESULTS, results)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _refit_cal() -> Any:  # noqa: ANN401 — CalibrationField union
    """The refit s(x) field, reconstructed from the recorded evidence."""
    from sverdrup.distributions.calibration import (  # noqa: PLC0415
        calibration_from_json,
    )

    wf = _read_results()["phase13"]["miost"]["refit"]["winner_field"]
    cal = calibration_from_json(wf["to_json"])
    if cal.key() != wf["cal_key"]:
        raise SystemExit(
            "REFUSED: reconstructed calibration key != recorded cal_key — "
            "the refit evidence is inconsistent; owner adjudication"
        )
    return cal


def record_provenance() -> None:
    """Pre-touch: write the field artifact + the content-hash block.

    No c2 access here. The touch's tripwire recomputes every hash below
    and refuses on any mismatch BEFORE the c2 file opens.
    """
    cal = _refit_cal()
    wf = _read_results()["phase13"]["miost"]["refit"]["winner_field"]
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    atomic_write_json(_FIELD, {"calibration": wf["to_json"], "cal_key": wf["cal_key"]})
    ev = _read_results()
    members = ev["phase13"]["miost"]["members"]
    winner = ev["phase13"]["miost"]["lanes"][members["chain_lane"]]["winner"]
    block = {
        "mean_maps_sha256": _sha(_MEAN),
        "var_maps_sha256": _sha(_VAR),
        "member_store_sha256": _sha(_STORE),
        "field_artifact_sha256": _sha(_FIELD),
        "cal_key": cal.key(),
        "member_root_str": str(members["root_int"]),
        "chain_lane": members["chain_lane"],
        "winner_index": winner["index"],
        "winner_trial": winner["trial"],
        "written_utc": datetime.now(UTC).isoformat(),
    }
    _write_evidence(f"{_PREFIX}.provenance", block)
    print(
        "[provenance] recorded (mean/var/store/field sha256 + cal_key + "
        f"root); field artifact written: {_FIELD}",
        flush=True,
    )


def provenance_tripwire(recorded: dict[str, Any]) -> None:
    """Recompute EVERY provenance field from disk; refuse on any mismatch.

    Runs BEFORE the c2 file opens (never a re-solve).

    Args:
        recorded: The ``phase13.miost.provenance`` block.

    Raises:
        SystemExit: On any hash/key mismatch with the gate-reviewed
            artifacts.
    """
    for p in (_MEAN, _VAR, _STORE, _FIELD):
        if not p.exists():
            raise SystemExit(
                f"PROVENANCE-TRIPWIRE defect-STOP: artifact missing: {p} — "
                "the touch substrate is not the gate-reviewed artifact set. "
                "No c2 data loaded."
            )
    cal = _refit_cal()
    checks = {
        "mean_maps_sha256": _sha(_MEAN),
        "var_maps_sha256": _sha(_VAR),
        "member_store_sha256": _sha(_STORE),
        "field_artifact_sha256": _sha(_FIELD),
        "cal_key": cal.key(),
    }
    for field, current in checks.items():
        if recorded.get(field) != current:
            raise SystemExit(
                f"PROVENANCE-TRIPWIRE defect-STOP ({field}): recorded "
                f"{recorded.get(field)!r} != recomputed {current!r} — the "
                "touch substrate is not the gate-reviewed artifact set. "
                "No c2 data loaded."
            )


def check_touch_protocol(
    evidence: dict[str, Any], env: dict[str, str] | None = None
) -> None:
    """One-invocation mechanics (phase-8 owner-rider-3 matrix, phase13 keys).

    no C: no ``c2_acceptance`` -> PROCEED (the first touch); present ->
    REFUSE (spent). C set: (A, no D) or (no A, D) -> PROCEED; A and D ->
    REFUSE (third invocation); neither -> REFUSE (flag invalid).

    Args:
        evidence: The parsed evidence JSON.
        env: Environment mapping (defaults to ``os.environ``).

    Raises:
        SystemExit: On every REFUSE row; no data loaded.
    """
    import os  # noqa: PLC0415

    e = os.environ if env is None else env
    corrected = e.get(_C2_CORRECTED_FLAG) == "1"
    m = evidence.get("phase13", {}).get("miost", {})
    acceptance = "c2_acceptance" in m
    defect = any(k.startswith(_DEFECT_KEY_PREFIX) for k in m)

    if not corrected:
        if acceptance:
            raise SystemExit(
                "REFUSED: phase13.miost.c2_acceptance already exists — the "
                "ONE touch is spent. A corrected re-touch requires "
                f"{_C2_CORRECTED_FLAG}=1 + a dated defect key. No data loaded."
            )
        return
    if acceptance and defect:
        raise SystemExit(
            "REFUSED: third invocation — c2_acceptance exists alongside a "
            "defect key; further touches are owner-gated. No data loaded."
        )
    if not acceptance and not defect:
        raise SystemExit(
            f"REFUSED: {_C2_CORRECTED_FLAG}=1 is invalid without a recorded "
            "defect — nothing to correct. No data loaded."
        )


def migrate_defect_run(evidence: dict[str, Any], date_str: str) -> bool:
    """Move a defective acceptance under a dated defect key (corrected path).

    Args:
        evidence: The parsed evidence JSON (mutated in place).
        date_str: YYYYMMDD suffix for the defect key.

    Returns:
        True if a migration happened.
    """
    m = evidence.get("phase13", {}).get("miost", {})
    if "c2_acceptance" not in m:
        return False
    m[f"{_DEFECT_KEY_PREFIX}{date_str}"] = m.pop("c2_acceptance")
    return True


def c2_touch_main() -> None:
    """The ONE phase-13 c2 touch. Ceremony order per the module docstring."""
    from sverdrup.application.calibration import regions as R  # noqa: PLC0415, N812
    from sverdrup.application.calibration.constants import (  # noqa: PLC0415
        COVERAGE_TARGET,
        COVERAGE_TOL,
        SIGMA_OBS2,
    )
    from sverdrup.validation.their_eval import score as their_score  # noqa: PLC0415

    p12 = _p12()
    p12.check_authorized()
    evidence = _read_results()
    check_touch_protocol(evidence)

    recorded_prov = evidence.get("phase13", {}).get("miost", {}).get("provenance")
    if not recorded_prov:
        raise SystemExit(
            "REFUSED: phase13.miost.provenance absent — run "
            "--record-provenance first. No c2 data loaded."
        )
    provenance_tripwire(recorded_prov)
    print(
        "[touch] provenance tripwire PASS (mean/var/store/field sha256 + "
        "cal_key recomputed, bit-match)",
        flush=True,
    )

    date_str = datetime.now(UTC).strftime("%Y%m%d")
    if migrate_defect_run(evidence, date_str):
        _write_evidence(
            f"{_PREFIX}.{_DEFECT_KEY_PREFIX}{date_str}",
            evidence["phase13"]["miost"][f"{_DEFECT_KEY_PREFIX}{date_str}"],
        )
        print(f"[touch] defect run migrated to {_DEFECT_KEY_PREFIX}{date_str}")

    print("[touch] opening the c2 track (the ONE authorized touch)", flush=True)
    lon, lat, tt, resid, v = p12._interp_c2(_MEAN, _VAR, _C2_TRACK)  # noqa: SLF001
    tripwire = p12.window_tripwire(int(resid.size), tt)
    print(f"[touch] window tripwire PASS (n={resid.size})", flush=True)

    triplet = [float(x) for x in their_score(_MEAN, _C2_TRACK)]
    cal = _refit_cal()
    vt = (cal.sqrt_s_at(lon, lat) ** 2) * v + SIGMA_OBS2
    aggregate = p12._cal_stats(resid, vt)  # noqa: SLF001

    jet_cells = np.asarray(
        json.loads((_OURS / "phase8_jet_core_mask.json").read_text())["mask"],
        dtype=bool,
    )
    row, col = R.cell_index(lon, lat)
    jet_pts = jet_cells[row, col]
    regional = {}
    for reg, mask in R.evaluation_masks(lon, lat, jet_pts).items():
        if mask.any():
            regional[reg] = p12._cal_stats(resid[mask], vt[mask])  # noqa: SLF001
    months = np.asarray(tt, dtype="datetime64[M]").astype(int) % 12 + 1
    monthly = {
        f"{mo:02d}": p12._cal_stats(  # noqa: SLF001
            resid[months == mo], vt[months == mo]
        )
        for mo in range(1, 13)
        if (months == mo).any()
    }

    acceptance = {
        "mu_sigma_lambda_x": triplet,
        "aggregate_calibration": aggregate,
        "regional_table": regional,
        "monthly_table": monthly,
        "window_tripwire": tripwire,
        "reading_frame": {
            "coverage_bar": {"target": COVERAGE_TARGET, "tol": COVERAGE_TOL},
            "coverage_baseline_miost5": p12.COVERAGE_BASELINE,
            "coverage_baseline_scalar_era": p12.COVERAGE_BASELINE_SCALAR_ERA,
            "mu_hard_floor": p12.MU_HARD_FLOOR,
            "sigma_convention": (
                "s(x)*v + SIGMA_OBS2 (track-side, phase8 convention; s(x) = "
                "the phase13 REFIT field)"
            ),
            "miost5_regional_reference": "phase8.c2_acceptance.regional_table",
            "gate1_triplet_reference": "phase13.miost.diagnostics (carried)",
        },
        "c2_touch_tally": dict(_TALLY),
        "semantics": (
            "the ONE phase-13 c2 touch (owner-authorized fresh 2026-07-21; "
            "chain-lane-D winner substrate content-hash-asserted at entry; "
            "nothing refit on c2; three-branch ruling is the owner's message)"
        ),
        "written_utc": datetime.now(UTC).isoformat(),
    }
    _write_evidence(f"{_PREFIX}.c2_acceptance", acceptance)
    print("[touch] c2_acceptance written — the ONE touch is spent", flush=True)
    print(json.dumps(acceptance, indent=2))


def main() -> None:
    """CLI dispatch."""
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--record-provenance", action="store_true")
    mode.add_argument("--c2-touch", action="store_true")
    args = ap.parse_args()
    if args.record_provenance:
        record_provenance()
    else:
        c2_touch_main()


if __name__ == "__main__":
    main()
