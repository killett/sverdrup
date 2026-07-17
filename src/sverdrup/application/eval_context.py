"""One wiring path from products to evaluator report rows (spec §7; Task 6).

The builder is the σ-guard's single source (``field_kind``), the only place
the orbit-geometry artifact enters a context, and the ONE derivation of the
track-wedge exclusion masks — the SAME mask objects serve GroundTrack's
baseline exclusions and SpectralFidelity's ring exclusions (owner plan-review
pin 1b; both report rows record the shared ``wedge_masks_sha``).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from sverdrup.core.context_spy import SpyItems
from sverdrup.core.evaluation import ContextKey, EvalContext, Evaluator, Registry
from sverdrup.eval import ALL_EVALUATORS
from sverdrup.eval.groundtrack import all_probe_wedge_masks
from sverdrup.eval.map_spectrum import PlaneGrid
from sverdrup.eval.phase11_constants import REPORT_SCHEMA_VERSION

# Evaluators consuming the shared exclusion masks (spec §3: one exclusion
# implementation, two consumers) — their rows record wedge_masks_sha.
_MASK_CONSUMERS = frozenset({"groundtrack", "spectral_fidelity"})


def default_registry() -> Registry:
    """The standard report-only registry, built FROM ``ALL_EVALUATORS``.

    EffectiveResolution is excluded THIS PHASE: its inputs (``eval_locations``
    / ``eval_times``) are not part of the standard result payload the builder
    assembles; recorded decision (plan obligation 3) — integrity coverage
    comes from ``ALL_EVALUATORS``, not from this registry.

    Returns:
        A :class:`Registry` over the default evaluator family.
    """
    instances = [f() for f in ALL_EVALUATORS]
    return Registry([ev for ev in instances if ev.name != "effective_resolution"])


@dataclass(frozen=True)
class BuiltEval:
    """Builder output: the enriched result, the context, and mask provenance.

    Attributes:
        result: Shallow copy of the input result with ``field_kind`` (always)
            and ``track_wedge_masks`` (when geometry + grid available) set.
        context: The assembled :class:`EvalContext`.
        wedge_masks_sha: sha256 over the derived mask bytes, or ``None`` when
            no masks were derived.
    """

    result: dict[str, Any]
    context: EvalContext
    wedge_masks_sha: str | None


def _masks_sha(masks: list[np.ndarray]) -> str:
    """Deterministic sha256 of the exclusion-mask set (count + packed bits)."""
    h = hashlib.sha256()
    h.update(str(len(masks)).encode())
    for m in masks:
        h.update(str(m.shape).encode())
        h.update(np.packbits(np.asarray(m, dtype=bool)).tobytes())
    return h.hexdigest()


def _load_geometry_bag(
    artifact: Path, assimilated_missions: str
) -> dict[str, Any] | None:
    """Load the Task-1 artifact filtered by the product's mission attr.

    Args:
        artifact: Path to ``phase11_orbit_geometry.json``.
        assimilated_missions: Space-separated mission ids (the product attr).

    Returns:
        ``{mission: {"asc"/"desc": fam-dict|None}}`` for the intersection of
        artifact missions and the product's assimilated set, or ``None`` when
        the intersection is empty.
    """
    data = json.loads(artifact.read_text())
    wanted = set(assimilated_missions.split())
    bag = {m: fams for m, fams in data["missions"].items() if m in wanted}
    return bag or None


def build_eval_context(
    result: dict[str, Any],
    *,
    field_kind: str,
    truth: dict[str, Any] | None = None,
    withheld: dict[str, Any] | None = None,
    geometry_artifact: Path | str | None = None,
    assimilated_missions: str | None = None,
) -> BuiltEval:
    """Assemble the result payload and context for one evaluation.

    Sets ``field_kind`` on the result (the σ-guard's single source), loads
    ORBIT_GEOMETRY from the Task-1 artifact filtered by the product's
    ``assimilated_missions`` attr, and precomputes the track-wedge exclusion
    masks ONCE when the result carries map axes (pin 1b).

    Args:
        result: Evaluation payload (map fields / eval points); not mutated.
        field_kind: ``"mean"`` | ``"sigma"`` | ``"other"``.
        truth: Optional TRUTH bag.
        withheld: Optional WITHHELD_OBS bag.
        geometry_artifact: Optional path to the orbit-geometry artifact; a
            missing file simply yields no ORBIT_GEOMETRY (absence means
            absence).
        assimilated_missions: Space-separated mission ids from the product's
            NetCDF attr; required for geometry to load (the filter is the
            point — a mission the product never assimilated must not
            contribute probe wedges).

    Returns:
        A :class:`BuiltEval`.
    """
    out = dict(result)
    out["field_kind"] = field_kind
    items: dict[ContextKey, object] = {}
    if truth is not None:
        items[ContextKey.TRUTH] = truth
    if withheld is not None:
        items[ContextKey.WITHHELD_OBS] = withheld
    masks_sha: str | None = None
    if geometry_artifact is not None and assimilated_missions is not None:
        artifact = Path(geometry_artifact)
        if artifact.exists():
            bag = _load_geometry_bag(artifact, assimilated_missions)
            if bag is not None:
                items[ContextKey.ORBIT_GEOMETRY] = bag
                if "grid_lon" in out and "grid_lat" in out:
                    grid = PlaneGrid.from_deg(
                        np.asarray(out["grid_lon"]), np.asarray(out["grid_lat"])
                    )
                    masks = all_probe_wedge_masks(bag, grid)
                    out["track_wedge_masks"] = masks
                    masks_sha = _masks_sha(masks)
    return BuiltEval(result=out, context=EvalContext(items), wedge_masks_sha=masks_sha)


def _row_flags(metrics: dict[str, float]) -> list[str]:
    """Lift the pinned indicator metrics into visible row flags."""
    flags: list[str] = []
    if "wedge_exclusion" in metrics:
        flags.append(
            f"wedge_exclusion:{'true' if metrics['wedge_exclusion'] else 'false'}"
        )
    if any(k.endswith("_under_floor") for k in metrics):
        flags.append("under_floor")
    if any(k.endswith("_estimand_drifting_band") for k in metrics):
        flags.append("drifting_band")
    return flags


def build_report_rows(
    registry: Registry, result: dict[str, Any], context: EvalContext
) -> list[dict[str, Any]]:
    """One schema'd report row per APPLICABLE evaluator.

    An evaluator returning ``{}`` yields a VISIBLE skip row
    (``flags: ["no_usable_context"]``); evaluator guard raises PROPAGATE
    (a σ map reaching a mean-only evaluator crashes the run — pinned).

    Args:
        registry: The evaluator registry (usually :func:`default_registry`).
        result: The builder-enriched result payload.
        context: The builder-assembled context.

    Returns:
        Report rows in registry order.
    """
    masks = result.get("track_wedge_masks")
    masks_sha = _masks_sha(list(masks)) if masks is not None else None
    rows: list[dict[str, Any]] = []
    for ev in registry.applicable(context.keys()):
        spy = SpyItems(context.items)
        metrics = ev.evaluate(result, EvalContext(spy))  # guards propagate
        skipped = not metrics
        params: dict[str, Any] = {}
        if masks_sha is not None and ev.name in _MASK_CONSUMERS:
            params["wedge_masks_sha"] = masks_sha
        rows.append(
            {
                "schema_version": REPORT_SCHEMA_VERSION,
                "evaluator": ev.name,
                "evaluator_version": int(getattr(ev, "version", 1)),
                "metrics": metrics,
                "context_keys_available": sorted(k.name for k in context.keys()),
                "context_keys_used": (
                    [] if skipped else sorted(k.name for k in spy.reads)
                ),
                "params": params,
                "n_modes": {k: v for k, v in metrics.items() if "n_modes" in k},
                "flags": ["no_usable_context"] if skipped else _row_flags(metrics),
                "provenance": {"field_kind": result.get("field_kind")},
            }
        )
    return rows


_GEOMETRY_ARTIFACT_NAME = "phase11_orbit_geometry.json"


def report_only_instruments_block(mean_maps: Path | str) -> dict[str, Any]:
    """Reference-free report rows on a product's mean-map file (spec §7).

    The orbit-geometry artifact is expected BESIDE the maps file
    (``phase11_orbit_geometry.json``, the obligation-7 path); when absent,
    GroundTrack is simply not applicable — absence means absence, and the
    fidelity row's ``wedge_exclusion:false`` flag makes the degraded estimand
    visible (owner pin 1a). Report-only: never gate-bearing.

    Args:
        mean_maps: Product mean-map NetCDF (time, lat, lon ``ssh``) carrying
            the ``assimilated_missions`` attr.

    Returns:
        Evidence block with provenance shas and the report rows.
    """
    import xarray as xr

    mean_maps = Path(mean_maps)
    with xr.open_dataset(mean_maps) as ds:
        fields = np.asarray(ds["ssh"].values, dtype=float)
        lon = np.asarray(ds["lon"].values, dtype=float)
        lat = np.asarray(ds["lat"].values, dtype=float)
        missions = ds.attrs.get("assimilated_missions")
    geometry = mean_maps.parent / _GEOMETRY_ARTIFACT_NAME
    built = build_eval_context(
        {"fields": fields, "grid_lon": lon, "grid_lat": lat},
        field_kind="mean",
        geometry_artifact=geometry,
        assimilated_missions=missions if isinstance(missions, str) else None,
    )
    rows = build_report_rows(default_registry(), built.result, built.context)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "mean_maps": str(mean_maps),
        "mean_maps_sha256": hashlib.sha256(mean_maps.read_bytes()).hexdigest(),
        "geometry_artifact_sha256": (
            hashlib.sha256(geometry.read_bytes()).hexdigest()
            if geometry.exists()
            else None
        ),
        "wedge_masks_sha": built.wedge_masks_sha,
        "rows": rows,
    }


def evaluator_names(registry: Registry) -> list[str]:
    """Names of the registry's evaluators (test/reporting convenience)."""
    evaluators: list[Evaluator] = registry._evaluators  # noqa: SLF001
    return [e.name for e in evaluators]
