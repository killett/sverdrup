"""Phase-10 per-lane tuning execution (Task 7/8; spec §4).

Runs ONE lane's Sobol trials (screening subset — the contingency is ACTIVE
per the sealed budget) through the reused Phase-5 tuner loop with the
Phase-10 scorer seams, full-year re-scores the lane's top-k + anchors,
persists their validation-track residual arrays (band source), and selects
the lane winner via the read-time selection layer.

Scope discipline:
    SVERDRUP_PHASE10_SCOPE=dev  -> 12-day window, 2 trials, k=1; evidence
                                   under phase10.oi.lanes_dev.* (NEVER gate
                                   evidence).
    (default / full)            -> sealed screening days + budget numbers;
                                   evidence under phase10.oi.lanes.<lane>.

c2 is NEVER touched: train-only assimilation (c2 locked out by the standing
split), j3-only scoring, assert_scored_not_assimilated on every map.

Usage:
    SVERDRUP_PHASE10_SCOPE=dev pixi run python scripts/phase10_lane_run.py --lane lane0
    nohup pixi run python scripts/phase10_lane_run.py --lane lane0 > lane0.log 2>&1 &
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np

from sverdrup.application.calibration.constants import SIGMA_OBS2
from sverdrup.application.tuning.feasibility import CompositeFeasibility
from sverdrup.application.tuning.lane_compare import (
    load_protocol,
    primary_verdict,
    select_lane_winner,
)
from sverdrup.application.tuning.loop import tune
from sverdrup.application.tuning.objective import BASELINE_BAR_MU, ConstrainedObjective
from sverdrup.application.tuning.scorer import ValidationTrackScorer
from sverdrup.core.parameters import ParameterSpace
from sverdrup.eval.calibration import coverage
from sverdrup.eval.skill_score import leaderboard_nrmse
from sverdrup.eval.spectral import (
    ShortTrackError,
    UnresolvedScaleError,
    effective_resolution_lambda_x,
)
from sverdrup.validation.phase10_lanes import (
    ALL_DIMS,
    BOXES,
    LANES,
    anchors_for,
    lane_bars,
    provider_for_trial,
    sobol_trials,
)

_OUT_ROOT = Path("data/2021a_ssh_mapping_ose/ours")
_RESULTS = _OUT_ROOT / "stage_miost_gate_results.json"
_PROTOCOL_PATH = _OUT_ROOT / "phase10_band_artifact.json"
_VAL_TRACK = Path(
    "data/2021a_ssh_mapping_ose/dc_obs/"
    "dt_gulfstream_j3_phy_l3_20161201-20180131_285-315_23-53.nc"
)
# c2 never appears here; the standing split locks it out of assimilation.

_SCOPE = os.environ.get("SVERDRUP_PHASE10_SCOPE", "full")
if _SCOPE not in {"dev", "full"}:
    raise SystemExit(f"SVERDRUP_PHASE10_SCOPE must be 'dev' or 'full', got {_SCOPE!r}")

_DEV_DAYS = [float(d) for d in range(60, 72)]
_FULL_DAYS = [float(d) for d in range(0, 365)]
_MU_BAR = BASELINE_BAR_MU  # λx computed only above the µ floor (scorer contract)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _evidence_root(lane: str) -> str:
    base = "phase10.oi.lanes" if _SCOPE == "full" else "phase10.oi.lanes_dev"
    return f"{base}.{lane}"


def _write_evidence(key_path: str, value: object) -> None:
    """Atomic nested-key write (phase9_fit_run pattern).

    SINGLE-WRITER DISCIPLINE: lanes run SEQUENTIALLY (V consumes lane-0's
    winner anyway); running two lanes in parallel would race this
    read-modify-write and lose records.
    """
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


def _read_evidence() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_RESULTS.read_text()))


def _load_ctx() -> dict[str, Any]:
    """Load obs (train split), grid, half-window, MDT — the probe pattern."""
    from sverdrup.application.splits import make_splits  # noqa: PLC0415
    from sverdrup.validation.input_adapter import (  # noqa: PLC0415
        load_mapping_obs,
        load_mdt_grid,
    )
    from sverdrup.validation.params import baseline_config  # noqa: PLC0415
    from sverdrup.validation.run import _subset  # noqa: PLC0415

    obs_dir = Path("data/2021a_ssh_mapping_ose/dc_obs")
    mapping = [
        obs_dir / f"dt_gulfstream_{m}_phy_l3_20161201-20180131_285-315_23-53.nc"
        for m in ("alg", "h2g", "j2g", "j2n", "j3", "s3a")
    ]
    provider, grid, half = baseline_config()
    obs_all = load_mapping_obs(mapping, provider)
    split = make_splits(
        obs_all, by="mission", locked_missions=["c2"], validation_missions=["j3"]
    )
    train = _subset(obs_all, split.train_idx)
    mdt = load_mdt_grid(mapping, grid)
    return {"train": train, "grid": grid, "half": half, "mdt": mdt}


def _interp_track(mean_p: Path, var_p: Path) -> dict[str, np.ndarray]:
    """Interp mean+var maps onto the j3 track (harness box; finite subset)."""
    from sverdrup.validation.provenance_guard import (  # noqa: PLC0415
        assert_scored_not_assimilated,
    )
    from sverdrup.validation.vendor import prepare_vendored_imports  # noqa: PLC0415

    assert_scored_not_assimilated(mean_p, _VAL_TRACK)
    prepare_vendored_imports()
    from src.mod_inout import read_l3_dataset  # noqa: PLC0415
    from src.mod_interp import interp_on_alongtrack  # noqa: PLC0415

    box = dict(
        lon_min=295.0,
        lon_max=305.0,
        lat_min=33.0,
        lat_max=43.0,
        time_min="2017-01-01",
        time_max="2018-01-01",
    )
    ds_at = read_l3_dataset(str(_VAL_TRACK), **box)
    t_a, lat_a, lon_a, ssh, mu = interp_on_alongtrack(
        str(mean_p), ds_at, is_circle=False, **box
    )
    _, _, _, _, var = interp_on_alongtrack(str(var_p), ds_at, is_circle=False, **box)
    ssh, mu, var = (np.asarray(a, float) for a in (ssh, mu, var))
    ok = np.isfinite(ssh) & np.isfinite(mu) & np.isfinite(var) & (var > 0)
    return {
        "time": np.asarray(t_a)[ok],
        "lat": np.asarray(lat_a, float)[ok],
        "lon": np.asarray(lon_a, float)[ok],
        "ssh": ssh[ok],
        "mean_interp": mu[ok],
        "var_interp": var[ok],
    }


def _scores_from_track(trk: dict[str, np.ndarray]) -> dict[str, float]:
    """Score a persisted track: µ, coverage (var + SIGMA_OBS2), λx above bar."""
    mu = leaderboard_nrmse(trk["ssh"], trk["mean_interp"])
    scores = {
        "mu_score": mu,
        "coverage_1sigma": float(
            coverage(
                trk["mean_interp"], trk["var_interp"] + SIGMA_OBS2, trk["ssh"], 1.0
            )
        ),
    }
    if mu >= _MU_BAR:
        try:
            scores["lambda_x"] = float(
                effective_resolution_lambda_x(
                    trk["time"], trk["lat"], trk["lon"], trk["ssh"], trk["mean_interp"]
                )
            )
        except (ShortTrackError, UnresolvedScaleError) as exc:
            scores["lambda_x_error"] = float("nan")
            print(f"  [warn] lambda_x failed: {type(exc).__name__}", flush=True)
    return scores


def _full_year_score_and_persist(
    trial: dict[str, float], ctx: dict[str, Any], npz_path: Path, days: list[float]
) -> dict[str, float]:
    """Full-scope re-score of one trial; persists the residual-track npz."""
    import tempfile  # noqa: PLC0415

    from sverdrup.validation.run import run_mean_var_maps  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as td:
        mean_p, var_p = Path(td) / "mean.nc", Path(td) / "var.nc"
        run_mean_var_maps(
            "oi",
            ctx["train"],
            provider_for_trial(trial),
            ctx["grid"],
            ctx["half"],
            days,
            mean_p,
            var_p,
            mdt_grid=ctx["mdt"],
            oi_gaussian_kernel_from_params=True,
        )
        trk = _interp_track(mean_p, var_p)
    np.savez(npz_path, **cast(Any, trk))
    return _scores_from_track(trk)


def make_record(
    *,
    lane: str,
    index: int,
    anchor: bool,
    scope: str,
    trial: dict[str, float],
    scores: dict[str, float] | None,
    feasible: bool = True,
    exclusion_reason: str | None = None,
    created_utc: str,
    residuals_npz: str | None = None,
) -> dict[str, Any]:
    """Build one evidence record (pure; per-bar outcomes itemized).

    Args:
        lane: Lane name.
        index: Trial index within the lane run (anchors follow Sobol trials).
        anchor: Whether this is a pre-registered anchor evaluation.
        scope: ``"screening"`` or ``"full"``.
        trial: The six-dim trial dict.
        scores: The score vector (None for unscorable trials).
        feasible: The tuner-loop feasibility flag.
        exclusion_reason: Why the trial went unscored, if it did.
        created_utc: Record write-time (ISO 8601, tz-aware).
        residuals_npz: Persisted track path (full scope only).

    Returns:
        The evidence-ready record with ``bars`` (per-bar pass/fail) and
        ``admissible`` (all bars pass).
    """
    bars = {b.metric: bool(scores and b.passes(scores)) for b in lane_bars()}
    rec: dict[str, Any] = {
        "created_utc": created_utc,
        "lane": lane,
        "index": index,
        "anchor": anchor,
        "scope": scope,
        "trial": trial,
        "scores": scores,
        "feasible": feasible,
        "exclusion_reason": exclusion_reason,
        "bars": bars,
        "admissible": bool(scores) and all(bars.values()),
    }
    if residuals_npz is not None:
        rec["residuals_npz"] = residuals_npz
    return rec


class _CheckpointScorer:
    """Wraps the trial scorer: per-trial record persisted AS SCORED.

    An overnight screening pass (~30 trials × ~8 min) must not lose hours of
    work to a crash — every trial's record (with a REAL per-trial write-time)
    lands in the evidence JSON before the next trial starts.
    """

    def __init__(
        self,
        inner: ValidationTrackScorer,
        lane: str,
        n_sobol: int,
        sink_key: str,
    ) -> None:
        self.inner = inner
        self.lane = lane
        self.n_sobol = n_sobol
        self.sink_key = sink_key
        self.records: list[dict[str, Any]] = []

    def _checkpoint(self, rec: dict[str, Any]) -> None:
        self.records.append(rec)
        _write_evidence(self.sink_key, self.records)

    def score(
        self,
        method_name: str,
        params: dict[str, float],
        split: object,
        seed: int,
        window: object,
    ) -> dict[str, float]:
        """Score one trial, checkpointing the record either way."""
        idx = len(self.records)
        try:
            scores = self.inner.score(method_name, params, split, seed, window)
        except (UnresolvedScaleError, ShortTrackError) as exc:
            self._checkpoint(
                make_record(
                    lane=self.lane,
                    index=idx,
                    anchor=idx >= self.n_sobol,
                    scope="screening",
                    trial=params,
                    scores=None,
                    exclusion_reason=type(exc).__name__,
                    created_utc=_now(),
                )
            )
            raise  # tune() records the unscorable trial too (its own ledger)
        self._checkpoint(
            make_record(
                lane=self.lane,
                index=idx,
                anchor=idx >= self.n_sobol,
                scope="screening",
                trial=params,
                scores=scores,
                created_utc=_now(),
            )
        )
        return scores


class _PairedTrials:
    """SearchStrategy proposing the lane's pre-paired masked Sobol trials."""

    def __init__(self, trials: list[dict[str, float]]) -> None:
        self.trials = trials

    def propose(self, space: object, history: object) -> list[dict[str, float]]:
        """Return the pre-drawn paired trials (single round)."""
        return self.trials


