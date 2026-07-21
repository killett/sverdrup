"""Phase-13 comparison read → BRANCH record (plan Task 9; spec §7/§10).

Reads the three recorded lane winners plus the CO-SEALED lane-0 reference
and writes the claim-bearing verdict block at ``phase13.miost.lanes.verdict``:

- SINGLE-EXECUTION GUARD first: an existing verdict refuses the run — the
  pre-registered misfire protocol (owner, 2026-07-20) routes any corrected
  read through owner adjudication under a dated defect key, never a silent
  re-execution.
- REFUSAL CLOCK next (plan AC 1): the sealed band protocol must predate
  every consulted WINNER record (``assert_band_predates``). lane-0 has no
  post-seal record to clock — it is co-sealed WITH the protocol — so its
  integrity check is byte-level instead: recompute sha256 of the residuals
  npz and match the sealed ``residuals_sha256``.
- Bands computed AT READ TIME per consulted pair (single seeded execution
  each): PRIMARY = lane-C winner vs lane-0 (claim-bearing); D-vs-0 and
  modes-only-vs-0 as designated never-claim-bearing secondaries; C-vs-D
  for the winner-lane rule.
- Lexicographic µ→λx with BOTH degradation criteria via the sealed
  ``lane_compare`` machinery (``_lambda_usable`` enforces the usability
  fraction AND the band-width rule); verdict wording via the pinned
  ``primary_wording`` branch strings.
- WINNER-LANE RULE (spec §10 owner pin): C-vs-D within band → the SIMPLER
  lane (D) takes the acceptance chain; the conditional modes-only lane is
  never claim-bearing and NEVER ships regardless of its numbers.
- BRANCH RECORDED verbatim: negative → Task 10; winner → Tasks 11-14 on
  the chain lane.

The held-out challenge track is never read here: this script consumes only
recorded winner blocks, the sealed artifact, and persisted validation-track
residuals.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np

from sverdrup.application.tuning.lane_compare import (
    BandProtocol,
    BandValues,
    _lambda_usable,
    adjudicate_primary,
    assert_band_predates,
    compute_bands,
    load_protocol,
    primary_wording,
)
from sverdrup.eval.spectral import effective_resolution_lambda_x

_RESULTS = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
_SWEEP_LANES = ("D", "C", "modes-only")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _read_evidence() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_RESULTS.read_text()))


def _write_evidence(key_path: str, value: object) -> None:
    """Atomic nested-key write (phase10_compare pattern; single writer)."""
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    results = json.loads(_RESULTS.read_text())
    keys = key_path.split(".")
    node: dict[str, Any] = results
    for k in keys[:-1]:
        node = node.setdefault(k, {})
    node[keys[-1]] = value
    atomic_write_json(_RESULTS, results)


def _loader(rec: dict[str, Any]) -> dict[str, np.ndarray]:
    """Load a record's persisted validation-track arrays.

    Args:
        rec: A lane record carrying ``residuals_npz``.

    Returns:
        The persisted track arrays keyed as saved.
    """
    with np.load(rec["residuals_npz"], allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def lane0_record(artifact: dict[str, Any]) -> dict[str, Any]:
    """Build the lane-0 side from the CO-SEALED reference block.

    lane-0 predates the seal by construction (its arrays are sealed WITH
    the protocol), so the refusal clock cannot apply; the integrity check
    is byte-level instead.

    Args:
        artifact: The parsed sealed band artifact.

    Returns:
        A record shaped for the pair-band loader.

    Raises:
        SystemExit: On a sha256 mismatch between the residuals npz bytes
            and the sealed ``residuals_sha256`` (a clobbered reference must
            never anchor the claim-bearing read).
    """
    ref = artifact["lane0_reference"]
    recomputed = hashlib.sha256(Path(ref["residuals_npz"]).read_bytes()).hexdigest()
    if recomputed != ref["residuals_sha256"]:
        raise SystemExit(
            f"lane-0 residuals sha mismatch: sealed {ref['residuals_sha256']} "
            f"!= recomputed {recomputed} — the co-sealed reference has been "
            "altered; REFUSING the read (misfire protocol: owner adjudication)"
        )
    return {
        "lane": "lane0",
        "residuals_npz": ref["residuals_npz"],
        "scores": {"mu_score": ref["mu_score"]},
        "integrity": {
            "residuals_sha256_sealed": ref["residuals_sha256"],
            "residuals_sha256_recomputed": recomputed,
            "match": True,
        },
    }


def _pair_row(
    w_a: dict[str, Any],
    w_b: dict[str, Any],
    protocol: BandProtocol,
    load_track: Callable[[dict[str, Any]], Mapping[str, np.ndarray]],
    bands_fn: Callable[..., BandValues],
    lambda_x_fn: Callable[..., float],
) -> dict[str, Any]:
    """One consulted pair's read-time row (single seeded execution).

    Args:
        w_a: Side-a record (the challenger lane).
        w_b: Side-b record (the incumbent).
        protocol: The sealed band protocol.
        load_track: Maps a record to its persisted track arrays.
        bands_fn: The band computation (injectable for tests; the real read
            uses :func:`compute_bands`).
        lambda_x_fn: The λx estimator.

    Returns:
        The evidence-ready row (bands + branch + wording + write-time).
    """
    bv = bands_fn(load_track(w_a), load_track(w_b), protocol, lambda_x_fn)
    usable, note = _lambda_usable(bv, protocol)
    branch, positive = adjudicate_primary(bv, usable)
    return {
        "rule": "lexicographic mu->lambda_x, BOTH degradation criteria (spec §7)",
        "a_lane": w_a.get("lane"),
        "b_lane": w_b.get("lane"),
        "a_scores": w_a.get("scores"),
        "b_scores": w_b.get("scores"),
        "positive": positive,
        "branch": branch,
        # The pinned wording strings hardcode "beats lane-0" — only a
        # lane-0 comparison may carry them (dual-review finding).
        "wording": (
            primary_wording(str(w_a.get("lane")), positive, branch)
            if w_b.get("lane") == "lane0"
            else None
        ),
        "note": note,
        "delta_mu": bv.delta_mu,
        "band_mu": bv.band_mu,
        "delta_lambda_x": bv.delta_lambda_x,
        "band_lambda_x": bv.band_lambda_x,
        "lambda_informative": bv.lambda_informative,
        "n_segments": bv.n_segments,
        "n_lambda_used": bv.n_lambda_used,
        "protocol_sha": bv.protocol_sha,
        "written_utc": _now(),
    }


def assemble_verdict(
    winners: dict[str, dict[str, Any]],
    lane0: dict[str, Any],
    protocol: BandProtocol,
    load_track: Callable[[dict[str, Any]], Mapping[str, np.ndarray]],
    bands_fn: Callable[..., BandValues] = compute_bands,
    lambda_x_fn: Callable[..., float] = effective_resolution_lambda_x,
) -> dict[str, Any]:
    """Assemble the full verdict block (refusal clock FIRST).

    Args:
        winners: The three sweeping-lane winner records keyed by lane.
        lane0: The co-sealed lane-0 record (:func:`lane0_record`).
        protocol: The sealed band protocol.
        load_track: Maps a record to its persisted track arrays.
        bands_fn: The band computation (injectable for tests).
        lambda_x_fn: The λx estimator (injectable for tests).

    Returns:
        The evidence-ready verdict block with BRANCH recorded.

    Raises:
        PreRegistrationError: If any consulted winner record does not
            postdate the protocol seal (clock runs before any track load).
    """
    consulted = [winners[lane] for lane in _SWEEP_LANES]
    assert_band_predates(protocol, consulted)  # refusal clock FIRST

    primary = _pair_row(
        winners["C"], lane0, protocol, load_track, bands_fn, lambda_x_fn
    )
    primary["role"] = "PRIMARY (claim-bearing, sealed designation)"

    sec_d = _pair_row(winners["D"], lane0, protocol, load_track, bands_fn, lambda_x_fn)
    sec_d["role"] = "ATTRIBUTION secondary; same bands; never claim-bearing"
    sec_m = _pair_row(
        winners["modes-only"], lane0, protocol, load_track, bands_fn, lambda_x_fn
    )
    sec_m["role"] = (
        "conditional lane; attribution 2x2 cell; never claim-bearing; NEVER ships"
    )

    # Winner-lane rule (spec §10 owner pin): C-vs-D consulted pair; within
    # band -> the SIMPLER lane (D) takes the chain. adjudicate_primary's
    # non-positive branch collapses TIE and D-better into "within-band" —
    # both map to D (simpler AND at-least-equal), recorded honestly below.
    cd = _pair_row(
        winners["C"], winners["D"], protocol, load_track, bands_fn, lambda_x_fn
    )
    cd["role"] = "winner-lane rule pair (spec §10); never claim-bearing"
    chain_lane = ("C" if cd["positive"] else "D") if primary["positive"] else None
    winner_lane = {
        "rule": (
            "C-vs-D within band -> lane-D takes the acceptance chain "
            "(simpler lane on tie, spec §10)"
        ),
        "pair": cd,
        "chain_lane": chain_lane,
    }

    branch_recorded = (
        f"WINNER: Tasks 11-14 proceed on lane {chain_lane} "
        "(winner-lane rule applied; modes-only never ships)"
        if primary["positive"]
        else (
            "NEGATIVE: Task 10 close executes; Tasks 11-14 close as "
            "superseded (plan branch semantics; measured-not-shipped)"
        )
    )

    return {
        "created_utc": _now(),
        "rule": (
            "PRIMARY = lane-C winner vs lane-0 (sealed phase13 bands); "
            "lexicographic mu->lambda_x with BOTH degradation criteria; "
            "wording pin: non-positive reads 'improvements within band', "
            "never 'worse'"
        ),
        "refusal_clock": {
            "sealed_utc": protocol.created_utc,
            "winner_records_postdate": {
                lane: winners[lane]["created_utc"] for lane in _SWEEP_LANES
            },
        },
        "lane0_integrity": lane0.get("integrity"),
        "primary": primary,
        "secondary_d_vs_lane0": sec_d,
        "secondary_modes_only_vs_lane0": sec_m,
        "winner_lane_rule": winner_lane,
        "branch_recorded": branch_recorded,
        "protocol_sha": protocol.protocol_sha,
    }


def main() -> None:
    """Assemble and write ``phase13.miost.lanes.verdict`` (ONCE)."""
    ev = _read_evidence()
    p13 = ev.get("phase13", {})

    # SINGLE-EXECUTION GUARD before anything else (misfire protocol,
    # owner 2026-07-20): a second run never silently overwrites the read.
    if p13.get("miost", {}).get("lanes", {}).get("verdict"):
        raise SystemExit(
            "phase13.miost.lanes.verdict already exists — the single-"
            "execution rule refuses a re-run; a corrected read requires "
            "owner adjudication under a dated defect key (misfire protocol)"
        )

    proto_ptr = p13.get("band_protocol")
    if not proto_ptr:
        raise SystemExit("run scripts/phase13_prereg.py first (protocol missing)")
    protocol = load_protocol(Path(proto_ptr["path"]), expected_sha=proto_ptr["sha256"])
    artifact = cast(dict[str, Any], json.loads(Path(proto_ptr["path"]).read_text()))

    lanes = p13.get("miost", {}).get("lanes", {})
    winners: dict[str, dict[str, Any]] = {}
    for lane in _SWEEP_LANES:
        w = lanes.get(lane, {}).get("winner")
        if not w:
            raise SystemExit(f"lane {lane} has no recorded winner — run it first")
        winners[lane] = w

    lane0 = lane0_record(artifact)

    # REFUSAL CLOCK before anything else touches disk beyond the seals
    # (plan AC 1); assemble_verdict re-asserts it, harmlessly idempotent.
    assert_band_predates(protocol, [winners[lane] for lane in _SWEEP_LANES])

    # PRE-FLIGHT: load every consulted track BEFORE the first seeded band
    # computation (adversarial-review hardening T1) — a missing/corrupt npz
    # refuses up-front instead of aborting mid-ceremony.
    cached: dict[str, dict[str, np.ndarray]] = {
        str(rec["lane"]): _loader(rec) for rec in (lane0, *winners.values())
    }
    verdict = assemble_verdict(
        winners, lane0, protocol, lambda rec: cached[str(rec["lane"])]
    )
    _write_evidence("phase13.miost.lanes.verdict", verdict)

    p = verdict["primary"]
    print(
        f"[verdict] PRIMARY C-vs-lane0: {p['branch']} positive={p['positive']} "
        f"dmu={p['delta_mu']:+.7f} band={p['band_mu']:.7f} "
        f"dlx={p['delta_lambda_x']:+.2f} band_lx={p['band_lambda_x']:.2f} "
        f"lambda_informative={p['lambda_informative']}",
        flush=True,
    )
    w = verdict["winner_lane_rule"]
    print(
        f"[verdict] winner-lane rule: C-vs-D {w['pair']['branch']} -> "
        f"chain_lane={w['chain_lane']}",
        flush=True,
    )
    print(f"[verdict] {verdict['branch_recorded']}", flush=True)


if __name__ == "__main__":
    main()
