"""A full-scope ``generate_oi_maps`` run never rewrites the signed OI maps.

``oi_{mean,var}_maps.nc`` are the Phase-9 OI evidence: the calibration
harness reads them by default and the phase-11 retro recorded their sha.
A plain rerun (full scope is the default) regenerated them in place —
non-atomically, so a crash mid-year left them truncated, and even a clean
rerun's fresh bytes broke the recorded sha.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.helpers import load_script


class _NoWork(AssertionError):
    """Raised by a patched ``baseline_config`` — work began."""


def _arm(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scope: str
) -> tuple[Any, Path, Path]:
    mod = load_script("generate_oi_maps")
    mean, var = tmp_path / "oi_mean_maps.nc", tmp_path / "oi_var_maps.nc"
    monkeypatch.setattr(mod, "_AUDIT_MODE", None)
    monkeypatch.setattr(mod, "_SCOPE", scope)
    monkeypatch.setattr(mod, "_MEAN_DEST", mean)
    monkeypatch.setattr(mod, "_VAR_DEST", var)

    def _work() -> None:
        raise _NoWork("work began")

    monkeypatch.setattr(mod, "baseline_config", _work)
    return mod, mean, var


@pytest.mark.parametrize("existing", ["mean", "var"])
def test_full_scope_refuses_over_an_existing_signed_map(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, existing: str
) -> None:
    """Bug caught: the default-scope rerun regenerating the signed maps in
    place; checking only the mean map (a var-only survivor is overwritten)."""
    mod, mean, var = _arm(monkeypatch, tmp_path, "full")
    signed = mean if existing == "mean" else var
    signed.write_bytes(b"SIGNED")
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert str(signed) in str(exc.value)
    assert signed.read_bytes() == b"SIGNED"


def test_full_scope_proceeds_on_a_fresh_box(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Bug caught: a guard that refuses unconditionally."""
    mod, _, _ = _arm(monkeypatch, tmp_path, "full")
    with pytest.raises(_NoWork):
        mod.main()


def test_dev_scope_reruns_over_its_own_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Bug caught: the guard blocking the dev smoke, whose ``*_dev`` maps
    nothing reads."""
    mod, mean, var = _arm(monkeypatch, tmp_path, "dev")
    mean.write_bytes(b"DEV")
    var.write_bytes(b"DEV")
    with pytest.raises(_NoWork):
        mod.main()
