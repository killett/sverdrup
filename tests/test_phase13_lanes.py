"""Tests for the phase-13 lane machinery (plan Task 7).

Each test names the bug it catches; expected values hand-derived from the
sealed boxes and the signed record.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sverdrup.validation import phase13_lanes as lanes
from tests.helpers import load_script


def test_pairing_shared_dims_equal_across_lanes() -> None:
    # ONE shared engine + per-lane masking: at the same index, released
    # dims common to two lanes carry IDENTICAL draws.
    # Bug caught: per-lane engines (or per-lane reseeding) breaking the
    # pairing the sealed §7 design depends on.
    d = lanes.sobol_trials("D", 5)
    c = lanes.sobol_trials("C", 5)
    m = lanes.sobol_trials("modes-only", 5)
    for i in range(5):
        for dim in ("delta_alg", "delta_h2g", "delta_j2g", "delta_j2n", "log10_rho"):
            assert d[i][dim] == c[i][dim], (i, dim)
        for dim in ("log10_rho", "log_lam_bias", "log_lam_tilt"):
            assert m[i][dim] == c[i][dim], (i, dim)


def test_masked_lambda_is_none_never_zero() -> None:
    # Structural column absence (spec §2 rider 3): masked Λ dims are None.
    # Bug caught: Λ frozen at 0.0 — a zero prior variance divides by zero
    # in Q_aug^-1 (or silently builds a degenerate mode block).
    for t in lanes.sobol_trials("D", 3):
        assert t["log_lam_bias"] is None
        assert t["log_lam_tilt"] is None
    for t in lanes.sobol_trials("modes-only", 3):
        assert t["delta_alg"] == 0.0
        assert isinstance(t["log_lam_bias"], float)


def test_lane0_trial_is_the_signed_restriction() -> None:
    # lane-0 = the signed config: δ all 0, ρ at the signed value, Λ absent.
    # Bug caught: the quoted lane drifting from the record.
    t = lanes.lane0_trial()
    assert all(t[f"delta_{m}"] == 0.0 for m in ("alg", "h2g", "j2g", "j2n"))
    assert t["log10_rho"] == lanes.SIGNED_PARAMS["log10_rho"]
    assert t["log_lam_bias"] is None and t["log_lam_tilt"] is None


def test_signed_params_match_record() -> None:
    # Bug caught: the frozen literal drifting from the signed record.
    rec = json.loads(
        Path(
            "data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json"
        ).read_text()
    )
    assert lanes.SIGNED_PARAMS == rec["winner"]["params"]


def test_rspec_for_trial_wiring() -> None:
    # Bug caught: a lane-D trial arriving with modes active (Λ leaking
    # through), or the contrast dict dropping a mission.
    d = lanes.sobol_trials("D", 1)[0]
    r = lanes.rspec_for_trial(d)
    assert not r.modes_active
    assert r.deltas["alg"] == d["delta_alg"]
    c = lanes.sobol_trials("C", 1)[0]
    rc = lanes.rspec_for_trial(c)
    assert rc.modes_active
    assert rc.log_lam_bias == c["log_lam_bias"]


def test_params_for_trial_freezes_alpha_qslope_lt() -> None:
    # Spec §4: α/q_slope/L_t FROZEN at the signed record; ρ from the trial.
    # Bug caught: a trial's ρ silently discarded (all lanes sweeping a
    # dead dimension) or a frozen dim picked up from the trial dict.
    c = lanes.sobol_trials("C", 1)[0]
    p = lanes.params_for_trial(c)
    assert p["spacing_alpha"] == lanes.SIGNED_PARAMS["spacing_alpha"]
    assert p["q_slope"] == lanes.SIGNED_PARAMS["q_slope"]
    assert p["l_t_days"] == lanes.SIGNED_PARAMS["l_t_days"]
    assert p["log10_rho"] == c["log10_rho"]


def test_anchors_lane0_at_lambda_box_floor_into_c() -> None:
    # Spec §4 anchor embedding: lane-0 enters C at the Λ BOX-FLOOR (−∞ is
    # outside any box); the D winner enters C the same way. Anchors are
    # evaluated extra points, never Sobol points.
    # Bug caught: lane-0 anchored column-absent inside C (unreachable in
    # the C space — the tie-or-win read would compare across spaces), or
    # the D winner's Λ left None.
    floor = lanes.LOG10_LAM_BOX[0] if hasattr(lanes, "LOG10_LAM_BOX") else -6.0
    d_winner = lanes.sobol_trials("D", 1)[0]
    anchors = lanes.anchors_for("C", {"D": d_winner})
    assert len(anchors) == 2
    for a in anchors:
        assert a["log_lam_bias"] == floor
        assert a["log_lam_tilt"] == floor
    assert anchors[0]["delta_alg"] == 0.0  # lane-0 first
    assert anchors[1]["delta_alg"] == d_winner["delta_alg"]
    # D gets the trivial lane-0 restriction point
    d_anchors = lanes.anchors_for("D", {})
    assert d_anchors == [lanes.lane0_trial()]


def test_sobol_values_inside_boxes() -> None:
    # Bug caught: a unit-cube scaling error placing trials outside the
    # sealed boxes (the pre-registration would be violated silently).
    for t in lanes.sobol_trials("C", 8):
        for dim, (lo, hi) in lanes.BOXES.items():
            v = t[dim]
            assert v is not None and lo <= v <= hi, (dim, v)


def test_lane_bars_point_capability_mu_only() -> None:
    # Lane trials are POINT solves: the µ floor only — no coverage bar.
    # Bug caught: a coverage bar demanded of variance-less trials (every
    # trial inadmissible; the sweep would select nothing).
    bars = lanes.lane_bars()
    assert [b.metric for b in bars] == ["mu_score"]


def test_runner_refuses_without_the_sealed_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Launch rule (plan Task 7): the runner reads the Task-6 bundle and
    # REFUSES if absent — no sweep without the seal.
    # Bug caught: a sweep silently launching against an unsealed state.
    runner = load_script("phase13_lane_run")
    empty = tmp_path / "results.json"
    empty.write_text("{}")
    monkeypatch.setattr(runner, "_RESULTS", empty)
    with pytest.raises(SystemExit, match="prereg"):
        runner.main_for_lane("D")


def test_modes_only_lane_uses_the_sealed_hyphen_name() -> None:
    # The sealed band artifact (phase13_band_artifact.json) and the probe's
    # budget determination both spell the conditional lane "modes-only"
    # (hyphen); LANES must match so the runner is invokable with the name
    # the sealed budget lists.
    # Bug caught: the LANES key keyed "modes_only" (the underscore odd-one-
    # out vs the sha-sealed artifact) — the incident that left the
    # pre-registered third lane unrunnable.
    assert "modes-only" in lanes.LANES
    assert "modes_only" not in lanes.LANES


def test_runner_choices_cover_every_budget_funded_lane() -> None:
    # Cross-namespace invariant: the lane runner draws its --lane argparse
    # choices from LANES, but its launch guard checks membership against the
    # sealed budget's lane list. If the two name-spaces disagree, a budget-
    # funded lane is rejected at the CLI and can never sweep.
    # Bug caught: LANES and the probe's lane strings diverging for the
    # modes-only lane (funded=["D","C","modes-only"] vs a choice set missing
    # it) — exactly the hard-fail that blocked Task 8's third lane.
    probe = load_script("phase13_probe")
    funded = probe.budget_determination(t_trial_s=1200.0, wall_budget_h=12.0)["lanes"]
    runner_choices = set(lanes.LANES) - {"lane0"}
    assert set(funded) <= runner_choices, (funded, sorted(runner_choices))
