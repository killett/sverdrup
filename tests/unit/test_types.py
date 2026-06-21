from sverdrup.core.types import CovFidelity, Linearity, UncertaintyCapability


def test_cov_fidelity_members_distinct():
    # Bug caught: collapsing EXACT/LOW_RANK/SAMPLE (dispatch could not tell paths apart).
    members = {CovFidelity.EXACT, CovFidelity.LOW_RANK, CovFidelity.SAMPLE}
    assert len(members) == 3


def test_capability_ladder_present():
    # Bug caught: a missing rung breaks native-vs-adapter routing.
    names = {c.name for c in UncertaintyCapability}
    assert names == {"POINT", "MARGINAL_VARIANCE", "COVARIANCE", "SAMPLES"}


def test_linearity_two_routes():
    assert {lin.name for lin in Linearity} == {"LINEAR", "NONLINEAR"}
