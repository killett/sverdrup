"""Seal-runner tests (T19 review finding 4: mechanical re-derivability)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.helpers import load_script

_mod = load_script("phase14_seal_run")
runner = CliRunner()

_EPOCH_TABLE = [
    {
        "epoch_id": "e00_1995-01-01",
        "locked_instruments": ["gauges"],
    },
    {
        "epoch_id": "e05_2009-02-10",
        "locked_instruments": ["gauges", "c2"],
    },
    {
        "epoch_id": "e12_2020-08-01",
        "locked_instruments": ["gauges", "c2n"],
    },
]


def _fixtures(tmp_path: Path) -> dict[str, Path]:
    et = tmp_path / "epoch_table_draft.json"
    et.write_text(json.dumps(_EPOCH_TABLE))
    ls = tmp_path / "locked_split.json"
    ls.write_text(json.dumps({"locked": ["uh002", "uh001"], "dev": ["uh003"]}))
    return {
        "epoch_table": et,
        "locked_split": ls,
        "seal": tmp_path / "seal_v1.json",
        "evidence": tmp_path / "evidence.json",
    }


def _args(p: dict[str, Path], cmd: str) -> list[str]:
    return [
        cmd,
        "--epoch-table",
        str(p["epoch_table"]),
        "--locked-split",
        str(p["locked_split"]),
        "--seal-path",
        str(p["seal"]),
        "--evidence-path",
        str(p["evidence"]),
    ]


def test_build_then_check_roundtrip(tmp_path: Path) -> None:
    """build writes the seal + evidence pointer; check re-derives the sha.

    Bug caught: an assembly recipe that exists only as session prose — a
    changed input (epoch table bytes, split ids, config constants) would
    make the recorded sha unreproducible with nothing to run.
    """
    p = _fixtures(tmp_path)
    p["evidence"].write_text(json.dumps({"phase14": {"stage0": {}}}))
    res = runner.invoke(_mod.app, _args(p, "build"))
    assert res.exit_code == 0, res.output
    seal = json.loads(p["seal"].read_text())
    ev = json.loads(p["evidence"].read_text())
    node = ev["phase14"]["stage0"]["seal"]
    assert node["sha"] == seal["seal_sha"]
    assert node["path"] == str(p["seal"])
    # c2 windows derived from the table: c2 OR c2n rows, e00 excluded
    assert seal["content"]["c2_era_windows"] == [
        "e05_2009-02-10",
        "e12_2020-08-01",
    ]
    assert seal["content"]["locked_gauges"] == ["uh001", "uh002"]
    res2 = runner.invoke(_mod.app, _args(p, "check"))
    assert res2.exit_code == 0, res2.output
    assert "PASS" in res2.output


def test_check_fails_on_drifted_input(tmp_path: Path) -> None:
    """A changed input after sealing makes check FAIL, not silently pass.

    Bug caught: check comparing the seal file only against itself (always
    green) instead of re-assembling from the live artifacts.
    """
    p = _fixtures(tmp_path)
    p["evidence"].write_text(json.dumps({"phase14": {"stage0": {}}}))
    assert runner.invoke(_mod.app, _args(p, "build")).exit_code == 0
    drift = json.loads(p["locked_split"].read_text())
    drift["locked"].append("uh999")
    p["locked_split"].write_text(json.dumps(drift))
    res = runner.invoke(_mod.app, _args(p, "check"))
    assert res.exit_code != 0
    assert "FAIL" in res.output


def test_build_refuses_existing_seal(tmp_path: Path) -> None:
    """Second build refuses (write-once) — supersession is the only path."""
    p = _fixtures(tmp_path)
    p["evidence"].write_text(json.dumps({"phase14": {"stage0": {}}}))
    assert runner.invoke(_mod.app, _args(p, "build")).exit_code == 0
    res = runner.invoke(_mod.app, _args(p, "build"))
    assert res.exit_code != 0


# ---- supersession: the sanctioned amendment path (fork-f pin 2) -----------
# Exercised for real by the rubric v2 amendment (owner ruling 2026-07-27,
# pins 32 + 34), which changes the SEALED instrument configs.

_SIGNOFF = (
    "owner ruling 2026-07-27 pins 32+34 (rubric v2: ensemble floor + F by "
    "accuracy target) — docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md"
)


def _supersede_args(p: dict[str, Path], signoff: str) -> list[str]:
    return [
        "supersede",
        "--signoff",
        signoff,
        "--epoch-table",
        str(p["epoch_table"]),
        "--locked-split",
        str(p["locked_split"]),
        "--evidence-path",
        str(p["evidence"]),
    ]


def _built(tmp_path: Path) -> dict[str, Path]:
    p = _fixtures(tmp_path)
    p["evidence"].write_text(json.dumps({"phase14": {"stage0": {}}}))
    assert runner.invoke(_mod.app, _args(p, "build")).exit_code == 0
    return p


def _amend_the_sealed_instrument(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand in for the rubric-v2 change to the SEALED instrument configs.

    The amendment's real input is ``instrument_configs()`` — the only
    substantive change a rubric amendment makes to seal content — so the
    test changes exactly that and leaves every other artifact alone.
    """
    monkeypatch.setattr(
        _mod,
        "serialize_instrument_configs",
        lambda: b'{"seam":{"rubric_version":2}}',
    )


