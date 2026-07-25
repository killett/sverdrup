"""Stage-1 seam dispersion metrics (phase-14, pre-registered rubric).

Authoritative definitions live in ``docs/validation/phase14_seam_rubric.md``
(PRE-REGISTERED in Stage 0); this module applies them mechanically:

- :func:`interior_increment_rms` — the interior reference dispersion
  ``D_int``: pooled one-grid-step increment RMS along the axis
  perpendicular to the seam, interior nodes only (the caller passes the
  already-trimmed core-interior field).
- :func:`seam_delta` — ``RMS(delta)``: co-located mean-map disagreement on
  the seam line (separation zero — two solves, one point).
- :func:`seam_verdict` — the pre-registered verdict cells (CLEAN /
  ELEVATED / STRUCTURAL_STOP), thresholds read from the sealed
  ``instrument_configs()["seam"]`` at CALL time (never cached at import).
- :func:`seam_read` — the assembled reading, guarded by a residual
  validity guard: an invalid solve (PCG final relative residual not
  known to be within its rtol) never produces a verdict. The rubric's
  Rule-0 floor-probe attributability check (3x solver floor) is applied
  by the consumer (T4), not here.

Pure numpy metric arithmetic — no solver imports, no file I/O. NaN nodes
(land) are excluded from every pool; an all-NaN pool refuses.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from sverdrup.validation.phase14_instruments import instrument_configs

VERDICT_CLEAN = "CLEAN"
VERDICT_ELEVATED = "ELEVATED"
VERDICT_STRUCTURAL_STOP = "STRUCTURAL_STOP"


def _rms(values: NDArray[np.float64]) -> float:
    """Root-mean-square of a 1-D pool of finite values.

    Args:
        values: Finite values; must be non-empty.

    Returns:
        ``sqrt(mean(values**2))``.
    """
    return float(np.sqrt(np.mean(np.square(values))))


def _finite_increments(field: ArrayLike, axis: int) -> NDArray[np.float64]:
    """One-grid-step increments along ``axis`` with NaN pairs dropped.

    Any increment touching a NaN (land) node is NaN and is excluded, which
    implements the rubric's node-exclusion for the interior pool.

    Args:
        field: Interior field values (any array-like of floats).
        axis: Axis along which to take one-grid-step differences.

    Returns:
        Flat array of the finite increments (possibly empty).
    """
    increments = np.diff(np.asarray(field, dtype=np.float64), axis=axis)
    flat: NDArray[np.float64] = increments.ravel()
    return flat[np.isfinite(flat)]


def interior_increment_rms(field: ArrayLike, axis: int) -> float:
    """Interior reference dispersion ``D_int`` for one interior field.

    Rubric definition: ``RMS(field(x + s*e_perp) - field(x))`` over the
    interior nodes, ``s`` one grid step, ``e_perp`` the axis perpendicular
    to the seam (the caller passes that axis). NaN nodes are excluded.

    Args:
        field: Core-interior field values (already trimmed by the caller
            to nodes at least overlap-width from any core boundary).
        axis: Axis perpendicular to the shared boundary.

    Returns:
        Pooled one-grid-step increment RMS.

    Raises:
        ValueError: If the pool has no finite increments (all-NaN interior).
    """
    increments = _finite_increments(field, axis)
    if increments.size == 0:
        raise ValueError("all-NaN interior: no finite one-grid-step increments to pool")
    return _rms(increments)


def seam_delta(field_a: ArrayLike, field_b: ArrayLike) -> float:
    """``RMS(delta)``: co-located seam disagreement between two solves.

    Rubric definition: RMS of ``field_A(x) - field_B(x)`` over the seam
    nodes ``x`` (each tile's own solve, before blending). A node that is
    NaN in either field is excluded from the pool.

    Args:
        field_a: Tile A values on the seam line.
        field_b: Tile B values on the same (co-located) seam nodes.

    Returns:
        RMS of the co-located differences.

    Raises:
        ValueError: If the fields have different shapes, or if the seam
            has no finite co-located pair (all-NaN seam).
    """
    a = np.asarray(field_a, dtype=np.float64)
    b = np.asarray(field_b, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError(
            f"seam fields must be co-located: shape {a.shape} != {b.shape}"
        )
    diffs: NDArray[np.float64] = (a - b).ravel()
    finite = diffs[np.isfinite(diffs)]
    if finite.size == 0:
        raise ValueError("all-NaN seam: no finite co-located differences")
    return _rms(finite)


def seam_verdict(r: float) -> str:
    """Map a seam ratio ``R`` to its pre-registered verdict cell.

    Cells (``docs/validation/phase14_seam_rubric.md``): ``R <= clean_max``
    CLEAN; ``clean_max < R <= elevated_max`` ELEVATED (the rubric's
    ELEVATED-RECORDED — report-only); ``R > elevated_max``
    STRUCTURAL_STOP. Thresholds are read from the sealed
    ``instrument_configs()["seam"]`` at call time, never cached at import.

    Args:
        r: The seam ratio ``R = RMS(delta) / D_int``.

    Returns:
        One of ``"CLEAN"``, ``"ELEVATED"``, ``"STRUCTURAL_STOP"``.

    Raises:
        ValueError: If ``r`` is not finite (a poisoned ratio must never
            classify).
    """
    if not np.isfinite(r):
        raise ValueError(f"seam ratio must be finite, got {r!r}")
    seam_cfg = instrument_configs()["seam"]
    clean_max = float(seam_cfg["clean_max"])
    elevated_max = float(seam_cfg["elevated_max"])
    if r <= clean_max:
        return VERDICT_CLEAN
    if r <= elevated_max:
        return VERDICT_ELEVATED
    return VERDICT_STRUCTURAL_STOP


@dataclass(frozen=True)
class SeamRead:
    """One assembled seam reading (the rubric's recorded row core).

    Attributes:
        rms_delta: Co-located seam disagreement RMS.
        d_int: Pooled interior reference dispersion (both tiles).
        r_seam: ``rms_delta / d_int`` — the verdict-bearing ratio.
        verdict: Pre-registered cell for ``r_seam``.
    """

    rms_delta: float
    d_int: float
    r_seam: float
    verdict: str


def seam_read(
    seam_a: ArrayLike,
    seam_b: ArrayLike,
    interior_a: ArrayLike,
    interior_b: ArrayLike,
    axis: int,
    *,
    final_rel_residual_a: float,
    rtol_a: float,
    final_rel_residual_b: float,
    rtol_b: float,
) -> SeamRead:
    """Assemble one seam reading, guarded by a residual validity guard.

    Refuses BEFORE any metric arithmetic unless each underlying solve's
    PCG final relative residual is known to be within its rtol (a NaN
    residual — a crashed or aborted solve — also refuses) — an invalid
    solve never produces a verdict. The rubric's Rule-0 floor-probe
    attributability check (RMS(delta) vs 3x solver floor) is applied by
    the consumer (T4), not here. ``D_int`` pools the one-grid-step
    increments of BOTH core interiors into a single RMS, per the rubric.

    Args:
        seam_a: Tile A values on the seam line.
        seam_b: Tile B values on the co-located seam nodes.
        interior_a: Tile A core-interior field.
        interior_b: Tile B core-interior field.
        axis: Axis perpendicular to the shared boundary.
        final_rel_residual_a: Tile A solve's PCG final relative residual.
        rtol_a: Tile A solve's PCG relative-residual tolerance.
        final_rel_residual_b: Tile B solve's PCG final relative residual.
        rtol_b: Tile B solve's PCG relative-residual tolerance.

    Returns:
        The assembled :class:`SeamRead`.

    Raises:
        ValueError: If either solve is invalid (residual not known to be
            within rtol, including NaN), if the seam or pooled interior
            is all-NaN, or if the seam fields are not co-located.
    """
    for label, residual, rtol in (
        ("A", final_rel_residual_a, rtol_a),
        ("B", final_rel_residual_b, rtol_b),
    ):
        if not residual <= rtol:  # NaN-safe: refuses unless known-converged
            raise ValueError(
                f"residual validity guard: solve {label} PCG final relative "
                f"residual {residual:g} is not within rtol {rtol:g}; an "
                "invalid solve never produces a seam verdict"
            )
    rms_delta = seam_delta(seam_a, seam_b)
    pooled = np.concatenate(
        [
            _finite_increments(interior_a, axis),
            _finite_increments(interior_b, axis),
        ]
    )
    if pooled.size == 0:
        raise ValueError("all-NaN interior: no finite one-grid-step increments to pool")
    d_int = _rms(pooled)
    r_seam = rms_delta / d_int
    return SeamRead(
        rms_delta=rms_delta,
        d_int=d_int,
        r_seam=r_seam,
        verdict=seam_verdict(r_seam),
    )
