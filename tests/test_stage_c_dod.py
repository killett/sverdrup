"""Stage-C definition of done: boundary respected, quantified, relaxable, surfaced (both tiers)."""

from __future__ import annotations

from pathlib import Path

from sverdrup.application.tuning.feasibility import (
    CoherenceFeasibility,
    RelaxedCoherenceFeasibility,
)
from sverdrup.application.tuning.tradeoff import feasibility_frontier


def test_joint_region_empty_marginal_ships() -> None:
    rows = feasibility_frontier(CoherenceFeasibility())
    assert rows and all(
        not r["joint_feasible"] for r in rows
    )  # boundary real: joint empty
    assert all(r["marg_feasible"] for r in rows)  # marginal ships


def test_relaxation_is_the_redesign_interface() -> None:
    n_default = sum(
        r["joint_feasible"] for r in feasibility_frontier(CoherenceFeasibility())
    )
    n_relaxed = sum(
        r["joint_feasible"]
        for r in feasibility_frontier(RelaxedCoherenceFeasibility(n_star_joint=64))
    )
    assert n_relaxed > n_default


def test_frontier_doc_surfaced() -> None:
    p = Path("docs/validation/phase5_feasibility_resolution_frontier.md")
    assert p.exists()
    text = p.read_text()
    assert "MARGINAL_VARIANCE" in text and "owner-deferred" in text
