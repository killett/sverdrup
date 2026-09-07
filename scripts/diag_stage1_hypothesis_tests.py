"""Stage-1 mechanism tests: which hypothesis predicts the skill loss?

Read-only over the persisted maps and tracks — no solve, no write, no
evidence touched.

Four candidates are on the table for why equatorial's λx is UNRESOLVED
(owner pins 177, 181):

1. **f** — geostrophic degeneracy as the Coriolis parameter vanishes.
2. **ratio-SNR** — skill keyed to signal strength relative to a tile's own
   scale.
3. **absolute noise floor** — skill keyed to absolute band variance against
   a fixed instrument floor (pin 181, promoted to first-class).
4. **long-scale dominance** — the solution's power concentrated in the
   longest basis rung, leaking into shorter bands (pin 175).

What this reports:

* **181(c)** fine-band track spectra for every tile, plus each band's ratio
  to the band above it. A ratio above 1 marks where a spectrum stops
  falling and a floor takes over. A COMMON floor predicts the rise appears
  at tile-specific wavelengths (wherever each signal drops through it) and
  converges to ONE level.
* **181(a)** per-band skill against per-band ABSOLUTE variance, with |f| as
  the competing predictor — the sharpest discriminator between 2 and 3.
* **177(a)/(b)** the sign check and the magnitude check.

Usage::

    pixi run python scripts/diag_stage1_hypothesis_tests.py
"""

from __future__ import annotations

import importlib.util
import math
import pathlib
import tempfile
from types import ModuleType
from typing import Any

import numpy as np
import xarray as xr

TILES = ("kuroshio", "southern", "equatorial", "quiet_gyre")
# ~1000 km at the vendored along-track sampling: the production segment.
SEG = 156
# Mid-tile Coriolis parameter [s^-1], the competing predictor in 181(a).
CORIOLIS = {
    "kuroshio": 8.32e-5,
    "southern": 1.19e-4,
    "equatorial": 5.3e-6,
    "quiet_gyre": 5.5e-5,
}
FINE_BANDS = [
    (400, 1000),
    (250, 400),
    (180, 250),
    (130, 180),
    (95, 130),
    (70, 95),
    (50, 70),
    (35, 50),
    (25, 35),
    (13, 25),
]
SKILL_BANDS = FINE_BANDS[:7]


