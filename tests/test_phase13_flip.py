"""Tests for the T14 five-mission lineage flip (owner sign-off 2026-07-21).

``shipped_miost5()`` = the phase-13 chain-lane-D winner (per-mission R +
refit s(x)); the signed scalar-era Phase-8 configuration is preserved
FOREVER as ``shipped_miost5_scalar_phase8()`` (identity/calibration
reference — every pre-phase-13 signed artifact pins THAT config).
Each test names the bug it catches; expected values quoted from the
recorded evidence, never from the implementation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sverdrup.methods.miost import (
    PHASE8_POLY_COEFFS,
    PHASE13_MEMBER_ROOT,
    PHASE13_WINNER_PARAMS,
    STAGE_B_ROOT,
    shipped_miost5,
    shipped_miost5_scalar_phase8,
)

_RESULTS = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")


def _evidence() -> dict[str, Any]:
    return json.loads(_RESULTS.read_text())


def test_flipped_lineage_carries_the_winner_rspec() -> None:
    # The lineage entry's per-mission R must equal the recorded D-winner
    # trial EXACTLY (deltas as CONTRASTS; gauge: delta_s3a = -sum; modes
    # column-absent).
    # Bug caught: hand-typed deltas drifting from the record, or Lambda
    # accidentally activated on the modes-absent shipping lane.
    ev = _evidence()
    trial = ev["phase13"]["miost"]["lanes"]["D"]["winner"]["trial"]
    m = shipped_miost5()
    assert not m.rspec.is_scalar
    assert not m.rspec.modes_active
    for name in ("alg", "h2g", "j2g", "j2n"):
        assert m.rspec.all_deltas[name] == trial[f"delta_{name}"]
    assert m.rspec.all_deltas["s3a"] == -sum(
        trial[f"delta_{n}"] for n in ("alg", "h2g", "j2g", "j2n")
    )


def test_flipped_lineage_carries_the_refit_field() -> None:
    # The lineage s(x) is the phase-13 REFIT field byte-for-byte (the
    # miost5 Phase-8 field is not transferable across an R change).
    # Bug caught: the flip shipping the OLD field with the NEW R — the
    # coverage referent statement would be false.
    ev = _evidence()
    cal_key = ev["phase13"]["miost"]["refit"]["winner_field"]["cal_key"]
    assert shipped_miost5()._calibration.key() == cal_key  # noqa: SLF001


def test_flipped_lineage_winner_params_match_the_record() -> None:
    # Solve params ride the ParameterProvider: the exported constant must
    # equal signed alpha/q_slope/l_t + the winner's log10_rho.
    # Bug caught: a caller solving the lineage product at the wrong rho
    # (the swept dimension) or an unfrozen alpha/q_slope/l_t.
    ev = _evidence()
    trial = ev["phase13"]["miost"]["lanes"]["D"]["winner"]["trial"]
    assert PHASE13_WINNER_PARAMS["log10_rho"] == trial["log10_rho"]
    from sverdrup.validation.phase13_lanes import SIGNED_PARAMS

    for k in ("spacing_alpha", "q_slope", "l_t_days"):
        assert PHASE13_WINNER_PARAMS[k] == SIGNED_PARAMS[k]


def test_flipped_lineage_member_root_is_the_phase13_acceptance_root() -> None:
    # The acceptance provenance: m=100 at the phase-13 root — NEVER the
    # stage-b-winner root (CRN streams must not collide with the signed
    # products').
    # Bug caught: the flip silently reusing STAGE_B_ROOT.
    m = shipped_miost5()
    assert m.members == 100
    assert m.member_root == PHASE13_MEMBER_ROOT == 7742201642112487637
    assert m.member_root != STAGE_B_ROOT


def test_scalar_phase8_factory_preserves_the_signed_config() -> None:
    # The preserved reference: scalar rspec (byte-identical scalar-era
    # params_key), Phase-8 poly field, STAGE_B_ROOT — every pre-phase-13
    # signed artifact pins THIS configuration.
    # Bug caught: the flip mutating the identity-reference config the
    # four-route suite and the Phase-8 regression solve against.
    from sverdrup.distributions.calibration import PolyCalibration

    m = shipped_miost5_scalar_phase8()
    assert m.rspec.is_scalar
    assert m.member_root == STAGE_B_ROOT
    cal = m._calibration  # noqa: SLF001
    assert isinstance(cal, PolyCalibration)
    assert tuple(cal.coeffs) == PHASE8_POLY_COEFFS
