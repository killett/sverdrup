"""Registry role-split tests (Phase-10 Task 1; spec §8).

Bugs caught: double registration (a name in both tables silently re-creates
the lookup ambiguity the split kills); "miost" left in METHODS (tuning sweeps
could search the SHIPPED SAMPLES product again — the retired landmine); the
SHIPPED table drifting off the flip-signed factory; the "miost-point" SEARCH
entry vanishing (run_stage_miost would KeyError).
"""

from __future__ import annotations

from sverdrup.methods.miost import shipped_miost6
from sverdrup.methods.registry import METHODS, SHIPPED


def test_tables_disjoint() -> None:
    assert set(METHODS) & set(SHIPPED) == set()


def test_miost_migrated() -> None:
    assert "miost" not in METHODS
    assert SHIPPED["miost"] is shipped_miost6


def test_search_entry_remains() -> None:
    assert "miost-point" in METHODS


def test_run_challenge_map_shipped_escape_reads_shipped_table() -> None:
    """The ``shipped=True`` escape resolves SHIPPED, never METHODS.

    Bug caught: the escape silently falling back to METHODS (KeyError for
    "miost" post-split would be masked, or a tuning-table method would be
    scored as the shipped product). Signature-level check: the resolution
    expression must select between the two tables on the flag.
    """
    import inspect

    from sverdrup.validation.run import run_challenge_map

    src = inspect.getsource(run_challenge_map)
    assert "(SHIPPED if shipped else METHODS)[method_name]" in src
