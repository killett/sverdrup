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
from dataclasses import dataclass

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


# ---------------------------------------------------------------------------
# Task-22 component-sum peak model (no bare multipliers).
#
# Byte constants are the actual dtypes of the solve path:
#   CSR G:      8 B data + 4 B int32 indices per nnz (indptr negligible)
#   triplets:   vals f64 + rows i64 + cols i64 accumulated during assembly
#               (24 B/nnz — the measured "~2x stored-G" transient)
#   workspace:  b2, x, r, z, p, ap (6) + apply_a transients gtx/back (2)
#               = 8 coefficient-shaped f64 arrays per RHS, plus gx/scaled-gx
#               (2) obs-shaped f64 arrays per RHS
#   obs:        lon, lat, t, y, r, CRN identity rows (4) = 8 f64 per obs
# The peak is the MAX over solve phases (assembly / preconditioner /
# batched solve / S build) — G's triplets are freed before the workspace
# exists, and S is built only after G is freed (hardening 2).
# ---------------------------------------------------------------------------

CSR_BYTES_PER_NNZ = 12.0
TRIPLET_BYTES_PER_NNZ = 24.0
COEF_ARRAYS_SOLVE = 8.0
OBS_ARRAYS_SOLVE = 2.0
F64 = 8.0
OBS_FIELDS = 8.0
BASELINE_BYTES = 0.3e9  # measured interpreter+libs RSS at script start


def nnz_s(
    n_grid_nodes: int,
    alpha: float,
    n_dir: int,
    lam_min: float,
    lam_max: float = LAM_MAX,
) -> int:
    """Non-zeros of the SPATIAL S matrix (no t-slot axis) at the grid.

    Per node and per scale: (3/alpha)^2 spatial overlaps x n_dir x 2 phases —
    the per-obs bound of :func:`nnz_g` without the temporal factor.

    Args:
        n_grid_nodes: Grid node count.
        alpha: Element spacing as a fraction of wavelength.
        n_dir: Number of plane-wave directions.
        lam_min: Smallest wavelength [km].
        lam_max: Largest admissible wavelength [km].

    Returns:
        Total nnz(S_spatial).
    """
    per_node_per_scale = (2.0 * SUPPORT_FACTOR / alpha) ** 2 * n_dir * 2
    return int(
        round(n_grid_nodes * len(scale_set(lam_min, lam_max)) * per_node_per_scale)
    )


@dataclass(frozen=True)
class PeakComponents:
    """Named byte components of one window solve + the phase-max total."""

    csr_g: float
    assembly_triplets: float
    precond_copy: float
    s_matrix: float
    obs_arrays: float
    rhs_batch: float
    solve_workspace: float
    baseline: float
    retained: float

    @property
    def total(self) -> float:
        """Peak bytes = max over phases; phase-exclusive parts never summed."""
        always = self.baseline + self.retained + self.obs_arrays
        return max(
            always + self.assembly_triplets + self.csr_g,
            always + self.csr_g + self.precond_copy,
            always + self.csr_g + self.rhs_batch + self.solve_workspace,
            always + self.s_matrix,
        )


def peak_model(
    alpha: float,
    n_dir: int,
    window_days: float,
    lam_min: float,
    n_obs: int,
    m: int = 1,
    lam_max: float = LAM_MAX,
    n_grid_nodes: int = 0,
    retained_bytes: float = 0.0,
    baseline_bytes: float = BASELINE_BYTES,
) -> PeakComponents:
    """Component-sum peak-RSS model for one window solve (Task 22).

    Replaces the bare 2.7x fudge (measured on the 425-d single-RHS path,
    overstating windowed solves) with named components; validate against an
    instrumented WINDOWED trial before trusting the budget.

    Args:
        alpha: Element spacing as a fraction of wavelength.
        n_dir: Number of plane-wave directions.
        window_days: Solve window length [days].
        lam_min: Smallest wavelength [km].
        n_obs: Observation count in the window (support-widened).
        m: Right-hand sides solved jointly (1 = mean; members = m).
        lam_max: Largest admissible wavelength [km].
        n_grid_nodes: Grid nodes for the S phase (0 = no S build).
        retained_bytes: Bytes held across windows by the caller (e.g.
            accumulated member anomalies in merged_members).
        baseline_bytes: Process baseline RSS.

    Returns:
        The named components; ``.total`` is the phase-max peak in bytes.
    """
    nnz = nnz_g(n_obs, alpha, n_dir, lam_min, lam_max)
    n_coef = n_coefficients(alpha, n_dir, window_days, lam_min, lam_max, margin=True)
    return PeakComponents(
        csr_g=CSR_BYTES_PER_NNZ * nnz,
        assembly_triplets=TRIPLET_BYTES_PER_NNZ * nnz,
        precond_copy=CSR_BYTES_PER_NNZ * nnz,
        s_matrix=CSR_BYTES_PER_NNZ
        * nnz_s(n_grid_nodes, alpha, n_dir, lam_min, lam_max),
        obs_arrays=OBS_FIELDS * F64 * n_obs,
        rhs_batch=F64 * n_coef * m,
        solve_workspace=(COEF_ARRAYS_SOLVE * n_coef + OBS_ARRAYS_SOLVE * n_obs)
        * F64
        * m,
        baseline=baseline_bytes,
        retained=retained_bytes,
    )
