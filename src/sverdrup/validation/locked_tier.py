"""Generalized locked-tier touch ceremony + per-era tally ledger (0a-4).

ONE touch = one scoring pass of an accepted product over the sealed locked
set for its era range. The ceremony inherits the phase-13 mechanics
verbatim: exact-string env, seal tripwire recomputed BEFORE any locked
data opens, refusal tests green pre-touch, dated defect keys, the misfire
protocol per the owner 2026-07-20 recording.

**gate approval is NOT touch authorization** (the standing rule): the
owner's gate ruling never opens this ceremony — a FRESH authorization
message does, and the env is set by :func:`open_touch` for its child
scope only, never exported by any other code path.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sverdrup.adapters.insitu.gauges import LOCKED_ENV

TOUCH_ENV = "SVERDRUP_PHASE14_TOUCH"

_TALLY_KEYS = ("phase14", "locked_tally")


class TouchRefusedError(RuntimeError):
    """The ceremony refused to open (env / tally / double-open)."""


class SealVerificationError(RuntimeError):
    """The seal tripwire failed (mismatch or missing seal)."""


def default_seal_verifier() -> None:
    """The REAL verifier (Task 19): byte-verify the recorded current seal.

    Delegates to ``phase14_seal.verify_current_seal`` — refuses while no
    seal is recorded in evidence (a locked open before the sealed set
    exists is definitionally unceremonied) and on any byte mismatch.

    Raises:
        SealVerificationError: No recorded seal or verification failure.
    """
    from sverdrup.validation.phase14_seal import (  # noqa: PLC0415
        SealError,
        verify_current_seal,
    )

    try:
        verify_current_seal()
    except SealError as exc:
        raise SealVerificationError(str(exc)) from exc


def read_tally(evidence_path: Path) -> dict[str, Any]:
    """The tally ledger ``{product_id: {era_id: n_touches}}`` (empty ok)."""
    if not evidence_path.exists():
        return {}
    node: Any = json.loads(evidence_path.read_text())
    for k in _TALLY_KEYS:
        node = node.get(k, {})
    return dict(node)


_ceremony_open = False


@contextmanager
def open_touch(
    product_id: str,
    eras: Sequence[str],
    evidence_path: Path,
    seal_verifier: Callable[[], None] = default_seal_verifier,
    corrected_by: str | None = None,
) -> Iterator[None]:
    """The ONE code path that opens locked instruments (context manager).

    Refusal order (all BEFORE any locked data can open):
    (a) ``SVERDRUP_PHASE14_TOUCH`` must be the exact string ``"1"``;
    (b) the seal verifier runs — a mismatch or missing seal refuses;
    (c) any (product, era) tally at ≥ 1 refuses unless ``corrected_by``
        names the owner's dated defect key (misfire protocol);
    (d) a second concurrent/nested ceremony refuses.

    Inside the context the locked-instrument env
    (``SVERDRUP_INSITU_LOCKED``) is set for the CHILD SCOPE ONLY and
    restored on exit; the tally increments only on clean completion.

    Args:
        product_id: The accepted product being scored.
        eras: The era ids this touch covers.
        evidence_path: The standing evidence JSON (single-writer).
        seal_verifier: Callable raising :class:`SealVerificationError` on
            any seal problem (Task 19 supplies the real recompute).
        corrected_by: The owner's dated defect key authorizing a corrected
            re-touch of an already-touched (product, era).

    Raises:
        TouchRefusedError: On (a), (c), (d).
        SealVerificationError: On (b).
    """
    global _ceremony_open
    if os.environ.get(TOUCH_ENV) != "1":
        raise TouchRefusedError(
            f"locked-tier touch refused: {TOUCH_ENV} is not the exact "
            'string "1" — the ceremony env comes from a FRESH owner '
            "authorization (gate approval is NOT touch authorization)"
        )
    if _ceremony_open:
        raise TouchRefusedError(
            "a touch ceremony is already open — single-ceremony discipline"
        )
    seal_verifier()  # tripwire BEFORE any locked data opens
    tally = read_tally(evidence_path)
    for era in eras:
        n = int(tally.get(product_id, {}).get(era, 0))
        if n >= 1 and corrected_by is None:
            raise TouchRefusedError(
                f"tally exceeded: ({product_id!r}, {era!r}) already touched "
                f"{n}x — a corrected re-touch needs the owner's dated "
                "defect key (misfire protocol, owner 2026-07-20)"
            )
    _ceremony_open = True
    prev = os.environ.get(LOCKED_ENV)
    os.environ[LOCKED_ENV] = "1"
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop(LOCKED_ENV, None)
        else:  # pragma: no cover - nested-env restore
            os.environ[LOCKED_ENV] = prev
        _ceremony_open = False
    # clean completion only: count the touch (a raise above skips this)
    results: dict[str, Any] = (
        json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    )
    node = results
    for k in _TALLY_KEYS:
        node = node.setdefault(k, {})
    prod = node.setdefault(product_id, {})
    for era in eras:
        prod[era] = int(prod.get(era, 0)) + 1
        if corrected_by is not None:
            prod[f"{era}_corrected_by"] = corrected_by
    evidence_path.write_text(json.dumps(results, indent=1, sort_keys=True))
