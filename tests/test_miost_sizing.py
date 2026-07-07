"""Tests for the MIOST basis sizing arithmetic (single source: methods/miost_sizing)."""

from __future__ import annotations

import math

import pytest

from sverdrup.methods.miost_sizing import n_coefficients, nnz_g, scale_set


def test_scale_ladder_80() -> None:
    """Ladder from 80 km: 7 scales, consecutive ratio sqrt(2), capped at 800.

    Hand ladder: 80, 113.14, 160, 226.27, 320, 452.55, 640; next = 905 > 800.
    """
    scales = scale_set(80.0)
    assert len(scales) == 7
    assert scales[0] == 80.0
    assert scales[-1] == pytest.approx(640.0)
    assert all(s <= 800.0 for s in scales)
    for a, b in zip(scales, scales[1:], strict=False):
        assert b / a == pytest.approx(math.sqrt(2.0), rel=1e-12)


def test_scale_ladder_113() -> None:
    """Ladder from 113 km: 6 scales; 113 * sqrt(2)^6 = 904 km must be excluded."""
    scales = scale_set(113.0)
    assert len(scales) == 6
    assert scales[-1] < 800.0


def test_scale_ladder_905_cap() -> None:
    """8-rung ladder 80->905 (D1). Hand: 80*sqrt(2)^7 = 905.097 <= 905 cap + eps."""
    scales = scale_set(80.0, lam_max=905.0)
    assert len(scales) == 8
    assert scales[-1] == pytest.approx(905.097, abs=0.01)


def test_n_coefficients_hand_derived() -> None:
    """N_coef(alpha=1, n_dir=8, 60 d, lam_min=80) = 61,056.

    Hand derivation (independent of the code): D_x = 10 * 111.32 * cos(38 deg)
    = 877.2 km, D_y = 1113.2 km. Per scale ceil(D_x/lam) * ceil(D_y/lam):
    11*14 + 8*10 + 6*7 + 4*5 + 3*4 + 2*3 + 2*2 = 318 spatial positions.
    Times n_t = ceil(60/5) = 12, times 8 directions, times 2 phases -> 61,056.
    """
    assert n_coefficients(alpha=1.0, n_dir=8, window_days=60, lam_min=80.0) == 61_056


def test_n_coefficients_margin_term() -> None:
    """Pavement margin (D=box+2*1.5*lam per scale) raises N_coef; box-only unchanged.

    Hand (lam=80, alpha=1): n_x = ceil((877.2+240)/80) = 14, n_y = ceil((1113.2+240)/80) = 17
    vs box-only 11 x 14 — margin must produce MORE positions at every scale.
    """
    box = n_coefficients(alpha=1.0, n_dir=8, window_days=60, lam_min=80.0, margin=False)
    marg = n_coefficients(alpha=1.0, n_dir=8, window_days=60, lam_min=80.0, margin=True)
    assert box == 61_056  # the probe's hand-derived anchor still holds
    assert marg > box


def test_n_coefficients_monotone_in_alpha() -> None:
    """Finer spacing (smaller alpha) must mean strictly more coefficients."""
    counts = [
        n_coefficients(alpha=a, n_dir=8, window_days=60, lam_min=80.0)
        for a in (0.5, 1.0, 1.5)
    ]
    assert counts[0] > counts[1] > counts[2]


def test_nnz_g_hand_derived() -> None:
    """nnz per obs per scale = (3/alpha)^2 * n_dir * 2 * (2 L_t / dt).

    Hand: alpha=1 -> 9*8*2*4 = 576/obs/scale; 7 scales, 1000 obs -> 4,032,000.
    alpha=1.5 -> 4*8*2*4 = 256/obs/scale -> 1,792,000.
    """
    assert nnz_g(n_obs=1000, alpha=1.0, n_dir=8, lam_min=80.0) == 4_032_000
    assert nnz_g(n_obs=1000, alpha=1.5, n_dir=8, lam_min=80.0) == 1_792_000


def test_nnz_g_zero_obs() -> None:
    """No observations -> G has no entries at all."""
    assert nnz_g(n_obs=0, alpha=1.0, n_dir=8, lam_min=80.0) == 0


def test_peak_model_component_arithmetic() -> None:
    """Component bytes are exact hand arithmetic (Task 22, no fudge factors).

    Hand (alpha=1.5, n_dir=8, 2-rung ladder 320/452.5, n_obs=100, m=1):
    per-obs-per-scale overlaps = (3/1.5)^2 * 8 * 2 * (2*10/5) = 256
    nnz = 100 * 2 * 256 = 51_200; CSR = 12 B/nnz = 614_400 B;
    assembly triplets = 24 B/nnz = 1_228_800 B (the measured ~2x transient).
    Bug caught: wrong per-nnz byte constants (e.g. int64 indices -> 16 B)
    or a silent multiplier -- the predicate would misprice every config.
    """
    from sverdrup.methods.miost_sizing import peak_model

    pc = peak_model(
        alpha=1.5,
        n_dir=8,
        window_days=60.0,
        lam_min=320.0,
        lam_max=453.0,
        n_obs=100,
        m=1,
    )
    assert pc.csr_g == 12 * 51_200
    assert pc.assembly_triplets == 24 * 51_200


def test_peak_model_is_phase_max_not_component_sum() -> None:
    """Peak = max over solve phases, NOT the sum of everything.

    G assembly triplets are freed before the PCG workspace exists, and S is
    built only after G is freed; summing all components would overestimate
    the peak ~2x and visibly exclude feasible configs.
    Bug caught: total() summing phase-exclusive components.
    """
    from sverdrup.methods.miost_sizing import peak_model

    pc = peak_model(
        alpha=1.5,
        n_dir=8,
        window_days=60.0,
        lam_min=320.0,
        lam_max=453.0,
        n_obs=100,
        m=1,
    )
    always = pc.baseline + pc.retained + pc.obs_arrays
    phases = (
        always + pc.assembly_triplets + pc.csr_g,
        always + pc.csr_g + pc.precond_copy,
        always + pc.csr_g + pc.rhs_batch + pc.solve_workspace,
        always + pc.s_matrix,
    )
    assert pc.total == pytest.approx(max(phases))
    assert pc.total < sum(phases)  # summing phases would be the bug


def test_peak_model_member_batch_scales_solve_phase() -> None:
    """m=100 members must grow the solve phase ~m-fold (OOM-#2 class).

    Bug caught: workspace/RHS not scaled by member count -- a member-gen
    config would pass the predicate and then OOM at the batched solve.
    Hand: rhs_batch and solve_workspace are both linear in m, so total at
    m=100 must exceed total at m=1 by at least 50x their m=1 values.
    """
    from sverdrup.methods.miost_sizing import PeakComponents, peak_model

    def _pm(m: int) -> PeakComponents:
        return peak_model(
            alpha=1.5,
            n_dir=8,
            window_days=60.0,
            lam_min=320.0,
            lam_max=453.0,
            n_obs=100,
            m=m,
        )

    p1, p100 = _pm(1), _pm(100)
    assert p100.rhs_batch == 100 * p1.rhs_batch
    assert p100.solve_workspace == 100 * p1.solve_workspace
    assert p100.total > p1.total
