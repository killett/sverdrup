"""Geometry-consuming ground-track artifact metric (spec §4; plan Task 3)."""

from __future__ import annotations

from typing import Any, cast

import numpy as np

from sverdrup.core.evaluation import ContextKey, EvalContext, MetricScope
from sverdrup.eval.map_spectrum import (
    PlaneGrid,
    annulus_mask,
    detrend,
    power2d,
    radial_hann,
    wedge_mask,
)
from sverdrup.eval.phase11_constants import (
    DK_HALFWIDTH_BINS,
    DTHETA_DEG,
    MAX_WIDENINGS,
    N_MODES_BASELINE_FLOOR,
)


def probe_angle_east_deg(heading_north_deg: float) -> float:
    """Wavevector direction (from east, axial) of a track family's signature.

    Track stripes lie ALONG the track, spaced perpendicular to it, so the
    spectral signature sits at the direction PERPENDICULAR to the track:
    east-referenced angle ``-heading`` (the axial fold in the wedge mask
    normalizes the representative).

    Args:
        heading_north_deg: Axial from-north track heading.

    Returns:
        East-referenced probe angle in degrees (any axial representative).
    """
    return -float(heading_north_deg)


def all_probe_wedge_masks(
    geometry: dict[str, dict[str, dict[str, Any] | None]], grid: PlaneGrid
) -> list[np.ndarray]:
    """Full-radial-range angular exclusion wedges for EVERY family.

    ONE implementation serves both consumers (spec §3): GroundTrack's
    baseline exclusions here, and SpectralFidelity's ring exclusions through
    the Task-6 builder, which precomputes these masks once and shares the
    objects (owner plan-review pin 1b).

    Args:
        geometry: The ORBIT_GEOMETRY bag ``{mission: {"asc"/"desc": fam}}``.
        grid: The map plane grid.

    Returns:
        Boolean masks over the kept half-plane modes, one per family, in
        sorted (mission, family) order.
    """
    _p, kx, ky = power2d(
        np.zeros(grid.shape), np.ones(grid.shape), grid
    )  # kept-mode axes only
    k_max = float(np.hypot(kx, ky).max())
    masks = []
    for mission in sorted(geometry):
        for fam_name in ("asc", "desc"):
            fam = geometry[mission].get(fam_name)
            if fam is None:
                continue
            angle = probe_angle_east_deg(float(fam["heading_north_deg"]))
            masks.append(wedge_mask(kx, ky, angle, DTHETA_DEG, 0.0, k_max + 1.0))
    return masks


def _family_band_km(fam: dict[str, Any]) -> tuple[float, float, bool]:
    """Radial band ``(k_lo, k_hi)`` in cyc/km for one family.

    Returns:
        ``(k_lo, k_hi, drifting)`` — repeat: point band at 1/d_perp (widened
        by the caller in bins); drifting: [1/q90, 1/q10] wedge-over-range.
    """
    if fam["orbit_class"] == "repeat":
        k0 = 1.0 / float(fam["d_perp_km"])
        return k0, k0, False
    q10, _q50, q90 = fam["spacing_quantiles_km"]
    return 1.0 / float(q90), 1.0 / float(q10), True


