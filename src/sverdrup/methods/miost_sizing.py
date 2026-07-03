"""MIOST basis sizing arithmetic — the single source for basis-size costs.

Sizing model (owner-specified, 2026-07-03):
    spatial positions per scale = ceil(D_x/(alpha*lam)) * ceil(D_y/(alpha*lam))
    per-obs overlapping elements per scale = (3/alpha)^2 * n_dir * 2 * (2*L_t/dt)
    support L = 1.5*lam (diameter 3*lam), L_t = 10 d, pavement dt = 5 d,
    scales geometric from lam_min to <= lam_max.

``margin=True`` adds the per-scale 1.5*lam pavement extension each side
(spec §2.1 — elements pave box + margin so edge obs keep full support).

Assumption (flagged, not in the papers): geometric ratio sqrt(2) — implied by
the probe grid's lam_min in {80, 113} being consecutive sqrt(2) steps.
"""

from __future__ import annotations

import math

BOX_LON = (295.0, 305.0)
BOX_LAT = (33.0, 43.0)
KM_PER_DEG = 111.32
MID_LAT = 0.5 * (BOX_LAT[0] + BOX_LAT[1])
D_X_KM = (BOX_LON[1] - BOX_LON[0]) * KM_PER_DEG * math.cos(math.radians(MID_LAT))
D_Y_KM = (BOX_LAT[1] - BOX_LAT[0]) * KM_PER_DEG

SCALE_RATIO = math.sqrt(2.0)
L_T_DAYS = 10.0
DT_DAYS = 5.0
SUPPORT_FACTOR = 1.5  # L = 1.5 * wavelength -> support diameter 3 * wavelength
LAM_MAX = 800.0


def scale_set(
    lam_min: float, lam_max: float = LAM_MAX, ratio: float = SCALE_RATIO
) -> list[float]:
    """Return the geometric wavelength ladder from lam_min up to lam_max.

    Args:
        lam_min: Smallest wavelength [km].
        lam_max: Largest admissible wavelength [km].
        ratio: Geometric ratio between consecutive scales.

    Returns:
        Wavelengths [km], ascending.
    """
    scales = []
    lam = lam_min
    # 0.1% relative slack: the designed 8th rung 80*sqrt(2)^7 = 905.097 km must
    # sit inside the D1 cap of 905 km.
    while lam <= lam_max * (1.0 + 1e-3):
        scales.append(lam)
        lam *= ratio
    return scales


def n_coefficients(
    alpha: float,
    n_dir: int,
    window_days: float,
    lam_min: float,
    lam_max: float = LAM_MAX,
    margin: bool = False,
    dt_days: float = DT_DAYS,
) -> int:
    """Count basis coefficients for one configuration.

    Per scale: spatial positions x temporal positions x directions x 2 phases
    (sine/cosine pairs). ``margin=True`` adds the per-scale 1.5*lam pavement
    extension each side (box-only when False, the probe's original numbers).

    Args:
        alpha: Element spacing as a fraction of wavelength.
        n_dir: Number of plane-wave directions.
        window_days: Solve window length [days].
        lam_min: Smallest wavelength [km].
        lam_max: Largest admissible wavelength [km].
        margin: Whether to extend the pavement by 1.5*lam each side.
        dt_days: Temporal pavement spacing [days].

    Returns:
        Total coefficient count N_coef.
    """
    n_t = math.ceil(window_days / dt_days)
    total = 0
    for lam in scale_set(lam_min, lam_max):
        ext = 2.0 * SUPPORT_FACTOR * lam if margin else 0.0  # 1.5*lam each side
        n_x = max(1, math.ceil((D_X_KM + ext) / (alpha * lam)))
        n_y = max(1, math.ceil((D_Y_KM + ext) / (alpha * lam)))
        total += n_x * n_y * n_t * n_dir * 2
    return total


def nnz_g(
    n_obs: int,
    alpha: float,
    n_dir: int,
    lam_min: float,
    lam_max: float = LAM_MAX,
) -> int:
    """Count non-zeros of G for one configuration.

    Per observation and per scale: (3/alpha)^2 spatial overlaps x n_dir x 2
    phases x (2*L_t/dt) temporal overlaps. Margin-free: the per-obs overlap
    bound is unchanged by pavement extension.

    Args:
        n_obs: Observation count in the window.
        alpha: Element spacing as a fraction of wavelength.
        n_dir: Number of plane-wave directions.
        lam_min: Smallest wavelength [km].
        lam_max: Largest admissible wavelength [km].

    Returns:
        Total nnz(G).
    """
    per_obs_per_scale = (3.0 / alpha) ** 2 * n_dir * 2 * (2.0 * L_T_DAYS / DT_DAYS)
    return int(round(n_obs * len(scale_set(lam_min, lam_max)) * per_obs_per_scale))
