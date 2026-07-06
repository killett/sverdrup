"""Replay cache for the Stage-A MIOST gate runner (relaunch-after-OOM recovery).

The cache lets a relaunched gate run replay already-measured trials (params ->
scores) parsed from the previous run's log + persisted results JSON, instead of
re-solving ~20 min/trial. Deterministic seeds mean the relaunch re-proposes the
identical points, so a hit is a faithful reproduction, not a shortcut.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stage_miost_gate_run.py"


@pytest.fixture(scope="module")
def gate_mod() -> Any:
    """Import the gate-runner script as a module (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location("stage_miost_gate_run", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["stage_miost_gate_run"] = mod
    spec.loader.exec_module(mod)
    yield mod
    # The script monkeypatches ValidationTrackScorer.score at import; restore.
    from sverdrup.application.tuning.scorer import ValidationTrackScorer

    ValidationTrackScorer.score = mod._orig_score  # type: ignore[method-assign]
    del sys.modules["stage_miost_gate_run"]


# Full-precision params exactly as the heartbeat log prints them (repr floats).
_P27 = {
    "spacing_alpha": 0.5100559420617307,
    "log10_rho": 1.561216598643947,
    "q_slope": 0.04066345738704445,
    "l_t_days": 6.625471885167879,
}
_P22 = {
    "spacing_alpha": 0.917304802367127,
    "log10_rho": 0.7934491422287584,
    "q_slope": 0.5615477543809351,
    "l_t_days": 6.386710423594152,
}

_LOG_TEXT = f"""[+00:00:03]   trial 1: {{'spacing_alpha': 1.0, 'log10_rho': 0.5, 'q_slope': 2.0, 'l_t_days': 8.5}} -> solving 365 day-maps ...
miost window w+00297.0+60: PCG residual 4.41e-04 after 500 iters (rtol 1e-06)
[+00:09:17]   trial 1: {{'mu_score': 0.781708395178266}} (554s)
[+00:09:17]   trial 2: {{'spacing_alpha': 0.917304802367127, 'log10_rho': 0.7934491422287584, 'q_slope': 0.5615477543809351, 'l_t_days': 6.386710423594152}} -> solving 365 day-maps ...
[+00:32:36]   trial 2: {{'mu_score': 0.8251056934606774, 'lambda_x': 204.83309985099908}} (1398s)
[+00:32:36]   trial 3: {_P27!r} -> solving 365 day-maps ...
"""


def test_log_pairing_extracts_completed_trials(gate_mod: Any, tmp_path: Path) -> None:
    """Start/score lines pair per trial number; a dangling start is excluded.

    Catches: mispairing (trial 3's params served trial 2's scores) and crashes
    on the never-scored final trial of an OOM-killed log.
    """
    log = tmp_path / "gate.log"
    log.write_text(_LOG_TEXT)
    cache = gate_mod._replay_from_log(log)
    assert len(cache) == 2
    k1 = gate_mod._replay_key(
        {"spacing_alpha": 1.0, "log10_rho": 0.5, "q_slope": 2.0, "l_t_days": 8.5}
    )
    k2 = gate_mod._replay_key(_P22)
    assert cache[k1] == {"mu_score": 0.781708395178266}
    assert cache[k2] == {"mu_score": 0.8251056934606774, "lambda_x": 204.83309985099908}
    # The dangling trial (params printed, killed before scoring) must be absent.
    assert gate_mod._replay_key(_P27) not in cache


def test_results_json_history_merges_and_skips_unscored(
    gate_mod: Any, tmp_path: Path
) -> None:
    """History rows with scores merge into the cache; score-less rows skipped.

    Catches: crash on exclusion rows (scores None) and duplicate params
    producing conflicting entries.
    """
    results = {
        "sobol": {
            "history": [
                {"params": _P22, "feasible": True, "scores": {"mu_score": 0.83}},
                {
                    "params": {"spacing_alpha": 0.4, "log10_rho": 0.0},
                    "feasible": False,
                    "exclusion_reason": "stored-G over budget",
                    "scores": None,
                },
            ]
        }
    }
    path = tmp_path / "results.json"
    path.write_text(json.dumps(results))
    log = tmp_path / "gate.log"
    log.write_text(_LOG_TEXT)  # trial 2 duplicates the _P22 history row
    cache = gate_mod._build_replay_cache(log, path)
    # Duplicate collapses to ONE entry; log wins or JSON wins is irrelevant as
    # both carry the same measurement — but it must be one of the two exactly.
    assert cache[gate_mod._replay_key(_P22)]["mu_score"] in (
        0.83,
        0.8251056934606774,
    )
    keys = set(cache)
    assert gate_mod._replay_key({"spacing_alpha": 0.4, "log10_rho": 0.0}) not in keys
    assert len(cache) == 2  # trial-1 params + _P22


def test_replay_key_exact_under_log_roundtrip(gate_mod: Any) -> None:
    """key(p) == key(literal_eval(repr(p))); nearby params get distinct keys.

    Catches: lossy str-formatting in the key — log-parsed keys would never
    match live BO proposals and the cache would silently no-op.
    """
    import ast

    roundtrip = ast.literal_eval(repr(_P27))
    assert gate_mod._replay_key(_P27) == gate_mod._replay_key(roundtrip)
    nearby = dict(_P27, spacing_alpha=0.513)
    assert gate_mod._replay_key(nearby) != gate_mod._replay_key(_P27)
    # Key must not depend on dict insertion order.
    reordered = dict(reversed(list(_P27.items())))
    assert gate_mod._replay_key(reordered) == gate_mod._replay_key(_P27)


class _Scorer:
    """Stand-in with the attributes _counting_score touches."""

    output_days = list(range(3))


def test_replay_hit_skips_solve(gate_mod: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cached params return the cached scores without invoking the real scorer.

    Catches: lookup wired after the solve, or key mismatch between build and
    lookup — either way the expensive re-solve silently returns.
    """

    def _boom(*a: Any, **k: Any) -> None:
        raise AssertionError("real scorer invoked on a cache hit")

    monkeypatch.setattr(gate_mod, "_orig_score", _boom)
    monkeypatch.setattr(
        gate_mod,
        "REPLAY_CACHE",
        {gate_mod._replay_key(_P22): {"mu_score": 0.8251056934606774}},
    )
    out = gate_mod._counting_score(_Scorer(), "miost", dict(_P22), None, 1, None)
    assert out == {"mu_score": 0.8251056934606774}


def test_replay_miss_falls_through(
    gate_mod: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un-cached params reach the real scorer.

    Catches: an overly-broad key (e.g. dropping a param) serving a stale µ to
    a genuinely new proposal.
    """
    sentinel = {"mu_score": 0.111}
    monkeypatch.setattr(gate_mod, "_orig_score", lambda *a, **k: sentinel)
    monkeypatch.setattr(
        gate_mod,
        "REPLAY_CACHE",
        {gate_mod._replay_key(_P22): {"mu_score": 0.999}},
    )
    out = gate_mod._counting_score(_Scorer(), "miost", dict(_P27), None, 1, None)
    assert out == sentinel


def test_replay_disabled_by_env(gate_mod: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """SVERDRUP_MIOST_REPLAY=0 forces the real solve even on a cache hit.

    Catches: kill-switch unwired — the owner could not force an honest full
    re-solve of the gate.
    """
    sentinel = {"mu_score": 0.222}
    monkeypatch.setattr(gate_mod, "_orig_score", lambda *a, **k: sentinel)
    monkeypatch.setattr(
        gate_mod,
        "REPLAY_CACHE",
        {gate_mod._replay_key(_P22): {"mu_score": 0.999}},
    )
    monkeypatch.setenv("SVERDRUP_MIOST_REPLAY", "0")
    out = gate_mod._counting_score(_Scorer(), "miost", dict(_P22), None, 1, None)
    assert out == sentinel
