"""Tier-3 similarity diagnostic: our MIOST map vs the pinned CLS OSE_ssh_mapping_MIOST.nc.

DIAGNOSTIC — NEVER A GATE (Stage-A validation strategy, owner-decided 2026-07-03):
pointwise reproduction of the distributed MIOST maps is impossible IN PRINCIPLE
(undocumented config, no public code). This tool reports RMS difference and
along-longitude spectral coherence as CONTEXT for the Task-13 evidence pack.

Usage:
    pixi run python scripts/diag_miost_tier3.py [OURS.nc]
    (default OURS = data/2021a_ssh_mapping_ose/ours/stage_miost_acceptance.nc)

Output: docs/validation/miost_tier3_similarity.md
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import xarray as xr
from scipy import signal  # type: ignore[import-untyped]

THEIRS = Path("data/2021a_ssh_mapping_ose/dc_maps/OSE_ssh_mapping_MIOST.nc")
OURS_DEFAULT = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_acceptance.nc")
DOC = Path("docs/validation/miost_tier3_similarity.md")
BANNER = "DIAGNOSTIC — never a gate (Tier 3; similarity is context, not a criterion)"
LAT_BAND = (37.0, 39.0)  # mid-lat band for the along-lon coherence
KM_PER_DEG = 111.32
WAVELENGTHS_KM = (100.0, 150.0, 200.0, 300.0, 500.0)


def main() -> None:
    """Compare the two maps; print + write the report."""
    print(BANNER, flush=True)
    ours_path = Path(sys.argv[1]) if len(sys.argv) > 1 else OURS_DEFAULT
    ours = xr.open_dataset(ours_path)
    theirs = xr.open_dataset(THEIRS)

    # Align: inner-join times; regrid OURS onto THEIR (finer) grid if they differ.
    common = np.intersect1d(ours["time"].values, theirs["time"].values)
    ours = ours.sel(time=common)
    theirs = theirs.sel(time=common)
    regridded = False
    if (ours.sizes["lat"], ours.sizes["lon"]) != (
        theirs.sizes["lat"],
        theirs.sizes["lon"],
    ):
        ours = ours.interp(lat=theirs["lat"], lon=theirs["lon"], method="linear")
        regridded = True

    a = np.asarray(ours["ssh"], float)
    b = np.asarray(theirs["ssh"], float)
    finite = np.isfinite(a) & np.isfinite(b)
    diff = np.where(finite, a - b, np.nan)
    rms_day = np.sqrt(np.nanmean(diff**2, axis=(1, 2)))
    rms_mean = float(np.sqrt(np.nanmean(diff**2)))
    their_std = float(np.nanstd(b))

    # Along-lon spectral coherence in the mid-lat band, averaged over days/rows.
    lat = np.asarray(theirs["lat"], float)
    band = (lat >= LAT_BAND[0]) & (lat <= LAT_BAND[1])
    dx_km = (
        float(np.diff(np.asarray(theirs["lon"], float)).mean())
        * KM_PER_DEG
        * math.cos(math.radians(0.5 * (LAT_BAND[0] + LAT_BAND[1])))
    )
    cxy_sum: np.ndarray | None = None
    n_rows = 0
    for it in range(0, a.shape[0], max(1, a.shape[0] // 60)):  # ~60 sampled days
        for il in np.nonzero(band)[0]:
            ra, rb = a[it, il, :], b[it, il, :]
            ok = np.isfinite(ra) & np.isfinite(rb)
            if ok.sum() < 64:
                continue
            f, cxy = signal.coherence(
                ra[ok] - ra[ok].mean(),
                rb[ok] - rb[ok].mean(),
                fs=1.0 / dx_km,
                nperseg=64,
            )
            cxy_sum = cxy if cxy_sum is None else cxy_sum + cxy
            n_rows += 1
    if cxy_sum is None or n_rows == 0:
        raise RuntimeError("no finite mid-lat rows to compare")
    cxy_mean = cxy_sum / n_rows
    wavelength = np.where(f > 0, 1.0 / np.maximum(f, 1e-12), np.inf)

    def _coh_at(lam_km: float) -> float:
        return float(np.interp(lam_km, wavelength[::-1], cxy_mean[::-1]))

    half_idx = np.nonzero(cxy_mean >= 0.5)[0]
    lam_half = float(wavelength[half_idx[-1]]) if half_idx.size else float("inf")

    lines = [
        "# MIOST Tier-3 similarity vs the pinned CLS maps",
        "",
        f"**{BANNER}**",
        "",
        f"- Ours: `{ours_path}`; theirs: `{THEIRS}` (SHA256-pinned in the 2021a manifest).",
        f"- Common days: {len(common)}; ours regridded to their 0.1-deg grid: {regridded}.",
        "",
        "## RMS difference [m]",
        "",
        f"- mean over all days: **{rms_mean:.4f}** (their field std {their_std:.3f})",
        f"- per-day: median {float(np.median(rms_day)):.4f}, p95 "
        f"{float(np.percentile(rms_day, 95)):.4f}, max {float(rms_day.max()):.4f} "
        f"(day index {int(np.argmax(rms_day))})",
        "",
        f"## Along-lon spectral coherence (lat {LAT_BAND[0]}-{LAT_BAND[1]}, "
        f"{n_rows} sampled rows)",
        "",
        "| wavelength [km] | coherence |",
        "|---|---|",
    ]
    lines += [f"| {w:.0f} | {_coh_at(w):.3f} |" for w in WAVELENGTHS_KM]
    lines += [
        "",
        f"Coherence-0.5 crossing: ~{lam_half:.0f} km.",
        "",
    ]
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
