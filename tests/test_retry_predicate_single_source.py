"""One transient-fault predicate, owned by the ODC download adapter (hygiene #36)."""

from __future__ import annotations

from sverdrup.adapters.odc import download
from sverdrup.validation import access


def test_every_retry_predicate_is_the_reference_one() -> None:
    """Every ``stamina.retry(on=...)`` predicate is the one CLAUDE.md names.

    Identity, not equality: a re-pasted copy is a distinct function object,
    so a copy fails here even while its body still agrees. Bug caught: a
    second predicate drifting (say, retrying 4xx) in one layer while the
    reference stays strict, so the same fault is retried by one download
    path and surfaced by another.
    """
    assert access.is_retryable is download.is_retryable
    assert download._is_retryable is download.is_retryable  # script importers