def test_supersede_writes_v2_chains_to_v1_and_moves_the_pointer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new version file, a recorded chain, and v1 left byte-untouched.

    Bug caught: an amendment that overwrites the pointer without recording
    what it superseded. Gate 0's evidence quotes seal v1 by sha; if the
    pointer moves with no chain, that quotation becomes unresolvable and
    the founding artifact's history is gone. Also catches an amendment
    that mutates the v1 FILE (the write-once property the whole seal
    design rests on).
    """
    p = _built(tmp_path)
    v1_bytes = p["seal"].read_bytes()
    v1_sha = json.loads(v1_bytes)["seal_sha"]
    _amend_the_sealed_instrument(monkeypatch)

    res = runner.invoke(_mod.app, _supersede_args(p, _SIGNOFF))
    assert res.exit_code == 0, res.output

    v2_path = tmp_path / "seal_v2.json"
    assert v2_path.exists()
    v2 = json.loads(v2_path.read_text())
    assert v2["content"]["supersedes"] == v1_sha
    assert v2["content"]["signoff"] == _SIGNOFF
    assert p["seal"].read_bytes() == v1_bytes  # write-once honoured

    node = json.loads(p["evidence"].read_text())["phase14"]["stage0"]["seal"]
    assert node["version"] == 2
    assert node["sha"] == v2["seal_sha"]
    assert node["path"] == str(v2_path)
    assert node["supersedes"]["version"] == 1
    assert node["supersedes"]["sha"] == v1_sha
    assert node["supersedes"]["path"] == str(p["seal"])


def test_supersede_refuses_without_an_owner_signoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No signoff, no new seal — and no pointer move either.

    Bug caught: an unratified edit to a PRE-REGISTERED instrument slipping
    through as a new sealed version. The rubric's own deviation clause
    requires an explicit owner decision; this is the mechanical enforcement
    of it, and a partial failure (seal written, pointer moved, signoff
    missing) would be worse than either outcome.
    """
    p = _built(tmp_path)
    _amend_the_sealed_instrument(monkeypatch)
    before = p["evidence"].read_bytes()
    res = runner.invoke(_mod.app, _supersede_args(p, "   "))
    assert res.exit_code != 0
    assert not (tmp_path / "seal_v2.json").exists()
    assert p["evidence"].read_bytes() == before


def test_supersede_refuses_when_content_is_unchanged(tmp_path: Path) -> None:
    """A supersession with nothing to amend is refused.

    Bug caught: version inflation — a v2 identical in substance to v1,
    which would make "which version verdicted this row" unanswerable while
    looking like a real amendment.
    """
    p = _built(tmp_path)
    res = runner.invoke(_mod.app, _supersede_args(p, _SIGNOFF))
    assert res.exit_code != 0
    assert "unchanged" in res.output.lower()
    assert not (tmp_path / "seal_v2.json").exists()


def test_check_still_re_derives_after_supersession(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """check PASSES against v2 and still FAILS on live-artifact drift.

    The superseded content carries an envelope (supersedes/signoff/date)
    that no live artifact produces, so check must re-derive the
    substantive fields and admit the envelope — without going blind to
    drift, which is the whole point of `check`.

    Bug caught (both directions): check hard-failing forever after any
    amendment — which would strand T5's verify step and invite someone to
    delete the check — or check being loosened into a self-comparison that
    passes even when the epoch table changed underneath the seal.
    """
    p = _built(tmp_path)
    _amend_the_sealed_instrument(monkeypatch)
    assert runner.invoke(_mod.app, _supersede_args(p, _SIGNOFF)).exit_code == 0

    ok = runner.invoke(_mod.app, _args(p, "check"))
    # the pointer now names v2; check reads the path from the pointer
    assert ok.exit_code == 0, ok.output
    assert "PASS" in ok.output

    drift = json.loads(p["locked_split"].read_text())
    drift["dev"].append("uh999")
    p["locked_split"].write_text(json.dumps(drift))
    bad = runner.invoke(_mod.app, _args(p, "check"))
    assert bad.exit_code != 0
    assert "FAIL" in bad.output


# ---------------------------------------------------------------------------
# Owner pin 152 — the re-keyed pin-42 check REFUSES, with the recorded-as-found
# nine visible but not fatal.
# ---------------------------------------------------------------------------


def test_a_NEW_undeclared_verdict_block_is_a_refusal() -> None:
    """An undeclared gate anywhere fails the check.

    Bug caught: leaving the re-keyed check reporting, which would make it
    a check that cannot fail — inside the pin whose entire subject is
    checks that cannot fail. This is the block a future leg might add.
    """
    store = {"phase14": {"stage1": {"brand_new_thing": {"verdict": "CLEAN"}}}}
    findings = _mod._verdict_findings(store)

    assert findings, "an undeclared verdict block must be caught"
    assert not findings[0].startswith("RECORDED-AS-FOUND ")


def test_the_recorded_as_found_nine_are_VISIBLE_but_not_fatal() -> None:
    """A recorded prior-phase gate is flagged for display, not for failure.

    Bug caught: silently exempting them, which is how a list of known
    exceptions stops being read; and conversely, failing on them, which
    would reopen closed owner-signed work the citation test already
    cleared (pin 145b).
    """
    store = {
        "phase10": {"oi": {"lanes": {"verdict": "PASS"}}},
        "phase14": {
            "stage1": {
                "reachability_declarations": {
                    "declarations": {},
                    "not_declared_uncited_prior_phase": {
                        "blocks": ["phase10.oi.lanes"]
                    },
                }
            }
        },
    }
    findings = _mod._verdict_findings(store)

    assert len(findings) == 1
    assert findings[0].startswith("RECORDED-AS-FOUND ")
    assert "phase10.oi.lanes" in findings[0]
