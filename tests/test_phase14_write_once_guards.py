"""Hygiene item 44 (part 2): phase-14 runners refuse to replace their record.

Each runner REPLACED its node on a rerun with no guard:

- settling ``run`` (records by default) rebuilt the node wholesale and so
  destroyed the owner-added ``pin_53_m_requirement`` / ``pin_54_condition``
  blocks that no code produces;
- golden-tile ``run`` (always records) destroyed the hand-added
  ``mu_scale_check`` the anchor gate's check 2 cites;
- floor-factor ``derive`` (records by default) re-created a node the
  ``rubric_v2_amendment_withdrawn`` ruling REMOVED, carrying the
  "cannot fail" ±4-sd test;
- sigma-diagnosis ``run`` (records by default) rewrote the node the σ
  withholding cites.

Each guard must fire BEFORE any work (a stubbed first-work call fails the
test if reached) and leave the store's bytes unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sverdrup.validation.write_once import NodeAlreadyRecordedError
from tests.helpers import load_script


class _WorkBegan(AssertionError):
    """A stubbed first-work call ran — the guard did not fire first."""


def _stub_work(*_a: object, **_k: object) -> Any:  # noqa: ANN401
    raise _WorkBegan("work began before the write-once refusal")


def _store(tmp_path: Path, stage: str, node: str) -> Path:
    path = tmp_path / "store.json"
    path.write_text(json.dumps({"phase14": {stage: {node: {"recorded": 1}}}}))
    return path


# ---- settling measurement --------------------------------------------------


def test_settling_rerun_refuses_over_its_recorded_node(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught: the default run replacing the node and its pin-53/54 blocks."""
    mod = load_script("phase14_settling_measurement")
    store = _store(tmp_path, "stage1", "ensemble_settling_measurement")
    before = store.read_bytes()
    monkeypatch.setattr(mod, "_stage1_module", _stub_work)
    with pytest.raises(NodeAlreadyRecordedError, match="ensemble_settling"):
        mod.run(evidence_path=store)
    assert store.read_bytes() == before


def test_settling_no_record_and_first_runs_pass_the_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught: a guard that also blocks ``--no-record`` (which writes
    nothing) or a first run over a store without the node."""
    mod = load_script("phase14_settling_measurement")
    monkeypatch.setattr(mod, "_stage1_module", _stub_work)
    recorded = _store(tmp_path, "stage1", "ensemble_settling_measurement")
    with pytest.raises(_WorkBegan):
        mod.run(evidence_path=recorded, record=False)
    fresh = tmp_path / "fresh.json"
    fresh.write_text(json.dumps({"phase14": {"stage1": {}}}))
    with pytest.raises(_WorkBegan):
        mod.run(evidence_path=fresh)


# ---- golden tile -----------------------------------------------------------


def test_golden_tile_rerun_refuses_over_its_recorded_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught: the always-recording run replacing the row and with it
    the hand-added ``mu_scale_check``."""
    mod = load_script("phase14_golden_tile")
    store = tmp_path / "store.json"
    store.write_text(
        json.dumps(
            {"phase14": {"stage0": {"golden_tile": {"dc2021a_vs_cmems_my": {"x": 1}}}}}
        )
    )
    before = store.read_bytes()
    monkeypatch.setattr(mod, "EVIDENCE", store)
    monkeypatch.setattr(mod, "_load_side", _stub_work)
    with pytest.raises(NodeAlreadyRecordedError, match="dc2021a_vs_cmems_my"):
        mod.run()
    assert store.read_bytes() == before


def test_golden_tile_other_pair_passes_the_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught: guarding the whole ``golden_tile`` node instead of the
    one comparison — a different source pair is a new record."""
    mod = load_script("phase14_golden_tile")
    store = tmp_path / "store.json"
    store.write_text(
        json.dumps({"phase14": {"stage0": {"golden_tile": {"a_vs_b": {"x": 1}}}}})
    )
    monkeypatch.setattr(mod, "EVIDENCE", store)
    monkeypatch.setattr(mod, "_load_side", _stub_work)
    with pytest.raises(_WorkBegan):
        mod.run()


# ---- ensemble floor factor -------------------------------------------------


@pytest.mark.parametrize(
    "node", ["ensemble_floor_factor_derivation", "rubric_v2_amendment_withdrawn"]
)
def test_floor_factor_refuses_to_recreate_or_replace(node: str, tmp_path: Path) -> None:
    """Bug caught: ``derive`` re-creating the node the withdrawal ruling
    REMOVED (or replacing it while it still stands)."""
    mod = load_script("phase14_ensemble_floor_factor")
    store = _store(tmp_path, "stage1", node)
    before = store.read_bytes()
    with pytest.raises(NodeAlreadyRecordedError, match=node):
        mod.derive(evidence_path=store)
    assert store.read_bytes() == before


def test_floor_factor_no_record_passes_the_guard(tmp_path: Path) -> None:
    """Bug caught: a guard that blocks the print-only ``--no-record`` run.

    Past the guard, a store with no seam_pair fails on that missing key —
    the signal that the work began.
    """
    mod = load_script("phase14_ensemble_floor_factor")
    store = _store(tmp_path, "stage1", "rubric_v2_amendment_withdrawn")
    with pytest.raises(KeyError, match="seam_pair"):
        mod.derive(evidence_path=store, record=False)


# ---- sigma diagnosis -------------------------------------------------------


def test_sigma_diagnosis_rerun_refuses_over_its_recorded_node(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught: the default run rewriting the node the σ withholding cites."""
    mod = load_script("phase14_sigma_diagnosis")
    store = _store(tmp_path, "stage1", "seam_sigma_diagnosis")
    before = store.read_bytes()
    monkeypatch.setattr(mod, "EVIDENCE", store)
    monkeypatch.setattr(mod, "_stage1_module", _stub_work)
    with pytest.raises(NodeAlreadyRecordedError, match="seam_sigma_diagnosis"):
        mod.run()
    assert store.read_bytes() == before


def test_sigma_diagnosis_no_record_passes_the_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug caught: a guard that blocks the print-only ``--no-record`` run."""
    mod = load_script("phase14_sigma_diagnosis")
    monkeypatch.setattr(
        mod, "EVIDENCE", _store(tmp_path, "stage1", "seam_sigma_diagnosis")
    )
    monkeypatch.setattr(mod, "_stage1_module", _stub_work)
    with pytest.raises(_WorkBegan):
        mod.run(record=False)
