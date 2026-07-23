"""Seal-runner tests (T19 review finding 4: mechanical re-derivability)."""

from __future__ import annotations

import json
from pathlib import Path

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
