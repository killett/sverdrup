"""Build the Phase-8 jet-core cell mask and write it to JSON.

Pre-registered rule (spec §6):
  1. Load stage_b_mean_maps.nc; compute per-cell temporal std of ssh using
     the same proxy_cells rule as diag_phase8_covariate_alignment.py.
  2. Threshold at the 75th percentile (JET_CORE_QUANTILE) over all 25 cells.
  3. Retain only the largest 4-connected component (cross structure).
  4. Write a JSON artifact with the mask and provenance (sha256, quantile,
     rule, source_file) — NO build_date, which would break byte-identical reruns.

Usage::

    pixi run python scripts/build_phase8_jet_core_mask.py
"""

from __future__ import annotations

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

MEAN_NC = Path("data/2021a_ssh_mapping_ose/ours/stage_b_mean_maps.nc")
OUT_JSON = Path("data/2021a_ssh_mapping_ose/ours/phase8_jet_core_mask.json")


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
    """Compute the jet-core mask and provenance dict.

    Args:
        mean_nc: Path to stage_b_mean_maps.nc.

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


def main() -> None:
    """Build and write the jet-core mask JSON artifact."""
    if not MEAN_NC.exists():
        raise FileNotFoundError(
            f"Source file not found: {MEAN_NC}\n"
            "Run the Stage-B pipeline first to generate mean maps."
        )

    mask, provenance = build_mask(MEAN_NC)

    # Represent mask as a 5×5 list of lists (row-major, bool values)
    mask_list = mask.tolist()

    artifact = {
        "mask": mask_list,
        "provenance": provenance,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(artifact, sort_keys=True, indent=2) + "\n")

    n_jet = int(mask.sum())
    jet_cells = [(int(r), int(c)) for r, c in zip(*np.where(mask), strict=True)]
    print(f"Wrote {OUT_JSON}")
    print(f"Jet-core cells ({n_jet}/25): {jet_cells}")
    print("Mask (row=0 → lat∈[33,35), col=0 → lon∈[295,297)):")
    for row in mask:
        print("  " + "  ".join("X" if v else "." for v in row))


if __name__ == "__main__":
    main()
