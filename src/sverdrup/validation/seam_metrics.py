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
  by the consumer (T4), not here. One call produces BOTH verdict routes
  of the rubric's per-FIELD-KIND requirement: the mean route (``R_seam``
  on mean maps) and the σ route (``R_seam_sigma = RMS(sigma_delta) /
  D_int_sigma`` on member-std maps), the same pure metric functions
  applied to each field kind, verdict cells applied independently per
  field kind.

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

    Carries BOTH field-kind routes; every field is required, so a read
    missing one route cannot be constructed (a mean-only construction
    refuses with ``TypeError``).

    Attributes:
        rms_delta: Co-located seam disagreement RMS (mean maps).
        d_int: Pooled interior reference dispersion (both tiles, mean maps).
        r_seam: ``rms_delta / d_int`` — the mean-route verdict-bearing ratio.
        verdict: Pre-registered cell for ``r_seam``.
        rms_sigma_delta: Co-located seam disagreement RMS (member-std maps).
        d_int_sigma: Pooled interior reference dispersion (member-std maps).
        r_seam_sigma: ``rms_sigma_delta / d_int_sigma`` — the σ-route
            verdict-bearing ratio (the rubric's second ratio).
        verdict_sigma: Pre-registered cell for ``r_seam_sigma``, applied
            independently of the mean route.
    """

    rms_delta: float
    d_int: float
    r_seam: float
    verdict: str
    rms_sigma_delta: float
    d_int_sigma: float
    r_seam_sigma: float
    verdict_sigma: str


def _pooled_interior_rms(
    interior_a: ArrayLike,
    interior_b: ArrayLike,
    axis: int,
    *,
    kind: str,
) -> float:
    """Pooled interior reference dispersion for one field kind.

    Pools the one-grid-step increments of BOTH core interiors into a
    single RMS, per the rubric — the SAME construction serves the mean
    route (``D_int``) and the σ route (``D_int_sigma``).

    Args:
        interior_a: Tile A core-interior field.
        interior_b: Tile B core-interior field.
        axis: Axis perpendicular to the shared boundary.
        kind: Pool label for the refusal message (``"interior"`` for the
            mean route, ``"sigma interior"`` for the σ route).

    Returns:
        Pooled one-grid-step increment RMS across both interiors.

    Raises:
        ValueError: If the pooled increment set is empty (all-NaN
            interiors for this field kind).
    """
    pooled = np.concatenate(
        [
            _finite_increments(interior_a, axis),
            _finite_increments(interior_b, axis),
        ]
    )
    if pooled.size == 0:
        raise ValueError(f"all-NaN {kind}: no finite one-grid-step increments to pool")
    return _rms(pooled)


def seam_read(
    seam_a: ArrayLike,
    seam_b: ArrayLike,
    interior_a: ArrayLike,
    interior_b: ArrayLike,
    axis: int,
    *,
    sigma_seam_a: ArrayLike,
    sigma_seam_b: ArrayLike,
    sigma_interior_a: ArrayLike,
    sigma_interior_b: ArrayLike,
    final_rel_residual_a: float,
    rtol_a: float,
    final_rel_residual_b: float,
    rtol_b: float,
) -> SeamRead:
    """Assemble one seam reading, guarded by a residual validity guard.

    Refuses BEFORE any metric arithmetic unless each underlying solve's
    PCG final relative residual is known to be within its rtol (a NaN
    residual — a crashed or aborted solve — also refuses) — an invalid
    solve never produces a verdict on EITHER route. The rubric's Rule-0
    floor-probe attributability check (RMS(delta) vs 3x solver floor) is
    applied by the consumer (T4), not here. One call produces BOTH
    field-kind routes: the mean route from the mean-map inputs and the σ
    route from the member-std inputs, via the same pure metric
    functions; the σ inputs are REQUIRED (no defaults) so a σ verdict
    can never be fabricated from mean maps. ``D_int`` (and
    ``D_int_sigma``) each pool the one-grid-step increments of BOTH core
    interiors of their field kind into a single RMS, per the rubric.
    Verdict cells are applied independently per field kind, from the
    sealed thresholds read at call time.

    Args:
        seam_a: Tile A mean-map values on the seam line.
        seam_b: Tile B mean-map values on the co-located seam nodes.
        interior_a: Tile A core-interior mean-map field.
        interior_b: Tile B core-interior mean-map field.
        axis: Axis perpendicular to the shared boundary.
        sigma_seam_a: Tile A member-std values on the seam line.
        sigma_seam_b: Tile B member-std values on the co-located seam nodes.
        sigma_interior_a: Tile A core-interior member-std field.
        sigma_interior_b: Tile B core-interior member-std field.
        final_rel_residual_a: Tile A solve's PCG final relative residual.
        rtol_a: Tile A solve's PCG relative-residual tolerance.
        final_rel_residual_b: Tile B solve's PCG final relative residual.
        rtol_b: Tile B solve's PCG relative-residual tolerance.

    Returns:
        The assembled :class:`SeamRead` carrying both routes.

    Raises:
        ValueError: If either solve is invalid (residual not known to be
            within rtol, including NaN), if a seam or pooled interior of
            either field kind is all-NaN, or if the seam fields of either
            field kind are not co-located.
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
    d_int = _pooled_interior_rms(interior_a, interior_b, axis, kind="interior")
    r_seam = rms_delta / d_int
    rms_sigma_delta = seam_delta(sigma_seam_a, sigma_seam_b)
    d_int_sigma = _pooled_interior_rms(
        sigma_interior_a, sigma_interior_b, axis, kind="sigma interior"
    )
    r_seam_sigma = rms_sigma_delta / d_int_sigma
    return SeamRead(
        rms_delta=rms_delta,
        d_int=d_int,
        r_seam=r_seam,
        verdict=seam_verdict(r_seam),
        rms_sigma_delta=rms_sigma_delta,
        d_int_sigma=d_int_sigma,
        r_seam_sigma=r_seam_sigma,
        verdict_sigma=seam_verdict(r_seam_sigma),
    )
