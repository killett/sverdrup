"""Hygiene item 42: the gate runner can no longer wipe the shared store.

The shared evidence store (``RESULTS``) is single-copy and gitignored, and
it holds phase 8-14 evidence that is not mirrored anywhere else. Before this
guard, ``main()`` — the membership dispatch's ``else`` — built a fresh dict
and wrote it over the store, so no flag, a typo (``--stageb``) or
``--c2-touch=1`` wiped it; and a ``--stage-b`` rerun's first ``_flush``
replaced the SIGNED ``stage_b`` block (erasing ``c2_acceptance`` and so
re-arming ``--c2-touch``) before the inline-touch refusal ran.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from tests.helpers import load_script

gate = load_script("stage_miost_gate_run")

_MODE_FUNCS = (
    "main",
    "stage_b_main",
    "c2_touch_main",
    "regen_acceptance_main",
    "build_replay_cache_main",
)


class _NoWork(AssertionError):
    """Raised by a patched ``_scope`` — any work began before the guard."""


def _record_modes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    for name in _MODE_FUNCS:
        monkeypatch.setattr(gate, name, lambda n=name: calls.append(n))
    return calls


def _forbid_work(monkeypatch: pytest.MonkeyPatch) -> None:
    def _scope() -> Path:
        raise _NoWork("work began before the refusal")

    monkeypatch.setattr(gate, "_scope", _scope)


def _store(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "stage_miost_gate_results.json"
    path.write_text(json.dumps(payload, indent=2))
    return path


_SIGNED_STAGE_B: dict[str, Any] = {
    "winner": {"params": {"c0": 0.1}},
    "phase14": {"stage1": {"kept": True}},
    "stage_b": {
        "status": "SIGNED OFF per owner pre-registered reading (2026-07-07)",
        "c2_acceptance": {"semantics": "the one spent touch"},
    },
}


@pytest.mark.parametrize(
    "argv",
    [
        ["--stageb"],
        ["--c2-touch=1"],
        ["stage-b"],
        ["--stage-b", "--c2-touch"],
        ["--stage-b", "--extra"],
    ],
)
def test_unrecognised_argv_refuses_and_runs_no_mode(
    monkeypatch: pytest.MonkeyPatch, argv: list[str]
) -> None:
    """Bug caught: the old ``"--x" in sys.argv`` chain sent a typo to main()
    (a store wipe) and let a two-flag argv silently pick one mode."""
    calls = _record_modes(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        gate.dispatch(argv)
    assert calls == []
    assert str(exc.value).startswith("REFUSED")
    assert repr(argv) in str(exc.value)


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        ([], "main"),
        (["--stage-b"], "stage_b_main"),
        (["--c2-touch"], "c2_touch_main"),
        (["--regen-acceptance"], "regen_acceptance_main"),
        (["--build-replay-cache"], "build_replay_cache_main"),
    ],
)
def test_each_recognised_argv_runs_exactly_its_mode(
    monkeypatch: pytest.MonkeyPatch, argv: list[str], expected: str
) -> None:
    """Bug caught: crossed wiring in the rewritten dispatch."""
    calls = _record_modes(monkeypatch)
    gate.dispatch(argv)
    assert calls == [expected]


def test_main_refuses_over_an_existing_store_before_any_work(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Bug caught: main() writing a fresh dict over the whole shared store."""
    store = _store(tmp_path, _SIGNED_STAGE_B)
    before = store.read_bytes()
    monkeypatch.setattr(gate, "RESULTS", store)
    _forbid_work(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        gate.main()
    assert str(store) in str(exc.value)
    assert store.read_bytes() == before


def test_main_proceeds_on_a_fresh_box(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Bug caught: a guard that refuses unconditionally (main unusable)."""
    monkeypatch.setattr(gate, "RESULTS", tmp_path / "absent.json")
    monkeypatch.setattr(gate, "OUT_DIR", tmp_path)
    _forbid_work(monkeypatch)
    with pytest.raises(_NoWork):
        gate.main()


@pytest.mark.parametrize(
    ("stage_b", "refused"),
    [
        (None, False),
        ({"status": "RUNNING: member generation"}, False),
        ({"status": "STOPPED: coverage bar failed"}, False),
        ({"status": "READY: evidence assembled; c2 NOT touched"}, True),
        ({"status": "SIGNED OFF per owner reading"}, True),
        ({"status": "something new"}, True),
        ({}, True),
        ({"status": "RUNNING: day fields", "c2_acceptance": {}}, True),
        ({"status": "STOPPED: x", "c2_acceptance": {"a": 1}}, True),
    ],
)
def test_completed_stage_b_guard_boundaries(
    tmp_path: Path, stage_b: dict[str, Any] | None, refused: bool
) -> None:
    """Bugs caught: a guard too narrow (misses a SIGNED block, or a spent
    touch under a non-final status) or too broad (blocks rerunning a
    STOPPED/RUNNING block, which is how a failed stage-b was retried)."""
    payload: dict[str, Any] = {"winner": {"params": {}}}
    if stage_b is not None:
        payload["stage_b"] = stage_b
    store = _store(tmp_path, payload)
    if refused:
        with pytest.raises(SystemExit) as exc:
            gate.refuse_completed_stage_b(store)
        assert "stage_b" in str(exc.value)
    else:
        gate.refuse_completed_stage_b(store)


def test_completed_stage_b_guard_allows_an_absent_store(tmp_path: Path) -> None:
    """Bug caught: a guard that crashes instead of allowing a fresh box."""
    gate.refuse_completed_stage_b(tmp_path / "absent.json")


def test_stage_b_refuses_over_a_signed_block_before_any_work(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Bug caught: the first _flush replacing the signed stage_b block."""
    store = _store(tmp_path, _SIGNED_STAGE_B)
    before = store.read_bytes()
    monkeypatch.setattr(gate, "RESULTS", store)
    monkeypatch.setattr(gate, "SCOPE_MODE", "full")
    monkeypatch.delenv("SVERDRUP_MIOST_C2", raising=False)
    _forbid_work(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        gate.stage_b_main()
    assert "stage_b" in str(exc.value)
    assert store.read_bytes() == before


def test_stage_b_env_flag_refuses_before_any_work(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Bug caught: the disarmed inline touch refusing only after hours of work."""
    monkeypatch.setattr(gate, "RESULTS", _store(tmp_path, {"winner": {}}))
    monkeypatch.setattr(gate, "SCOPE_MODE", "full")
    monkeypatch.setenv("SVERDRUP_MIOST_C2", "1")
    _forbid_work(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        gate.stage_b_main()
    assert str(exc.value) == gate.INLINE_TOUCH_DISARMED


def test_dev_scope_is_not_blocked_by_the_signed_block(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Bug caught: the guard blocking a dev smoke, which never writes RESULTS."""
    monkeypatch.setattr(gate, "RESULTS", _store(tmp_path, _SIGNED_STAGE_B))
    monkeypatch.setattr(gate, "SCOPE_MODE", "dev")
    monkeypatch.delenv("SVERDRUP_MIOST_C2", raising=False)
    _forbid_work(monkeypatch)
    with pytest.raises(_NoWork):
        gate.stage_b_main()


_CANONICAL_MAPS = ("stage_b_mean_maps.nc", "stage_b_var_maps.nc")
_DEV_MAPS = ("stage_b_dev_smoke_mean_maps.nc", "stage_b_dev_smoke_var_maps.nc")


class _MapsWritten(Exception):
    """Raised by the patched track interp: the run got past the map writes."""


def _run_stage_b_to_the_maps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scope_mode: str
) -> list[tuple[Path, Path]]:
    """Run ``stage_b_main`` against ``tmp_path`` up to its first map read.

    Only the compute is stubbed (obs load, member generation, field
    assembly, track interp); ``write_map`` is the real writer.

    Returns:
        The ``(mean_nc, var_nc)`` pairs the run handed to the track interp.
    """
    import sverdrup.distributions.miost_ensemble as ens
    from sverdrup.core.observations import DiagonalErrorModel, ObsWindow

    scope = tmp_path / "scope.json"
    scope.write_text(
        json.dumps(
            {
                "validation_mission": "j3",
                "validation_days": [60, 61],
                "val_track_path": str(tmp_path / "unused_track.nc"),
            }
        )
    )
    n = 8
    obs = ObsWindow.from_arrays(
        np.linspace(296.0, 304.0, n),
        np.linspace(34.0, 42.0, n),
        np.linspace(60.0, 61.0, n),
        np.zeros(n),
        DiagonalErrorModel(np.full(n, 0.01)),
        np.asarray(["alg", "j3"] * (n // 2)),
    )
    _, grid, _ = gate.baseline_config()
    read: list[tuple[Path, Path]] = []

    def _interp(mean_nc: Path, var_nc: Path, *_: object) -> None:
        read.append((mean_nc, var_nc))
        raise _MapsWritten

    monkeypatch.setattr(gate, "OUT_DIR", tmp_path)
    monkeypatch.setattr(gate, "RESULTS", _store(tmp_path, {"winner": {"params": {}}}))
    monkeypatch.setattr(gate, "SCOPE_MODE", scope_mode)
    monkeypatch.delenv("SVERDRUP_MIOST_C2", raising=False)
    monkeypatch.setattr(gate, "_scope", lambda: scope)
    monkeypatch.setattr(gate, "_halo_obs", lambda _scope: obs)
    monkeypatch.setattr(
        gate,
        "_escalated_members",
        lambda *_a: {
            "member_batches": [],
            "maxiter_used": 1,
            "converged": True,
            **dict.fromkeys(("spec", "etas_a", "anoms", "starts")),
        },
    )
    monkeypatch.setattr(
        ens, "mean_fields", lambda *_a: np.zeros((2, grid.y.size * grid.x.size))
    )
    monkeypatch.setattr(
        ens, "std_fields", lambda *_a: np.ones((2, grid.y.size * grid.x.size))
    )
    monkeypatch.setattr(gate, "_interp_mean_var_on_track", _interp)
    with pytest.raises(_MapsWritten):
        gate.stage_b_main()
    return read


def test_dev_smoke_never_writes_the_canonical_stage_b_maps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A dev smoke writes its maps under dev names and scores s* from them.

    The canonical maps are signed full-year evidence: ``--c2-touch`` scores
    them, and the harness defaults and the phase-8/11/12 runners read them.
    Bug caught: the dev smoke routed its JSON away from the store but wrote
    its 12-day maps over the canonical files (hygiene P0-2 residual).
    """
    for name in _CANONICAL_MAPS:
        (tmp_path / name).write_bytes(b"SIGNED " + name.encode())
    read = _run_stage_b_to_the_maps(monkeypatch, tmp_path, "dev")
    for name in _CANONICAL_MAPS:
        assert (tmp_path / name).read_bytes() == b"SIGNED " + name.encode(), name
    assert sorted(p.name for p in tmp_path.glob("*.nc")) == sorted(
        _CANONICAL_MAPS + _DEV_MAPS
    )
    assert read == [(tmp_path / _DEV_MAPS[0], tmp_path / _DEV_MAPS[1])]


def test_full_scope_stage_b_writes_and_reads_the_canonical_maps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Bug caught: a fix that renamed the maps in BOTH scopes, leaving
    ``--c2-touch`` to score whatever stale canonical files were on disk."""
    read = _run_stage_b_to_the_maps(monkeypatch, tmp_path, "full")
    assert sorted(p.name for p in tmp_path.glob("*.nc")) == sorted(_CANONICAL_MAPS)
    assert read == [(tmp_path / _CANONICAL_MAPS[0], tmp_path / _CANONICAL_MAPS[1])]
