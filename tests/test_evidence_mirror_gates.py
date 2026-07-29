"""The mirror's tamper gates, test-pinned (owner pin 59).

Editing ``gate5.mu`` in the evidence store was DEMONSTRATED live to make
``check`` fail naming the node and ``sync`` refuse. Pin 59, on the pin-47
precedent:

> a demonstrated defence with no test is a one-time observation, and this
> one guards every write-once claim in the stage.

So this module re-runs that demonstration against a synthetic store on
every suite run: both gates, plus the byte-identical restore.

Nothing here touches the real evidence store or the real mirror — the
script's module-level paths are redirected into ``tmp_path``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tests.helpers import load_script

STORE_BODY: dict[str, Any] = {
    "phase14": {
        "stage1": {
            "gate5": {"mu": 0.7694588601958132, "sigma": 0.2848175434425789},
            "ignored_telemetry": {"wall_s": 123.4},
        }
    },
    "c2_touch_tally": ["touch 1", "touch 2"],
}
SEAL_BODY = {"seal": "v1", "sha": "a17ea419"}


@pytest.fixture
def mirror(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """The mirror script, redirected onto a synthetic store in ``tmp_path``.

    Args:
        tmp_path: Pytest temporary directory.
        monkeypatch: Fixture used to redirect the module paths.

    Returns:
        The loaded script module, already pointed at the fake store.
    """
    mod = load_script("phase14_evidence_mirror")
    store = tmp_path / "store.json"
    seal = tmp_path / "seal.json"
    store.write_text(json.dumps(STORE_BODY, indent=2))
    seal.write_text(json.dumps(SEAL_BODY, indent=2))

    monkeypatch.setattr(mod, "STORE", store)
    monkeypatch.setattr(mod, "SEAL", seal)
    monkeypatch.setattr(mod, "MIRROR_DIR", tmp_path / "mirror")
    monkeypatch.setattr(mod, "MIRROR", tmp_path / "mirror" / "provenance.json")
    monkeypatch.setattr(mod, "SEAL_MIRROR", tmp_path / "mirror" / "seal.json")
    monkeypatch.setattr(
        mod, "SUPERSESSIONS", tmp_path / "mirror" / "supersessions.json"
    )
    monkeypatch.setattr(
        mod,
        "MIRRORED",
        {
            "phase14.stage1.gate5": "write-once gate-5 constants",
            "c2_touch_tally": "the locked-instrument tally",
        },
    )
    return mod


def _edit_gate5_mu(mod: Any, value: float) -> None:
    """Rewrite a witnessed node in the store — the tamper being defended against.

    Args:
        mod: The loaded mirror script.
        value: The value to write into ``gate5.mu``.
    """
    body = json.loads(mod.STORE.read_text())
    body["phase14"]["stage1"]["gate5"]["mu"] = value
    mod.STORE.write_text(json.dumps(body, indent=2))


def _sha(path: Path) -> str:
    """SHA-256 of a file's bytes.

    Args:
        path: File to hash.

    Returns:
        Hex digest.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_check_passes_on_a_freshly_synced_mirror(mirror: Any) -> None:
    """The baseline: a mirror in step with its store verifies clean.

    Catches a check that can never pass — a gate that always fires is
    noise, and the first thing anyone does with it is stop reading it.
    """
    mirror.sync()

    mirror.check()  # must not raise


def test_check_fails_naming_the_rewritten_node(mirror: Any) -> None:
    """Rewriting a witnessed node makes ``check`` STOP, naming it.

    This is the live demonstration, pinned: editing ``gate5.mu`` in the
    store must be detected. Catches a check that only verifies the
    mirror against its own digests and never compares it to the store —
    which would self-certify while the store drifted underneath.
    """
    mirror.sync()
    _edit_gate5_mu(mirror, 0.9999)

    with pytest.raises(RuntimeError, match="phase14.stage1.gate5") as excinfo:
        mirror.check()

    assert "DRIFTED" in str(excinfo.value)


