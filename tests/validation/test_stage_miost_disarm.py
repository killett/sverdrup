"""P0-1 disarm: the inline stage-b touch refuses; --c2-touch is the only touch.

Bugs caught: the legacy env branch re-spending the one authorized touch and
overwriting the signed sb["c2_acceptance"] with scalar-era semantics; a
refusal that still opens the c2 file; loss of the READY early-return.
"""

from __future__ import annotations

import pytest

from tests.helpers import load_script

gate = load_script("stage_miost_gate_run")


def test_env_set_refuses_with_pinned_text() -> None:
    with pytest.raises(SystemExit) as exc:
        gate.refuse_inline_touch({"SVERDRUP_MIOST_C2": "1"})
    assert "--c2-touch" in str(exc.value)
    assert "DISARMED" in str(exc.value)


def test_env_unset_is_noop() -> None:
    gate.refuse_inline_touch({})  # no raise


@pytest.mark.parametrize("val", ["0", "true", "", " 1"])
def test_non_exact_values_are_noop(val: str) -> None:
    gate.refuse_inline_touch({"SVERDRUP_MIOST_C2": val})  # no raise


def test_stage_b_main_never_writes_acceptance() -> None:
    """Source-level pin: no sb["c2_acceptance"] assignment remains in stage_b_main."""
    import inspect

    src = inspect.getsource(gate.stage_b_main)
    assert 'sb["c2_acceptance"]' not in src
    assert "refuse_inline_touch" in src
