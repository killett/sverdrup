"""Phase-11 retroactive one-shot (plan Task 7; spec §7).

Scores the shipped MIOST stage-B mean maps and the Phase-9 regenerated OI
mean maps with the rebuilt reference-free evaluators (GroundTrack +
SpectralFidelity) through the Task-6 wiring path, and records the numbers +
provenance at ``phase11.retro.*`` inside the standing evidence store
(nested-key atomic write, the ``phase10_compare`` pattern).

Zero c2: the orbit-geometry artifact derives from the ASSIMILATED-mission
union only; ``build_geometry_artifact`` refuses the id ``"c2"`` and the
withheld file is never opened. Provenance discipline: when a recorded input
sha exists in the evidence JSON, a mismatch REFUSES before any scoring;
absent shas are recorded as first anchors with a note.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
import xarray as xr

from sverdrup.application.eval_context import (
    build_eval_context,
    build_report_rows,
    default_registry,
)
from sverdrup.application.orbit_geometry import build_geometry_artifact
from sverdrup.eval.map_spectrum import PlaneGrid, power2d, radial_hann, ring_spectrum
from sverdrup.eval.phase11_constants import DERIVATION_VERSION

_OURS = Path("data/2021a_ssh_mapping_ose/ours")
_OBS_DIR = Path("data/2021a_ssh_mapping_ose/dc_obs")
_RESULTS = _OURS / "stage_miost_gate_results.json"
_GEOMETRY = _OURS / "phase11_orbit_geometry.json"
_PRODUCTS = {
    "miost": _OURS / "stage_b_mean_maps.nc",
    "oi": _OURS / "oi_mean_maps.nc",
}
_OI_SIGNED_ANCHOR = _OURS / "OSE_ssh_mapping_OURS_OI.nc"  # batch-2 pin 3


def _sha256(path: Path) -> str:
    """sha256 hex digest of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_evidence(results: Path, key_path: str, value: object) -> None:
    """Atomic nested-key write into the evidence store (phase10 pattern).

    Args:
        results: The evidence JSON path.
        key_path: Dot-separated key, e.g. ``"phase11.retro.miost.groundtrack"``.
        value: JSON-serializable value.
    """
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    evidence = json.loads(results.read_text()) if results.exists() else {}
    keys = key_path.split(".")
    node: dict[str, Any] = evidence
    for k in keys[:-1]:
        node = node.setdefault(k, {})
    node[keys[-1]] = value
    atomic_write_json(results, evidence)


def verify_or_anchor_inputs(
    evidence: dict[str, Any], inputs: dict[str, Path]
) -> tuple[dict[str, str], dict[str, str]]:
    """Check every input against its recorded sha BEFORE any scoring.

    Args:
        evidence: The full evidence store contents.
        inputs: ``{name: path}`` of input files to verify.

    Returns:
        ``(shas, notes)`` — actual sha256 per input and a per-input note
        (``"verified against recorded anchor"`` or the first-anchor note).

    Raises:
        ValueError: On any recorded-vs-actual mismatch (refusal-before-scoring).
    """
    recorded = (
        evidence.get("phase11", {})
        .get("retro", {})
        .get("provenance", {})
        .get("input_sha256", {})
    )
    shas: dict[str, str] = {}
    notes: dict[str, str] = {}
    for name, path in inputs.items():
        actual = _sha256(path)
        prior = recorded.get(name)
        if prior is not None and prior != actual:
            raise ValueError(
                f"input sha mismatch for {name!r}: recorded {prior[:12]}… but "
                f"{path} hashes to {actual[:12]}… — refusing before scoring"
            )
        shas[name] = actual
        notes[name] = (
            "verified against recorded anchor"
            if prior is not None
            else "first anchor — recorded now, verified on future runs"
        )
    return shas, notes


def mission_union(mission_attrs: list[str]) -> list[str]:
    """Sorted union of space-separated mission attrs; refuses ``c2``.

    Args:
        mission_attrs: One ``assimilated_missions`` attr string per product.

    Returns:
        Sorted mission ids.

    Raises:
        ValueError: If the withheld ``c2`` id appears anywhere.
    """
    union: set[str] = set()
    for attr in mission_attrs:
        union |= set(attr.split())
    if "c2" in union:
        raise ValueError(
            "mission 'c2' in an assimilated_missions attr — the withheld "
            "Cryosat-2 track never enters the geometry union (zero-c2)"
        )
    return sorted(union)