def test_sync_refuses_to_overwrite_a_witnessed_node(mirror: Any) -> None:
    """``sync`` REFUSES the same edit, and leaves the mirror untouched.

    Catches the failure that would make the whole mirror decorative: a
    sync that quietly re-records the new value, so the rewritten verdict
    becomes the witnessed one and nothing ever reports it.
    """
    mirror.sync()
    before = mirror.MIRROR.read_bytes()
    _edit_gate5_mu(mirror, 0.9999)

    with pytest.raises(RuntimeError, match="APPEND-ONLY VIOLATION"):
        mirror.sync()

    assert mirror.MIRROR.read_bytes() == before


def test_byte_identical_restore_returns_the_gate_to_pass(mirror: Any) -> None:
    """Putting the original bytes back clears the STOP — no latch, no residue.

    Catches a gate that latches into failure once tripped (which forces
    people to disable it), and pins that a restore is judged on BYTES:
    the store file is compared to its own pre-tamper hash, not merely
    re-parsed and re-serialized into something equivalent.
    """
    mirror.sync()
    original_bytes = mirror.STORE.read_bytes()
    original_sha = _sha(mirror.STORE)

    _edit_gate5_mu(mirror, 0.9999)
    with pytest.raises(RuntimeError):
        mirror.check()

    mirror.STORE.write_bytes(original_bytes)

    assert _sha(mirror.STORE) == original_sha
    mirror.check()  # must not raise


def test_supersede_preserves_the_prior_digest_and_body(mirror: Any) -> None:
    """The escape hatch keeps the record it replaces.

    Catches a supersede path that simply overwrites — that would turn
    the authorized route into a laundering route, which is worse than
    having no gate, because the result carries a legitimate label.
    """
    mirror.sync()
    prior = json.loads(mirror.MIRROR.read_text())["nodes"]["phase14.stage1.gate5"]
    _edit_gate5_mu(mirror, 0.5)

    mirror.sync(supersede=["phase14.stage1.gate5"], reason="owner ruling X")

    log = json.loads(mirror.SUPERSESSIONS.read_text())["supersessions"]
    assert len(log) == 1
    assert log[0]["path"] == "phase14.stage1.gate5"
    assert log[0]["reason"] == "owner ruling X"
    assert log[0]["prior_digest"] == prior["digest_sha256"]
    assert log[0]["prior_value"] == prior["value"]
    # and the new value is now the witnessed one
    now = json.loads(mirror.MIRROR.read_text())["nodes"]["phase14.stage1.gate5"]
    assert now["value"]["mu"] == 0.5


def test_supersede_without_a_reason_is_refused(mirror: Any) -> None:
    """An unreasoned supersession is a silent replacement with a label on it.

    Catches an escape hatch that can be taken by flag alone — the gate
    would then be one keystroke from being bypassed with no record of
    why, which is precisely the convention pin 56 said cannot be trusted.
    """
    mirror.sync()
    _edit_gate5_mu(mirror, 0.5)

    with pytest.raises(RuntimeError, match="requires --reason"):
        mirror.sync(supersede=["phase14.stage1.gate5"])


def test_a_brand_new_node_syncs_without_supersede(mirror: Any) -> None:
    """Appending a record is ordinary work, not a violation.

    Catches a gate so strict that every legitimate new measurement or
    correction trips it — which would train the operator to pass
    ``--supersede`` reflexively and hollow out the real protection.
    """
    mirror.sync()
    body = json.loads(mirror.STORE.read_text())
    body["phase14"]["stage1"]["new_record"] = {"measured": 1.0}
    mirror.STORE.write_text(json.dumps(body, indent=2))
    mirror.MIRRORED["phase14.stage1.new_record"] = "a later measurement"

    mirror.sync()  # must not raise

    nodes = json.loads(mirror.MIRROR.read_text())["nodes"]
    assert nodes["phase14.stage1.new_record"]["value"] == {"measured": 1.0}
    assert not mirror.SUPERSESSIONS.exists()
