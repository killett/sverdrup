r"""Generalised jet-core cell mask builder for any product's mean maps.

Pre-registered rule (same as build_phase8_jet_core_mask.py, spec §6):
  1. Load <mean_nc>; compute per-cell temporal std of ssh using proxy_cells.
  2. Threshold at the 75th percentile (JET_CORE_QUANTILE) over all 25 cells.
  3. Retain only the largest 4-connected component (cross structure).
  4. Write a JSON artifact with the mask and provenance (sha256, quantile,
     rule, source_file) — NO build_date, which would break byte-identical reruns.

This script generalises build_phase8_jet_core_mask.py; the phase8 script
and its artifact stay untouched.

Determinism guarantee: two runs on the same input file produce byte-identical
output (no timestamps or random state in the artifact).

Reproduces phase8 mask cells [(2,1),(2,2),(3,0),(3,1),(3,2),(3,3),(3,4)] when
run on stage_b_mean_maps.nc — same rule constants from the constants package.

Usage::

    pixi run python scripts/build_jet_core_mask.py \\
        --mean-maps data/2021a_ssh_mapping_ose/ours/stage_b_mean_maps.nc \\
        --out data/2021a_ssh_mapping_ose/ours/phase9_jet_core_mask_miost.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import xarray as xr

from sverdrup.application.calibration.constants import JET_CORE_QUANTILE
from sverdrup.application.calibration.regions import (
    largest_4connected_component,
    proxy_cells,
)


def sha256_file(path: Path) -> str:
    """Return hex sha256 digest of a file.

    Args:
        path: File to hash.

    Returns:
        Lowercase hex SHA-256 string.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_mask(mean_nc: Path) -> tuple[np.ndarray, dict[str, object]]:
    """Compute the jet-core mask and provenance dict for any product mean maps.

    Same rule as build_phase8_jet_core_mask.build_mask — extracted here so
    this script can be called on any product (MIOST, OI, …).

    Args:
        mean_nc: Path to the product mean maps NetCDF.

    Returns:
        Tuple of (mask_5x5, provenance_dict) where mask_5x5 is a (5,5) bool
        array and provenance_dict carries sha256, quantile, rule, source_file.
    """
    digest = sha256_file(mean_nc)
    mean_ds = xr.open_dataset(mean_nc)
    proxy = proxy_cells(mean_ds)
    mean_ds.close()

    # Flat values for percentile (default linear interpolation — must match
    # provenance rule string).
    flat = proxy.ravel()
    threshold = float(np.quantile(flat, JET_CORE_QUANTILE, method="linear"))

    above = proxy >= threshold  # (5,5) bool
    mask = largest_4connected_component(above)  # (5,5) bool, largest component

    provenance: dict[str, object] = {
        "source_file": str(mean_nc),
        "sha256": digest,
        "quantile": JET_CORE_QUANTILE,
        "quantile_method": "linear",
        "threshold": threshold,
        "rule": (
            "per-cell temporal std >= np.quantile(all_cells, 0.75, method='linear'), "
            "then largest 4-connected component "
            "(scipy.ndimage.label structure=[[0,1,0],[1,1,1],[0,1,0]])"
        ),
    }
    return mask, provenance


def write_mask(mask: np.ndarray, provenance: dict[str, object], out: Path) -> None:
    """Write the mask and provenance to a JSON artifact.

    Byte-identical on repeated runs: no build_date, sort_keys=True, trailing
    newline matches build_phase8_jet_core_mask.py.

    Args:
        mask: (5,5) bool ndarray.
        provenance: Provenance dict (sha256, quantile, rule, source_file).
        out: Destination path.
    """
    mask_list = mask.tolist()
    artifact = {
        "mask": mask_list,
        "provenance": provenance,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, sort_keys=True, indent=2) + "\n")


def main() -> None:
    """Build and write the jet-core mask JSON artifact for a given product."""
    parser = argparse.ArgumentParser(
        description="Build a jet-core cell mask from product mean maps."
    )
    parser.add_argument(
        "--mean-maps",
        required=True,
        type=Path,
        help="Path to product mean maps NetCDF (stage_b_mean_maps.nc or equivalent).",
    )
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output JSON path for the mask artifact.",
    )
    args = parser.parse_args()

    mean_nc: Path = args.mean_maps
    out: Path = args.out

    if not mean_nc.exists():
        raise FileNotFoundError(
            f"Source file not found: {mean_nc}\n"
            "Ensure the product mean maps exist before running this script."
        )

    mask, provenance = build_mask(mean_nc)
    write_mask(mask, provenance, out)

    n_jet = int(mask.sum())
    jet_cells = [(int(r), int(c)) for r, c in zip(*np.where(mask), strict=True)]
    print(f"Wrote {out}")
    print(f"Jet-core cells ({n_jet}/25): {jet_cells}")
    print("Mask (row=0 → lat∈[33,35), col=0 → lon∈[295,297)):")
    for row in mask:
        print("  " + "  ".join("X" if v else "." for v in row))


if __name__ == "__main__":
    main()