def _stage1_module() -> ModuleType:
    """Load the Stage-1 runner as a module (it is a script, not a package)."""
    spec = importlib.util.spec_from_file_location(
        "phase14_stage1_run", pathlib.Path(__file__).with_name("phase14_stage1_run.py")
    )
    if spec is None or spec.loader is None:  # pragma: no cover - import plumbing
        raise RuntimeError("cannot load phase14_stage1_run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _band_sum(wl: np.ndarray, values: np.ndarray, lo: float, hi: float) -> float:
    """Sum ``values`` over the wavelength band ``[lo, hi]`` km."""
    sel = (wl >= lo) & (wl <= hi) & np.isfinite(wl)
    return float(np.nansum(values[sel])) if sel.any() else float("nan")


def track_spectrum(tile: str) -> dict[str, Any] | None:
    """The tile's own along-track spectrum — no map involved (pin 181c).

    Args:
        tile: Tile name.

    Returns:
        Wavelengths and PSD, or None when the track is absent.
    """
    from sverdrup.eval.spectral import _DELTA_X  # noqa: PLC0415
    from sverdrup.validation.pertile_scoring import (  # noqa: PLC0415
        extract_core_track,
    )

    mod = _stage1_module()
    track = mod.STAGE1_DIR / f"dt_{tile}_j3_phy_l3_2017_stage1.nc"
    if not track.exists():
        return None
    frame, _grid, _framed, _cfg = mod._tile_framed_obs(tile)  # noqa: SLF001
    ds = extract_core_track(
        frame, track, mod.VALIDATION_TIME_MIN, mod.VALIDATION_TIME_MAX
    )
    ssh = np.asarray(ds["sla_unfiltered"].to_numpy(), dtype="float64")
    for name, sign in (("mdt", 1.0), ("lwe", -1.0)):
        if name in ds:
            ssh = ssh + sign * np.asarray(ds[name].to_numpy(), dtype="float64")
    ssh = ssh[np.isfinite(ssh)]

    window = np.hanning(SEG)
    norm = float((window**2).mean())
    ramp = np.arange(SEG, dtype="float64")
    acc = np.zeros(SEG // 2 + 1)
    used = 0
    for i in range(ssh.size // SEG):
        seg = ssh[i * SEG : (i + 1) * SEG]
        if not np.all(np.isfinite(seg)):
            continue
        seg = seg - np.polyval(np.polyfit(ramp, seg, 1), ramp)
        acc += np.abs(np.fft.rfft(seg * window)) ** 2 / (SEG * norm)
        used += 1
    wavenumber = np.fft.rfftfreq(SEG, d=_DELTA_X)
    positive = wavenumber > 0
    return {
        "tile": tile,
        "wl": np.where(positive, 1.0 / np.where(positive, wavenumber, np.nan), np.inf),
        "psd": acc / max(used, 1),
        "n": int(ssh.size),
        "n_segments": used,
    }


def skill_spectrum(tile: str) -> dict[str, Any] | None:
    """psd_ref / psd_study / psd_diff through the scorer's own path.

    Args:
        tile: Tile name.

    Returns:
        Wavelengths and the three PSDs, or None when map or track is absent.
    """
    from sverdrup.eval.spectral import (  # noqa: PLC0415
        _DELTA_T,
        _DELTA_X,
        _LENGTH_SCALE,
        _ensure_vendor_importable,
    )
    from sverdrup.validation.pertile_scoring import (  # noqa: PLC0415
        extract_core_track,
    )
    from sverdrup.validation.vendor import (  # noqa: PLC0415
        prepare_vendored_imports,
    )

    mod = _stage1_module()
    mean_map = mod.tile_mean_map(tile)
    track = mod.STAGE1_DIR / f"dt_{tile}_j3_phy_l3_2017_stage1.nc"
    if not (mean_map.exists() and track.exists()):
        return None
    frame, _grid, _framed, _cfg = mod._tile_framed_obs(tile)  # noqa: SLF001
    ds_track = extract_core_track(
        frame, track, mod.VALIDATION_TIME_MIN, mod.VALIDATION_TIME_MAX
    )
    prepare_vendored_imports()
    _ensure_vendor_importable()
    from src.mod_interp import interp_on_alongtrack  # noqa: PLC0415
    from src.mod_spectral import compute_spectral_scores  # noqa: PLC0415

    time_a, lat_a, lon_a, ssh_a, ssh_map = interp_on_alongtrack(
        str(mean_map),
        ds_track,
        lon_min=frame.core.lon_min,
        lon_max=frame.core.lon_max,
        lat_min=frame.core.lat_min,
        lat_max=frame.core.lat_max,
        time_min=mod.VALIDATION_TIME_MIN,
        time_max=mod.VALIDATION_TIME_MAX,
        is_circle=False,
    )
    with tempfile.TemporaryDirectory() as td:
        psd_file = pathlib.Path(td) / "psd.nc"
        compute_spectral_scores(
            np.asarray(time_a),
            np.asarray(lat_a),
            np.asarray(lon_a),
            np.asarray(ssh_a, dtype="float64"),
            np.asarray(ssh_map, dtype="float64"),
            _LENGTH_SCALE,
            _DELTA_X,
            _DELTA_T,
            str(psd_file),
        )
        with xr.open_dataset(str(psd_file)) as ds:
            wavenumber = np.asarray(ds.wavenumber.to_numpy(), dtype="float64")
            positive = wavenumber > 0
            return {
                "tile": tile,
                "wl": np.where(
                    positive, 1.0 / np.where(positive, wavenumber, np.nan), np.inf
                ),
                "ref": np.asarray(ds.psd_ref.to_numpy(), dtype="float64"),
                "study": np.asarray(ds.psd_study.to_numpy(), dtype="float64"),
                "diff": np.asarray(ds.psd_diff.to_numpy(), dtype="float64"),
            }


def main() -> None:
    """Print the 181(c) floor test and the 181(a) predictor comparison."""
    tracks = [r for r in (track_spectrum(t) for t in TILES) if r is not None]
    print(
        "=== 181(c): fine-band TRACK PSD (m^2 km) — where does each tile flatten? ==="
    )
    print(f"{'band km':<12}" + "".join(f"{r['tile']:>13}" for r in tracks))
    for lo, hi in FINE_BANDS:
        line = f"{lo:>4}-{hi:<7}"
        for r in tracks:
            line += f"{_band_sum(r['wl'], r['psd'], lo, hi):>13.3e}"
        print(line)

    print("\n  ratio to the band above (>1 = spectrum RISING = floor reached)")
    print(f"{'band km':<12}" + "".join(f"{r['tile']:>13}" for r in tracks))
    previous: dict[str, float | None] = {r["tile"]: None for r in tracks}
    for lo, hi in FINE_BANDS:
        line = f"{lo:>4}-{hi:<7}"
        for r in tracks:
            value = _band_sum(r["wl"], r["psd"], lo, hi)
            prior = previous[r["tile"]]
            ratio = value / prior if prior and prior > 0 else float("nan")
            line += f"{ratio:>13.2f}"
            previous[r["tile"]] = value
        print(line)

    skills = [r for r in (skill_spectrum(t) for t in TILES) if r is not None]
    print("\n=== 181(a): skill vs ABSOLUTE band variance ===")
    print(
        f"{'tile':<12}{'band km':<12}{'abs var m2':>12}{'diff/ref':>10}{'study/ref':>11}"
    )
    pairs: list[tuple[str, float, float]] = []
    for r in skills:
        for lo, hi in SKILL_BANDS:
            ref = _band_sum(r["wl"], r["ref"], lo, hi)
            if not (ref > 0):
                continue
            diff_ratio = _band_sum(r["wl"], r["diff"], lo, hi) / ref
            study_ratio = _band_sum(r["wl"], r["study"], lo, hi) / ref
            pairs.append((r["tile"], ref, diff_ratio))
            print(
                f"{r['tile']:<12}{f'{lo}-{hi}':<12}{ref:>12.3e}"
                f"{diff_ratio:>10.3f}{study_ratio:>11.3f}"
            )

    if len(pairs) > 2:
        log_var = np.array([math.log10(p[1]) for p in pairs])
        loss = np.array([p[2] for p in pairs])
        log_f = np.array([math.log10(CORIOLIS[p[0]]) for p in pairs])
        print("\n=== which predictor tracks the skill loss? ===")
        print(
            f"corr( log10 absolute band variance , diff/ref ) = "
            f"{float(np.corrcoef(log_var, loss)[0, 1]):+.3f}   (n={log_var.size})"
        )
        print(
            f"corr( log10 |f| , diff/ref )                    = "
            f"{float(np.corrcoef(log_f, loss)[0, 1]):+.3f}"
        )


if __name__ == "__main__":
    main()
