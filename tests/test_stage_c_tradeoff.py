"""The both-tiers frontier; a relaxed predicate widens the joint region without touching tradeoff.py."""

from __future__ import annotations

from sverdrup.application.tuning.feasibility import (
    CoherenceFeasibility,
    RelaxedCoherenceFeasibility,
)
from sverdrup.application.tuning.tradeoff import feasibility_frontier


def test_default_is_joint_empty_marg_ships() -> None:
    rows = feasibility_frontier(CoherenceFeasibility())
    assert rows and all(not r["joint_feasible"] for r in rows)  # empty joint region
    assert all(r["marg_feasible"] for r in rows)  # marginal ships at every N


def test_relaxed_widens_joint_region() -> None:
    # TEST 6 (Stage C): relaxation widens the joint region; tradeoff.py unchanged.
    n_default = sum(
        r["joint_feasible"] for r in feasibility_frontier(CoherenceFeasibility())
    )
    n_relaxed = sum(
        r["joint_feasible"]
        for r in feasibility_frontier(RelaxedCoherenceFeasibility(n_star_joint=64))
    )
    assert n_relaxed > n_default
