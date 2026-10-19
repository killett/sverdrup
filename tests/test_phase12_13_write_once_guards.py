"""Hygiene item 44 (part 3): closed phase-12/13 runners refuse to replace.

Each entry point REPLACED its node on a rerun with no guard:

- ``phase13_prereg`` re-dated and re-hashed the SEALED band protocol and
  repointed ``phase13.band_protocol`` — the pre-registration timestamp the
  verdict's recorded ``protocol_sha`` rests on;
- ``phase13_lane_run --winner-ensemble`` replaced ``phase13.miost.members``
  (dropping its ``variance_consistency_row``) and rewrote the c2-touched
  substrate; ``--winner-ctap`` replaced ``phase13.miost.ctap.<lane>``;
- ``phase12_miost6_run --smoke`` replaced ``phase12.miost6.budget`` with the
  owner's T7 launch adjudication in it; ``--run`` rewrote maps, member store
  and provenance after the c2 acceptance had scored them;
- ``phase13_c2_touch --record-provenance`` rewrote the provenance block the
  acceptance was verified against.

Each guard fires BEFORE any work and leaves the store's bytes unchanged; a
store without the node gets past it (the stubbed first work fires).
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


def _nested(dotted: str) -> dict[str, Any]:
    out: dict[str, Any] = {"recorded": 1}
    for part in reversed(dotted.split(".")):
        out = {part: out}
    return out


# (script, store attribute, first-work function, entry call, node)
_CASES = [
    (
        "phase13_prereg",
        "_RESULTS",
        "_load_probe_module",
        lambda m: m.main(),
        "phase13.band_protocol",
    ),
    (
        "phase13_lane_run",
        "_RESULTS",
        "_read_evidence",
        lambda m: m.main_winner_ensemble(),
        "phase13.miost.members",
    ),
    (
        "phase13_lane_run",
        "_RESULTS",
        "_read_evidence",
        lambda m: m.main_winner_ctap("V"),
        "phase13.miost.ctap.V",
    ),
    (
        "phase12_miost6_run",
        "RESULTS",
        "load_phase12_scope",
        lambda m: m.smoke_main(Path("scope.json")),
        "phase12.miost6.budget",
    ),
    (
        "phase12_miost6_run",
        "RESULTS",
        "load_phase12_scope",
        lambda m: m.run_main(Path("scope.json"), Path("signed.json")),
        "phase12.miost6.provenance",
    ),
    (
        "phase12_miost6_run",
        "RESULTS",
        "load_phase12_scope",
        lambda m: m.run_main(Path("scope.json"), Path("signed.json")),
        "phase12.miost6.c2_acceptance",
    ),
    (
        "phase13_c2_touch",
        "_RESULTS",
        "_refit_cal",
        lambda m: m.record_provenance(),
        "phase13.miost.provenance",
    ),
]


@pytest.mark.parametrize(("script", "store_attr", "work", "call", "node"), _CASES)
def test_rerun_over_a_recorded_node_refuses_before_any_work(
    script: str,
    store_attr: str,
    work: str,
    call: Any,  # noqa: ANN401
    node: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bug caught (hygiene 44): the rerun replacing a closed phase's record."""
    mod = load_script(script)
    store = tmp_path / "store.json"
    store.write_text(json.dumps(_nested(node)))
    before = store.read_bytes()
    monkeypatch.setattr(mod, store_attr, store)
    monkeypatch.setattr(mod, work, _stub_work)
    with pytest.raises(NodeAlreadyRecordedError, match=node):
        call(mod)
    assert store.read_bytes() == before


@pytest.mark.parametrize(
    ("script", "store_attr", "work", "call", "node"),
    # one control per distinct guard (the c2_acceptance row shares run_main's)
    [c for c in _CASES if c[4] != "phase12.miost6.c2_acceptance"],
)
def test_a_store_without_the_node_gets_past_the_guard(
    script: str,
    store_attr: str,
    work: str,
    call: Any,  # noqa: ANN401
    node: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bug caught: a guard on the wrong path (a parent, a sibling) that
    would refuse a first run — e.g. guarding ``phase13.lane0_reference``,
    which the prereg's documented "rerun heals" relies on rewriting."""
    mod = load_script(script)
    store = tmp_path / "store.json"
    parent = node.rsplit(".", 1)[0]
    store.write_text(json.dumps(_nested(f"{parent}.some_sibling")))
    monkeypatch.setattr(mod, store_attr, store)
    monkeypatch.setattr(mod, work, _stub_work)
    with pytest.raises(_WorkBegan):
        call(mod)
