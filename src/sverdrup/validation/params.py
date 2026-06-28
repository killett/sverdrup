"""baseline_oi.ipynb parameters translated into our OI config (audit-trailed).

Every value here is transcribed from
``vendor/2021a_SSH_mapping_OSE/notebooks/baseline_oi.ipynb`` (v1.0); see
``docs/validation/parameter_audit_trail.md`` for the cell-by-cell mapping and
the kernel/reference-frame caveats.

IMPORTANT method caveat: the challenge BASELINE uses a **Gaussian
(squared-exponential)**, **anisotropic**, **degree-space** covariance
(``exp(-(dlon/Lx)^2 - (dlat/Ly)^2 - (dt/Lt)^2)``), whereas our
``OptimalInterpolation`` uses **Matern-3/2**, **isotropic**, in **km**. The
mapping below (``length_scale = Lx_deg * km_per_deg``) is therefore an *analog*,
not an exact reproduction; a faithful BASELINE needs a Gaussian degree-space
kernel (see the audit trail Task-3 decision). The scalar values (variance,
noise, grid, window) are exact.
"""

from __future__ import annotations

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.parameters import ConstantProvider
from sverdrup.methods.kernel import GaussianSpaceTimeDegrees

# --- exact scalars from baseline_oi.ipynb cell 7 ---
SIGNAL_VARIANCE = 1.0  # OI uses a correlation (B with unit variance); noise is relative
SPATIAL_CORR_DEG = 1.0  # Lx = Ly = 1.0 degree (zonal == meridional decorrelation)
TEMPORAL_CORR_DAYS = 7.0  # Lt = 7 days
OBS_NOISE_STD = 0.05  # noise = 5%; R = diag(noise**2)
OBS_NOISE_VARIANCE = OBS_NOISE_STD**2  # 0.0025 -> DiagonalErrorModel.variance (Task 4)
GRID_RES_DEG = 0.2  # dx = dy = 0.2 degree
COARSEN_TIME = 5  # obs time-coarsening (mean every 5 steps), notebook cell 14

# Output OI grid box (cell 7) — NOTE: 295-305 / 33-43, the OI grid, which is the
# eval region, NOT the wider 285-315 / 23-53 data-extraction box.
LON_MIN, LON_MAX = 295.0, 305.0
LAT_MIN, LAT_MAX = 33.0, 43.0
TIME_MIN, TIME_MAX = "2017-01-01", "2017-12-31"

# Obs influence window: oi_core keeps |obs.time - grid.time| < 2*Lt.
TEMPORAL_HALF_WINDOW_DAYS = 2.0 * TEMPORAL_CORR_DAYS  # 14 days

_KM_PER_DEG = 111.195  # matches Matern32SpaceTime._DEG2KM


def baseline_config() -> tuple[ConstantProvider, GridSpec, float]:
    """Return the baseline_oi OI provider, output grid, and temporal half-window.

    Returns:
        ``(provider, grid, temporal_half_window_days)``. ``provider`` resolves
        ``variance`` (signal variance = 1.0), ``length_scale`` (km, the
        ``Lx`` degree scale mapped to km for our Matern kernel), and
        ``time_scale`` (days). ``grid`` is the 295-305 / 33-43 box at 0.2 deg.
        ``temporal_half_window_days`` is ``2*Lt = 14``.
    """
    provider = ConstantProvider(
        {
            "variance": SIGNAL_VARIANCE,
            "length_scale": SPATIAL_CORR_DEG * _KM_PER_DEG,  # analog (see caveat)
            "time_scale": TEMPORAL_CORR_DAYS,
        }
    )
    grid = GridSpec.lonlat(
        lons=np.arange(LON_MIN, LON_MAX + GRID_RES_DEG, GRID_RES_DEG),
        lats=np.arange(LAT_MIN, LAT_MAX + GRID_RES_DEG, GRID_RES_DEG),
    )
    return provider, grid, TEMPORAL_HALF_WINDOW_DAYS


def baseline_kernel() -> GaussianSpaceTimeDegrees:
    """Return the faithful challenge BASELINE covariance kernel.

    The exact ``oi_core`` covariance: Gaussian, anisotropic, degree-space, with
    ``Lx = Ly = 1.0°``, ``Lt = 7 days`` and unit signal variance. Pass this to
    ``OptimalInterpolation.solve(..., kernel=baseline_kernel())`` to reproduce the
    BASELINE OI (the gate-1 option-(a) decision).
    """
    return GaussianSpaceTimeDegrees(
        variance=SIGNAL_VARIANCE,
        lx_deg=SPATIAL_CORR_DEG,
        ly_deg=SPATIAL_CORR_DEG,
        time_scale=TEMPORAL_CORR_DAYS,
    )
