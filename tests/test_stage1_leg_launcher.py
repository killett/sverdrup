"""Hygiene: the Stage-1 leg launcher does not mistake a zombie for a live leg.

``while kill -0 "$PID"`` gated the sampling loop, and ``kill -0`` SUCCEEDS
on a zombie (an exited process its parent has not reaped) — the loop then
samples a dead leg indefinitely and the launcher never reaches its exit
handling. Liveness is now ``proc_alive``, which reads the process state.
The function is exercised as extracted from the script itself.
"""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stage1_leg_launcher.sh"


def _proc_alive_fn() -> str:
    m = re.search(r"^proc_alive\(\) \{.*?^\}", _SCRIPT.read_text(), re.M | re.S)
    assert m is not None, "stage1_leg_launcher.sh defines no proc_alive()"
    return m.group(0)


def _alive(pid: int | str) -> str:
    return subprocess.run(  # noqa: S603
        [
            "sh",
            "-c",
            f'{_proc_alive_fn()}\nproc_alive "{pid}" && echo alive || echo dead',
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def test_a_zombie_is_not_alive() -> None:
    """Bug caught: kill -0 reporting an exited-but-unreaped leg as alive."""
    child = subprocess.Popen(["true"])  # noqa: S603, S607 - not waited: a zombie
    try:
        for _ in range(50):
            state = Path(f"/proc/{child.pid}/stat").read_text().split()[2]
            if state == "Z":
                break
            time.sleep(0.05)
        assert state == "Z", "fixture: the child should be a zombie by now"
        assert (
            subprocess.run(["kill", "-0", str(child.pid)], check=False).returncode == 0
        )
        assert _alive(child.pid) == "dead"
    finally:
        child.wait()


def test_a_running_process_is_alive_and_no_pid_is_not() -> None:
    """Controls: a live process is alive; an unresolved (empty) pid is not."""
    child = subprocess.Popen(["sleep", "30"])  # noqa: S603, S607
    try:
        assert _alive(child.pid) == "alive"
    finally:
        child.kill()
        child.wait()
    assert _alive("") == "dead"


def test_the_sampling_loop_gates_on_proc_alive_not_kill_0() -> None:
    """Bug caught: the loop still gated on kill -0 after the helper existed."""
    text = _SCRIPT.read_text()
    assert 'while proc_alive "$PID"' in text
    code = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    assert not [ln for ln in code if "kill -0" in ln]
