"""Cross-env gate machinery tests (phase-14 Task 17, 0b-4) — CI-local.

The tiny synthetic window exercises the same production randomness layer
(``miost_crn._keyed_uniform``) the pinned subject uses; the real pinned
subject runs at Task 18 (Tier-2) and in the same-host legs.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from tests.helpers import load_script

_mod = load_script("phase14_crossenv")
runner = CliRunner()


def _crn(tmp_path: Path, name: str) -> Path:
    out = tmp_path / name
    res = runner.invoke(_mod.app, ["crn", "--out", str(out), "--synthetic"])
    assert res.exit_code == 0, res.output
    return out


def test_same_host_smoke_two_runs_equal(tmp_path: Path) -> None:
    """Two synthetic --leg crn runs -> compare-crn EQUAL (the smoke AC)."""
    a = _crn(tmp_path, "a.json")
    b = _crn(tmp_path, "b.json")
    res = runner.invoke(_mod.app, ["compare-crn", str(a), str(b)])
    assert res.exit_code == 0
    assert "EQUAL" in res.output


def test_manifest_determinism_and_content(tmp_path: Path) -> None:
    """The manifest carries per-axis shas, root, recipe, versions."""
    m = json.loads(_crn(tmp_path, "a.json").read_text())
    assert set(m["axes"]) == {"obs", "coef"}
    for axis in m["axes"].values():
        assert len(axis["sha256"]) == 64
        assert axis["n"] > 0
    assert m["env_recipe"] == {
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "PYTHONHASHSEED": "0",
    }
    assert "numpy" in m["versions"]


def test_compare_crn_mismatch_exits_nonzero(tmp_path: Path) -> None:
    """A flipped sha is a loud MISMATCH exit — never a soft report."""
    a = _crn(tmp_path, "a.json")
    m = json.loads(a.read_text())
    m["axes"]["obs"]["sha256"] = "0" * 64
    b = tmp_path / "b.json"
    b.write_text(json.dumps(m))
    res = runner.invoke(_mod.app, ["compare-crn", str(a), str(b)])
    assert res.exit_code == 1
    assert "MISMATCH" in res.output


def test_stream_sensitive_to_root_and_member() -> None:
    """Different root or member -> different stream bytes (keying works)."""
    ident = _mod._synthetic_identities()["obs"]
    base = _mod._uniform_stream("obs", ident, 12345, 0)
    assert not np.array_equal(base, _mod._uniform_stream("obs", ident, 12346, 0))
    assert not np.array_equal(base, _mod._uniform_stream("obs", ident, 12345, 1))
    # and identical inputs reproduce bit-exactly
    np.testing.assert_array_equal(base, _mod._uniform_stream("obs", ident, 12345, 0))


def test_compare_solve_reports_deltas(tmp_path: Path) -> None:
    """compare-solve REPORTS max-abs/RMS (hand values), asserts nothing."""
    a = tmp_path / "a.npz"
    b = tmp_path / "b.npz"
    mean_a = np.zeros((1, 2, 2))
    mean_b = np.full((1, 2, 2), 3e-7)
    np.savez(a, mean=mean_a, member_std=np.ones((1, 2, 2)))
    np.savez(b, mean=mean_b, member_std=np.ones((1, 2, 2)))
    res = runner.invoke(_mod.app, ["compare-solve", str(a), str(b)])
    assert res.exit_code == 0
    report = json.loads(res.output)
    assert report["mean"]["max_abs"] == pytest.approx(3e-7)
    assert report["mean"]["rms"] == pytest.approx(3e-7)
    assert report["member_std"]["max_abs"] == 0.0


def test_print_env_recipe() -> None:
    """print-env exports the four pinned vars."""
    res = runner.invoke(_mod.app, ["print-env"])
    assert res.exit_code == 0
    for var in (
        "OPENBLAS_NUM_THREADS=1",
        "OMP_NUM_THREADS=1",
        "MKL_NUM_THREADS=1",
        "PYTHONHASHSEED=0",
    ):
        assert var in res.output
