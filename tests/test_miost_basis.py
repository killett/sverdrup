"""Tests for the MIOST wavelet dictionary (BasisSpec, U2021 Eqs. 18-19)."""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.methods.miost_basis import LADDER, BasisSpec

SPEC = BasisSpec(alpha=1.0, l_t_days=10.0)


def test_ladder_8_rungs_80_to_905() -> None:
    """D1: 8-rung sqrt(2) ladder 80 -> 905.097."""
    assert len(LADDER) == 8 and LADDER[0] == 80.0
    assert LADDER[-1] == pytest.approx(905.097, abs=0.01)


def test_hard_compact_support() -> None:
    """Tier 2: exact zero beyond 1.5*lam spatially and beyond L_t temporally.

    Bug caught: Gaussian-like taper (no hard cutoff) or support radius != 1.5*lam.
    """
    els = SPEC.elements_for_window(start_day=0.0)
    # take one 80-km element near the box center
    p = next(i for i, e in enumerate(els.identity) if e[0] == 0)
    x0, y0, t0 = els.x_km[p], els.y_km[p], els.t_days[p]
    inside = SPEC.evaluate(
        els, np.array([x0 + 0.9 * 120.0]), np.array([y0]), np.array([t0])
    )[0, p]
    outside_x = SPEC.evaluate(
        els, np.array([x0 + 1.01 * 120.0]), np.array([y0]), np.array([t0])
    )[0, p]
    outside_t = SPEC.evaluate(
        els, np.array([x0]), np.array([y0]), np.array([t0 + 10.01])
    )[0, p]
    assert inside != 0.0 and outside_x == 0.0 and outside_t == 0.0


def test_no_omega_t_carrier() -> None:
    """Carrier phase is time-INDEPENDENT (documented absence of propagation).

    Bug caught: an omega*t term sneaking into the carrier. At fixed (x,y), moving in t
    changes only the temporal taper -> the ratio of values at two in-support times
    equals the ratio of tapers, INDEPENDENT of which element (same t-slot) we probe.
    """
    els = SPEC.elements_for_window(start_day=0.0)
    p = next(i for i, e in enumerate(els.identity) if e[0] == 0)
    x = np.array([els.x_km[p] + 20.0])
    y = np.array([els.y_km[p] + 10.0])
    v1 = SPEC.evaluate(els, x, y, np.array([els.t_days[p] + 1.0]))[0, p]
    v2 = SPEC.evaluate(els, x, y, np.array([els.t_days[p] + 3.0]))[0, p]
    lt = SPEC.l_t_days
    expected = np.cos(np.pi * 3.0 / (2 * lt)) / np.cos(np.pi * 1.0 / (2 * lt))
    assert v2 / v1 == pytest.approx(expected, rel=1e-12)


def test_directions_and_phases() -> None:
    """Tier 2: directions j*22.5 deg (mod-180), phase pairs {0, pi/2}."""
    els = SPEC.elements_for_window(start_day=0.0)
    dirs = np.unique(els.identity[:, 1])
    phases = np.unique(els.identity[:, 2])
    np.testing.assert_array_equal(dirs, np.arange(8))
    np.testing.assert_array_equal(phases, np.arange(2))
    np.testing.assert_allclose(np.unique(els.phase), [0.0, np.pi / 2], atol=1e-15)


def test_global_slot_identity_window_independent() -> None:
    """Same physical element enumerated from two overlapping windows -> same identity."""
    a = SPEC.elements_for_window(start_day=0.0)
    b = SPEC.elements_for_window(start_day=45.0)
    shared = set(map(tuple, a.identity)) & set(map(tuple, b.identity))
    assert shared  # the 15-day overlap shares temporal slots


def test_elements_for_window_custom_w_days() -> None:
    """Task-11 harness: a 425-d window enumerates slots across its FULL span.

    Bug caught: j_hi hardwired to start + 60 — the single-window instance would
    silently truncate to the first 60 days.
    """
    spec = BasisSpec(alpha=1.5, l_t_days=10.0, ladder=(452.548,))
    els = spec.elements_for_window(start_day=-30.0, w_days=425.0)
    assert els.t_days.max() == pytest.approx(395.0, abs=spec.dt_days)
    assert els.t_days.min() >= -30.0


def test_temporal_slots_global_epoch() -> None:
    """Slots are j*dt from the EPOCH (day 0), not window-relative offsets."""
    els = SPEC.elements_for_window(start_day=45.0)
    dt = SPEC.dt_days
    ts = np.unique(els.t_days)
    js = ts / dt
    np.testing.assert_allclose(js, np.round(js), atol=1e-12)
    assert ts.min() >= 45.0 and ts.max() <= 105.0
