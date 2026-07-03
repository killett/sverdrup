"""Tests for the pure sizing functions of the Task-0 MIOST cost probe."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from probe_miost_cost import n_coefficients, nnz_g, scale_set  # noqa: E402


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


def test_n_coefficients_hand_derived() -> None:
    """N_coef(alpha=1, n_dir=8, 60 d, lam_min=80) = 61,056.

    Hand derivation (independent of the code): D_x = 10 * 111.32 * cos(38 deg)
    = 877.2 km, D_y = 1113.2 km. Per scale ceil(D_x/lam) * ceil(D_y/lam):
    11*14 + 8*10 + 6*7 + 4*5 + 3*4 + 2*3 + 2*2 = 318 spatial positions.
    Times n_t = ceil(60/5) = 12, times 8 directions, times 2 phases -> 61,056.
    """
    assert n_coefficients(alpha=1.0, n_dir=8, window_days=60, lam_min=80.0) == 61_056


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