class GroundTrack:
    """Oriented-band track-artifact excess vs a same-|k| annulus baseline.

    NECESSARY-NOT-SUFFICIENT — a strong track signature proves a problem;
    a clean map does not prove correctness.

    Mean maps ONLY (Phase-8 theorem, recorded here): posterior covariance
    ``(G'R^-1G + Q^-1)^-1`` is independent of obs VALUES, so sigma/variance
    maps LEGITIMATELY carry sampling-geometry pattern — scoring them would
    "detect" an expected feature. ``field_kind != "mean"`` refuses loudly.

    Per family: band = axial wedge at the perpendicular-to-track probe angle
    (± DTHETA_DEG) over radius 1/d_perp ± DK_HALFWIDTH_BINS zonal-fundamental
    bins (repeat) or [1/q90, 1/q10] (drifting, flagged estimand). Baseline =
    the same-|k| annulus minus ALL families' exclusion wedges. Statistic =
    ``log10((band/n_band) / (baseline/n_baseline))`` per day, median over
    days — per-mode normalized, expectation 0 on isotropic input. Baseline
    under N_MODES_BASELINE_FLOOR widens ±1 bin/side up to MAX_WIDENINGS,
    beyond which the row is flagged ``under_floor`` (metric still reported).

    Exclusion masks may arrive precomputed via ``result["track_wedge_masks"]``
    (the Task-6 builder's shared objects, owner pin 1b); absent, the SAME
    implementation (:func:`all_probe_wedge_masks`) derives them here.
    """

    name = "groundtrack"
    required_context = frozenset({ContextKey.ORBIT_GEOMETRY})
    optional_context: frozenset[ContextKey] = frozenset()
    metric_scope = MetricScope.POINTWISE

    def evaluate(self, result: object, context: EvalContext) -> dict[str, float]:
        """Score per-family track-signature excess on mean maps.

        Args:
            result: Mapping with ``fields`` (n_days, ny, nx), ``grid_lon``,
                ``grid_lat``, ``field_kind`` and optionally
                ``track_wedge_masks``.
            context: Must carry ``ORBIT_GEOMETRY``.

        Returns:
            Flat metrics: ``track_excess_log10_{mission}_{family}`` with
            ``_n_modes_band`` / ``_n_modes_baseline`` / ``_n_widenings``
            companions, ``_under_floor`` / ``_estimand_drifting_band`` flags,
            and per-class maxima ``track_excess_log10_max_{repeat|drifting}``.

        Raises:
            ValueError: On non-mean ``field_kind`` (Phase-8 theorem) or NaN.
        """
        r = cast(Any, result)
        if r.get("field_kind") != "mean":
            raise ValueError(
                "GroundTrack scores mean maps ONLY (Phase-8 theorem: posterior "
                "sigma legitimately carries sampling-geometry pattern); got "
                f"field_kind={r.get('field_kind')!r}"
            )
        geometry = cast(
            "dict[str, dict[str, dict[str, Any] | None]]",
            context.items[ContextKey.ORBIT_GEOMETRY],
        )
        maps = np.asarray(r["fields"], dtype=float)
        if maps.ndim == 2:
            maps = maps[None]
        if np.isnan(maps).any():
            raise ValueError("NaN in box — GroundTrack requires a complete field")
        grid = PlaneGrid.from_deg(np.asarray(r["grid_lon"]), np.asarray(r["grid_lat"]))
        win = radial_hann(grid)
        day_powers = [power2d(detrend(day), win, grid) for day in maps]
        kx, ky = day_powers[0][1], day_powers[0][2]
        exclusions = r.get("track_wedge_masks")
        if exclusions is None:
            exclusions = all_probe_wedge_masks(geometry, grid)
        dk = 1.0 / grid.lx_km
        out: dict[str, float] = {}
        per_class: dict[str, list[float]] = {"repeat": [], "drifting": []}
        for mission in sorted(geometry):
            for fam_name in ("asc", "desc"):
                fam = geometry[mission].get(fam_name)
                if fam is None:
                    continue
                k_lo0, k_hi0, drifting = _family_band_km(fam)
                angle = probe_angle_east_deg(float(fam["heading_north_deg"]))
                width = DK_HALFWIDTH_BINS * dk
                widenings = 0
                while True:
                    k_lo = max(k_lo0 - width, 0.5 * dk)
                    k_hi = k_hi0 + width
                    band = wedge_mask(kx, ky, angle, DTHETA_DEG, k_lo, k_hi)
                    base = annulus_mask(kx, ky, k_lo, k_hi)
                    for excl in exclusions:
                        base &= ~excl
                    n_base = int(base.sum())
                    if n_base >= N_MODES_BASELINE_FLOOR or widenings >= MAX_WIDENINGS:
                        break
                    widenings += 1
                    width += dk
                n_band = int(band.sum())
                under = n_base < N_MODES_BASELINE_FLOOR
                day_vals = []
                for power, _kx, _ky in day_powers:
                    band_mean = float(power[band].mean()) if n_band else np.nan
                    base_mean = float(power[base].mean()) if n_base else np.nan
                    day_vals.append(float(np.log10(band_mean / base_mean)))
                key = f"track_excess_log10_{mission}_{fam_name}"
                value = float(np.median(day_vals))
                out[key] = value
                out[key + "_n_modes_band"] = float(n_band)
                out[key + "_n_modes_baseline"] = float(n_base)
                out[key + "_n_widenings"] = float(widenings)
                if under:
                    out[key + "_under_floor"] = 1.0
                if drifting:
                    out[key + "_estimand_drifting_band"] = 1.0
                per_class[str(fam["orbit_class"])].append(value)
        for cls, vals in per_class.items():
            if vals:
                out[f"track_excess_log10_max_{cls}"] = float(max(vals))
        return out