class _Win:
    def __init__(self, wid: str) -> None:
        self.id = wid


def main() -> None:
    """Run one lane end-to-end: screening -> full re-scores -> winner."""
    parser = argparse.ArgumentParser(description="Phase-10 lane run (spec §4).")
    parser.add_argument("--lane", choices=sorted(LANES), required=True)
    args = parser.parse_args()
    lane = args.lane

    ev = _read_evidence()
    oi_ev = ev.get("phase10", {}).get("oi", {})
    budget = oi_ev.get("probe", {}).get("budget")
    proto_ptr = oi_ev.get("band_protocol")
    if not budget or not proto_ptr:
        raise SystemExit("run phase10_prereg.py first (budget/protocol missing)")
    protocol = load_protocol(Path(proto_ptr["path"]), expected_sha=proto_ptr["sha256"])
    artifact = json.loads(Path(proto_ptr["path"]).read_text())

    if _SCOPE == "dev":
        screening_days = _DEV_DAYS
        full_days = _DEV_DAYS
        n_trials, k = 2, 1
    else:
        if not budget["contingency_active"]:
            raise SystemExit(
                "contingency inactive: this runner implements the screening "
                "path only (sealed budget said ACTIVE) — refuse to improvise"
            )
        screening_days = [float(d) for d in artifact["screening_days"]]
        full_days = _FULL_DAYS
        n_trials = int(budget["screening"]["n_sobol_per_lane"])
        k = int(artifact["screening_k"])

    winners_prior: dict[str, dict[str, float]] = {}
    for other in LANES:
        w = oi_ev.get("lanes", {}).get(other, {}).get("winner")
        if w and _SCOPE == "full":
            winners_prior[other] = {d: float(w["trial"][d]) for d in ALL_DIMS}
    anchors = anchors_for(lane, winners_prior)

    trials = sobol_trials(lane, n_trials)
    print(
        f"[lane {lane}] scope={_SCOPE} n_trials={n_trials} anchors={len(anchors)} "
        f"k={k} screening_days={len(screening_days)}",
        flush=True,
    )

    ctx = _load_ctx()
    scorer = ValidationTrackScorer(
        train_obs=ctx["train"],
        grid=ctx["grid"],
        output_days=screening_days,
        temporal_half_window_days=ctx["half"],
        val_track_path=_VAL_TRACK,
        lon_min=295.0,
        lon_max=305.0,
        lat_min=33.0,
        lat_max=43.0,
        time_min="2017-01-01",
        time_max="2018-01-01",
        mdt_grid=ctx["mdt"],
        oi_gaussian_kernel_from_params=True,
        provider_factory=provider_for_trial,
        coverage_extra_var=float(SIGMA_OBS2),
    )
    objective = ConstrainedObjective(bars=lane_bars())

    # ------------------------------------------------------------------
    # Screening pass (paired Sobol + anchors) through the REUSED tuner loop;
    # per-trial records checkpointed AS SCORED (crash-durable).
    # ------------------------------------------------------------------
    t0 = time.monotonic()
    ckpt = _CheckpointScorer(
        scorer, lane, len(trials), f"{_evidence_root(lane)}.records"
    )
    tune(
        method_name="oi",
        space=ParameterSpace(bounds=dict(BOXES)),
        strategy=_PairedTrials(trials + anchors),
        predicate=CompositeFeasibility(()),
        objective=objective,
        scorer=cast(Any, ckpt),
        split=None,
        seed=0,
        window=_Win(f"phase10-{lane}-screening"),
        tile_geometry=cast(Any, None),
        required_capabilities=frozenset(),
        on_empty="return_history",
    )
    records = ckpt.records
    print(
        f"[lane {lane}] screening done in {time.monotonic() - t0:.0f}s "
        f"({sum(1 for r in records if r['admissible'])} admissible)",
        flush=True,
    )

    # ------------------------------------------------------------------
    # Full-scope re-scores: top-k screening admissible + ALL anchors.
    # ------------------------------------------------------------------
    admissible = [r for r in records if r["admissible"]]
    ranked = sorted(admissible, key=lambda r: r["scores"]["mu_score"], reverse=True)
    chosen: list[dict[str, Any]] = ranked[:k] + [
        r for r in records if r["anchor"] and r not in ranked[:k] and r["admissible"]
    ]
    smoke_fallback = False
    if not chosen and _SCOPE == "dev":
        # DEV-ONLY plumbing fallback: on a 12-day window two arbitrary Sobol
        # points can legitimately fail the LIVE bars (that is the design
        # working); the smoke still needs to exercise the full-score/persist/
        # selection path. Labeled loudly; NEVER the full-scope semantics.
        smoke_fallback = True
        scored = [r for r in records if r["scores"]]
        chosen = sorted(scored, key=lambda r: r["scores"]["mu_score"], reverse=True)[:k]
        print(
            f"[lane {lane}] DEV SMOKE FALLBACK: no admissible trial; selecting "
            "over inadmissible records to exercise plumbing only",
            flush=True,
        )
    if not chosen:
        _write_evidence(f"{_evidence_root(lane)}.winner", None)
        raise SystemExit(f"[lane {lane}] NO admissible screening trial — STOP")

    full_records: list[dict[str, Any]] = []
    for j, src in enumerate(chosen):
        npz = _OUT_ROOT / f"phase10_residuals_{lane}_{src['index']}.npz"
        if _SCOPE == "dev":
            npz = _OUT_ROOT / f"phase10_residuals_dev_{lane}_{src['index']}.npz"
        t1 = time.monotonic()
        scores = _full_year_score_and_persist(src["trial"], ctx, npz, full_days)
        entry = make_record(
            lane=lane,
            index=src["index"],
            anchor=src["anchor"],
            scope="full",
            trial=src["trial"],
            scores=scores,
            created_utc=_now(),
            residuals_npz=str(npz),
        )
        if smoke_fallback:
            entry["admissible"] = True
            entry["smoke_admissible_override"] = True  # dev plumbing only
        full_records.append(entry)
        _write_evidence(f"{_evidence_root(lane)}.full_records", full_records)
        print(
            f"[lane {lane}] full re-score {j + 1}/{len(chosen)} "
            f"mu={scores.get('mu_score', float('nan')):.4f} "
            f"({time.monotonic() - t1:.0f}s)",
            flush=True,
        )

    # ------------------------------------------------------------------
    # Winner via the read-time selection layer (refusal clock inside).
    # ------------------------------------------------------------------
    def _loader(rec: dict[str, Any]) -> dict[str, np.ndarray]:
        with np.load(rec["residuals_npz"], allow_pickle=False) as z:
            return {k: z[k] for k in z.files}

    winner = select_lane_winner(full_records, protocol, _loader)
    _write_evidence(f"{_evidence_root(lane)}.winner", winner)
    print(
        f"[lane {lane}] WINNER index={winner['index']} "
        f"mu={winner['scores']['mu_score']:.4f} "
        f"lambda_x={winner['scores'].get('lambda_x', float('nan')):.1f} "
        f"branch={winner['adjudication']['branch']}",
        flush=True,
    )

    # Stage-1 SECONDARY row (attribution, never claim-bearing): V vs lane-0.
    if lane == "V":
        lane0_w = (
            _read_evidence()
            .get("phase10", {})
            .get("oi", {})
            .get("lanes" if _SCOPE == "full" else "lanes_dev", {})
            .get("lane0", {})
            .get("winner")
        )
        if lane0_w:
            row = primary_verdict(winner, lane0_w, protocol, _loader)
            row["role"] = "SECONDARY (attribution, never claim-bearing)"
            _write_evidence(
                f"{'phase10.oi.lanes' if _SCOPE == 'full' else 'phase10.oi.lanes_dev'}"
                ".stage1_secondary_v_vs_lane0",
                row,
            )
            print(
                f"[lane {lane}] secondary V-vs-lane0: {row['branch']} "
                f"dmu={row['delta_mu']:+.5f} band={row['band_mu']:.5f}",
                flush=True,
            )
    print(f"[lane {lane}] DONE", flush=True)


if __name__ == "__main__":
    main()
