"""The Matérn GMRF prior marginal variance is τ, independent of range (SPDE normalization).

Root cause of the Phase-5 GMRF zero-skill bug: ``matern_precision`` assembled
``Q=(κ²I−Δ)²/τ`` WITHOUT the ``1/(4πκ²)`` SPDE marginal-variance normalization, so the
prior variance was ``σ²=τ/(4πκ²) ∝ τ·range²`` — ~10³× too large at operational range
(100–800 km) vs the ~0.025 m² SLA signal. The over-loose prior failed to regularize
sparse-nadir interpolation, so the posterior mean over-fit obs and oscillated to ±300 m
in the gaps (zero held-out track skill). These tests pin the corrected contract.
"""

from __future__ import annotations

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.methods.gmrf_grid import kappa_from_range, matern_precision
from sverdrup.methods.gmrf_linalg import GMRFFactor


def _grid() -> GridSpec:
    """A ~12° box at 0.2° (60×60) — interior well-resolves 150–300 km ranges."""
    return GridSpec.lonlat(
        lons=np.arange(0.0, 12.0, 0.2),
        lats=np.arange(30.0, 42.0, 0.2),
    )


def _interior_median_prior_var(
    grid: GridSpec, range_km: float, tau: float, margin: int = 8
) -> float:
    """Return the interior-median prior marginal variance diag(Q⁻¹) (Neumann edges excluded)."""
    q = matern_precision(grid, kappa_from_range(range_km), tau)
    var = np.asarray(GMRFFactor(q).selective_inverse().diagonal()).reshape(grid.shape)
    ny, nx = grid.shape
    return float(np.median(var[margin : ny - margin, margin : nx - margin]))


def test_prior_variance_is_range_independent() -> None:
    # Behavior: the SPDE marginal variance is τ, independent of range.
    # Bug it catches: the missing 1/(4πκ²) normalization makes σ² ∝ range², so doubling
    # the range ~4×'s the prior variance (ratio ≈ (300/150)² = 4 without the fix).
    grid = _grid()
    v_short = _interior_median_prior_var(grid, 150.0, tau=1.0)
    v_long = _interior_median_prior_var(grid, 300.0, tau=1.0)
    assert 0.6 < v_long / v_short < 1.6


def test_prior_variance_matches_tau_magnitude() -> None:
    # Behavior: σ² ≈ τ in magnitude (the "variance" knob means marginal variance).
    # Bug it catches: the missing normalization inflates σ² by ~1/(4πκ²) ≈ 300× here
    # (range 250 km, κ≈0.0113), so the unnormalized value is ~150, not ~0.5.
    v = _interior_median_prior_var(_grid(), 250.0, tau=0.5)
    assert 0.25 < v < 1.0


def test_prior_variance_field_kappa_is_normalized() -> None:
    # Behavior: the nonstationary κ-field path is normalized per-node too (σ²≈τ),
    # so a lat-varying range does not blow up the variance where the range is large.
    # Bug it catches: scalar-only normalization that leaves the field path ∝ range².
    grid = _grid()
    ny, nx = grid.shape
    range_field = np.linspace(150.0, 300.0, ny)[:, None] * np.ones((1, nx))
    q = matern_precision(grid, kappa_from_range(range_field), tau=0.5)
    var = np.asarray(GMRFFactor(q).selective_inverse().diagonal()).reshape(grid.shape)
    interior = var[8 : ny - 8, 8 : nx - 8]
    # Every interior node sits near σ²≈τ regardless of its local range.
    assert np.all(interior > 0.1) and np.all(interior < 1.5)