def build_product_block(mean_maps: Path, geometry_artifact: Path) -> dict[str, Any]:
    """Score one product's mean maps; return the retro evidence block.

    Args:
        mean_maps: Product mean-map NetCDF (``ssh`` on time/lat/lon, with the
            ``assimilated_missions`` attr).
        geometry_artifact: The Task-1 orbit-geometry artifact path.

    Returns:
        ``{groundtrack: row, spectral_fidelity: row, n_modes_per_ring: table,
        n_days: int}`` — rows from the Task-6 builder path; the per-ring
        n_modes table is script-side via the shared prep (evaluator metrics
        stay flat).
    """
    with xr.open_dataset(mean_maps) as ds:
        fields = np.asarray(ds["ssh"].values, dtype=float)
        lon = np.asarray(ds["lon"].values, dtype=float)
        lat = np.asarray(ds["lat"].values, dtype=float)
        missions_attr = str(ds.attrs["assimilated_missions"])
    built = build_eval_context(
        {"fields": fields, "grid_lon": lon, "grid_lat": lat},
        field_kind="mean",
        geometry_artifact=geometry_artifact,
        assimilated_missions=missions_attr,
    )
    rows = build_report_rows(default_registry(), built.result, built.context)
    by_name = {r["evaluator"]: r for r in rows}
    # script-side full per-ring n_modes table (shared prep, day-0 field —
    # ring geometry is grid-fixed)
    grid = PlaneGrid.from_deg(lon, lat)
    power, kx, ky = power2d(fields[0], radial_hann(grid), grid)
    exclude = built.result.get("track_wedge_masks", [])
    k, _e, n_modes = ring_spectrum(power, kx, ky, dk=1.0 / grid.lx_km, exclude=exclude)
    return {
        "groundtrack": by_name["groundtrack"],
        "spectral_fidelity": by_name["spectral_fidelity"],
        "n_modes_per_ring": {
            "ring": [int(round(c * grid.lx_km)) for c in k],
            "k_cyc_per_km": [float(c) for c in k],
            "n_modes": [int(n) for n in n_modes],
            "note": "after track-wedge exclusion; ring width = 1/Lx (FFT)",
        },
        "n_days": int(fields.shape[0]),
    }


def _fmt_track_line(row: dict[str, Any]) -> str:
    """Format the groundtrack headline fragment from a row's metrics."""
    metrics = row["metrics"]
    parts = []
    for cls in ("repeat", "drifting"):
        key = f"track_excess_log10_max_{cls}"
        if key not in metrics:
            parts.append(f"max {cls}=n/a")
            continue
        val = metrics[key]
        arg = min(
            (
                k
                for k, v in metrics.items()
                if k.startswith("track_excess_log10_")
                and not k.startswith("track_excess_log10_max")
                and "_n_" not in k
                and not k.endswith(("_under_floor", "_estimand_drifting_band"))
                and v == val
            ),
            default="?",
        )
        label = arg.removeprefix("track_excess_log10_").replace("_", "/")
        parts.append(f"max {cls}={val:.3f} ({label})")
    return ", ".join(parts)


def _fmt_fidelity_line(row: dict[str, Any]) -> str:
    """Format the fidelity headline fragment from a row's metrics."""
    m = row["metrics"]
    return (
        f"spec_slope={m['spec_slope']:.2f} (WLS SE {m['spec_slope_wls_se']:.2f}, "
        f"day IQR {m['spec_slope_day_iqr']:.2f})"
    )


def main() -> None:
    """Run the one-shot: verify inputs, derive geometry, score, record."""
    evidence = (
        cast(dict[str, Any], json.loads(_RESULTS.read_text()))
        if _RESULTS.exists()
        else {}
    )
    inputs = dict(_PRODUCTS) | {"oi_signed_anchor": _OI_SIGNED_ANCHOR}
    shas, notes = verify_or_anchor_inputs(evidence, inputs)

    attrs = []
    for path in _PRODUCTS.values():
        with xr.open_dataset(path) as ds:
            attrs.append(str(ds.attrs["assimilated_missions"]))
    missions = mission_union(attrs)
    print(f"[retro] assimilated union: {missions} (c2 refused by construction)")
    geometry_sha = build_geometry_artifact(_OBS_DIR, missions, 38.1, _GEOMETRY)
    print(f"[retro] geometry artifact sha256 {geometry_sha[:12]}… at {_GEOMETRY}")

    blocks = {
        name: build_product_block(path, _GEOMETRY) for name, path in _PRODUCTS.items()
    }
    for name, block in blocks.items():
        write_evidence(_RESULTS, f"phase11.retro.{name}", block)
    write_evidence(
        _RESULTS,
        "phase11.retro.provenance",
        {
            "input_sha256": shas,
            "input_notes": notes,
            "geometry_artifact_sha256": geometry_sha,
            "derivation_version": DERIVATION_VERSION,
            "missions": missions,
            "written_utc": datetime.now(UTC).isoformat(),
        },
    )

    date = datetime.now(UTC).date().isoformat()
    lo, hi = 100, 219
    print()
    print(
        f"PHASE-11 RETRO NUMBERS ({date}, evidence phase11.retro.*, "
        f"geometry sha {geometry_sha[:12]}):"
    )
    labels = {"miost": "MIOST stage-B means", "oi": "OI regenerated means"}
    for name, block in blocks.items():
        print(
            f"- {labels[name]}: track_excess_log10 "
            f"{_fmt_track_line(block['groundtrack'])}; "
            f"{_fmt_fidelity_line(block['spectral_fidelity'])}, "
            f"band [{lo}, {hi}] km"
        )


if __name__ == "__main__":
    main()
