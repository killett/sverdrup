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

⛔ **IT USED TO WRITE NOTHING** (owner pin 201b). Every band number that
reached the record — the numbers the THREE-CLASS finding rests on — passed
through prose, because this script printed and exited. Running it again
without fixing that would repeat the defect. It now writes a JSON artifact
into the tree and, with ``--record``, the same tables into the evidence
store, where the mirror witnesses them (201d). **The tables are a
MEASUREMENT and belong in the store; the three-class READING is an
interpretation and stays in the pack** (pin 197b).

⭐ **:data:`SKILL_BANDS` IS THE CANONICAL GRID** (owner pin 205c). A future
quote either comes from this grid or states its own cut explicitly in the
same artifact. *A number quoted from a cut nobody can reproduce is the
prose-only failure wearing a decimal point.*

:data:`RULING_QUOTED` verifies, band by band, the figures the rulings
already quote — including southern's **500–1000 km**, which is NOT on the
canonical grid and whose provenance is exactly the finding at 205(b).
**Any disagreement STOPS** (205d): the three classes rest on these numbers.

Usage::

    pixi run python scripts/diag_stage1_hypothesis_tests.py
    pixi run python scripts/diag_stage1_hypothesis_tests.py --record
"""

from __future__ import annotations

import importlib.util
import json
import math
import pathlib
import tempfile
from types import ModuleType
from typing import Annotated, Any

import numpy as np
import typer
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

# Owner pin 201(b): the artifact this script used to not write.
ARTIFACT = pathlib.Path("docs/validation/phase14-stage1-band-tables.json")
STORE_NODE = "band_spectra"

# Owner pin 201(c)/205(a): the figures the rulings already quote, verified
# band by band against this recomputation. The (500, 1000) cut is NOT on the
# canonical grid — see UNRECORDED_CUT below, which is 205(b)'s finding.
RULING_QUOTED: tuple[dict[str, Any], ...] = (
    {
        "tile": "kuroshio",
        "band": (70, 95),
        "study_ref": 3.823,
        "diff_ref": 4.697,
        "source": "owner pin 181; PROGRESS pathological-band table",
        "on_canonical_grid": True,
    },
    {
        "tile": "equatorial",
        "band": (250, 400),
        "study_ref": 4.291,
        "diff_ref": 5.169,
        "source": "owner pin 181; PROGRESS pathological-band table",
        "on_canonical_grid": True,
    },
    {
        "tile": "quiet_gyre",
        "band": (400, 1000),
        "study_ref": 9.804,
        "diff_ref": 9.959,
        "source": "owner pin 201(c)",
        "on_canonical_grid": True,
    },
    {
        "tile": "southern",
        "band": (500, 1000),
        "study_ref": 0.084,
        "diff_ref": 0.988,
        "source": "owner pins 172/196(b) — the UNDER-powered class",
        "on_canonical_grid": False,
    },
)

UNRECORDED_CUT = (
    "⛔ FINDING (owner pin 205b), one level deeper than 201's defect: southern's "
    "0.084 / 0.988 are quoted at 500-1000 km, a cut that is NOT on the canonical "
    "grid (SKILL_BANDS carries 400-1000) and that no committed code produces. The "
    "figures came from an unrecorded ad-hoc band cut, so until this artifact existed "
    "a quoted number that the UNDER-powered class rests on had no reproducible band "
    "definition behind it. It is recomputed here from its explicit cut and verified; "
    "the finding is that it needed one."
)


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


def _agrees(computed: float, quoted: float) -> bool:
    """Whether ``computed`` matches ``quoted`` AT THE QUOTED PRECISION.

    The rulings quote three decimals; comparing at that precision is the
    honest test — a looser tolerance would pass numbers the record does
    not actually contain, and a tighter one would fail on the rounding
    the quote itself performed.

    Args:
        computed: The recomputed value.
        quoted: The value as it appears in the ruling.

    Returns:
        True when the two agree at the quoted number of decimals.
    """
    text = f"{quoted}"
    ndigits = len(text.split(".")[1]) if "." in text else 0
    return round(computed, ndigits) == quoted


def _band_ratios(skill: dict[str, Any], lo: float, hi: float) -> dict[str, float]:
    """``ref``/``study_ref``/``diff_ref`` for one tile over one band.

    Args:
        skill: A :func:`skill_spectrum` result.
        lo: Band lower wavelength [km].
        hi: Band upper wavelength [km].

    Returns:
        The absolute reference variance and the two ratios (NaN-free only
        where ``ref`` is positive; otherwise the ratios are NaN).
    """
    ref = _band_sum(skill["wl"], skill["ref"], lo, hi)
    if not ref > 0:
        return {"ref": ref, "study_ref": float("nan"), "diff_ref": float("nan")}
    return {
        "ref": ref,
        "study_ref": _band_sum(skill["wl"], skill["study"], lo, hi) / ref,
        "diff_ref": _band_sum(skill["wl"], skill["diff"], lo, hi) / ref,
    }


def verify_ruling_quotes(skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Recompute every figure the rulings quote and compare (pins 201c/205a).

    Includes southern's 500–1000 km cut, which is NOT on the canonical
    grid — reproducing it from its explicit cut is the whole point, and
    that it needed one is the finding at 205(b).

    Args:
        skills: :func:`skill_spectrum` results, one per tile.

    Returns:
        One verdict row per quoted figure, each carrying the quoted and
        the recomputed value and an ``agrees`` flag per field.
    """
    by_tile = {r["tile"]: r for r in skills}
    verdicts: list[dict[str, Any]] = []
    for quote in RULING_QUOTED:
        skill = by_tile.get(str(quote["tile"]))
        lo, hi = quote["band"]
        if skill is None:
            verdicts.append({**quote, "computed": None, "agrees": False})
            continue
        got = _band_ratios(skill, float(lo), float(hi))
        checks = {
            field: _agrees(got[field], float(quote[field]))
            for field in ("study_ref", "diff_ref")
            if field in quote
        }
        verdicts.append(
            {
                "tile": quote["tile"],
                "band_km": [lo, hi],
                "on_canonical_grid": quote["on_canonical_grid"],
                "source": quote["source"],
                "quoted": {
                    f: quote[f] for f in ("study_ref", "diff_ref") if f in quote
                },
                "computed": {f: got[f] for f in ("study_ref", "diff_ref")},
                "per_field_agrees": checks,
                "agrees": all(checks.values()),
            }
        )
    return verdicts


def build_payload(
    tracks: list[dict[str, Any]], skills: list[dict[str, Any]]
) -> dict[str, Any]:
    """Assemble the recorded artifact — the tables, not a reading of them.

    Args:
        tracks: :func:`track_spectrum` results.
        skills: :func:`skill_spectrum` results.

    Returns:
        The artifact payload, identical in the tree file and the store node.
    """
    verdicts = verify_ruling_quotes(skills)
    return {
        "label": "STAGE1-EVIDENCE",
        "kind": (
            "MEASUREMENT — read-only recomputation from the PERSISTED maps and "
            "tracks through the scorer's own path. No solve, no re-run, no "
            "recorded value changed (owner pin 201a; same class as pin 114's "
            "post-hoc recovery)"
        ),
        "pin": "201 (a)-(d), 205 (a)-(d)",
        "produced_by": "scripts/diag_stage1_hypothesis_tests.py",
        "canonical_grid_km": [list(b) for b in SKILL_BANDS],
        "canonical_grid_rule": (
            "owner pin 205(c): SKILL_BANDS is CANONICAL. A future quote comes from "
            "this grid or states its own cut explicitly in this same artifact. A "
            "number quoted from a cut nobody can reproduce is the prose-only "
            "failure wearing a decimal point"
        ),
        "not_an_interpretation": (
            "owner pin 197(b): these are measurements and belong in the store. The "
            "THREE-CLASS reading built on them is an interpretation and stays in "
            "the pack — the store holds measurements and firewalled hypotheses"
        ),
        "naming_hazard_pin_178": (
            "the vendored quantity called `coherence` elsewhere is 1 - "
            "psd_diff/psd_ref = 2*sqrt(r)*Re(gamma) - r and is NOT a coherence. "
            "The ratios here are the raw PSD ratios and carry no such relabelling"
        ),
        "unrecorded_cut_finding": UNRECORDED_CUT,
        "track_psd_m2km": {
            r["tile"]: {
                f"{lo}-{hi}": _band_sum(r["wl"], r["psd"], lo, hi)
                for lo, hi in FINE_BANDS
            }
            for r in tracks
        },
        "track_segments": {r["tile"]: r["n_segments"] for r in tracks},
        "skill_by_band": {
            r["tile"]: {f"{lo}-{hi}": _band_ratios(r, lo, hi) for lo, hi in SKILL_BANDS}
            for r in skills
        },
        "ruling_quote_verification": verdicts,
        "all_ruling_quotes_reproduced": all(v["agrees"] for v in verdicts),
    }


def _record(payload: dict[str, Any]) -> None:
    """Write the payload to the evidence store — seal-gated, like every writer.

    Args:
        payload: :func:`build_payload` output.
    """
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )
    from sverdrup.validation import phase14_seal  # noqa: PLC0415

    mod = _stage1_module()
    phase14_seal.verify_current_seal()
    evidence = mod.EVIDENCE
    results: dict[str, Any] = (
        json.loads(evidence.read_text()) if evidence.exists() else {}
    )
    node = results.setdefault("phase14", {}).setdefault("stage1", {})
    node[STORE_NODE] = payload
    atomic_write_json(evidence, results)
    print(f"\nrecorded: phase14.stage1.{STORE_NODE}")


def main(
    out: Annotated[
        pathlib.Path, typer.Option(help="Where the band tables are written")
    ] = ARTIFACT,
    record: Annotated[
        bool, typer.Option(help="Also record the tables in the evidence store")
    ] = False,
) -> None:
    """Print the 181(c) floor test and the 181(a) predictor comparison.

    Args:
        out: Artifact path (owner pin 201b — printing and exiting is the
            defect this replaces).
        record: Write the same tables to ``phase14.stage1.band_spectra``
            (201d — a measurement belongs in the store and the mirror).

    Raises:
        SystemExit: A ruling-quoted figure did not reproduce (205d). The
            three classes rest on these numbers, so this stops rather
            than recording a disagreement.
    """
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

    # Owner pins 201(c)/205(a)/(d): reproduce what the rulings quote, and
    # STOP on any disagreement rather than recording one.
    payload = build_payload(tracks, skills)
    print("\n=== ruling-quoted bands: recomputed and compared ===")
    print(
        f"{'tile':<12}{'band km':<12}{'field':<11}{'quoted':>9}{'computed':>11}"
        f"{'':>3}{'grid'}"
    )
    for verdict in payload["ruling_quote_verification"]:
        grid = "canonical" if verdict["on_canonical_grid"] else "EXPLICIT CUT (205b)"
        for field, quoted in verdict["quoted"].items():
            got = verdict["computed"][field]
            mark = "ok" if verdict["per_field_agrees"][field] else "MISMATCH"
            band = f"{verdict['band_km'][0]}-{verdict['band_km'][1]}"
            print(
                f"{verdict['tile']:<12}{band:<12}{field:<11}{quoted:>9.3f}"
                f"{got:>11.3f}  {mark}  {grid}"
            )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    print(f"\nwritten: {out}")

    if not payload["all_ruling_quotes_reproduced"]:
        failed = [v for v in payload["ruling_quote_verification"] if not v["agrees"]]
        raise SystemExit(
            "⛔ STOP (owner pin 205d): a ruling-quoted figure did not reproduce — "
            f"{[(v['tile'], v['band_km']) for v in failed]}. The three-class finding "
            "rests on these numbers. Nothing is recorded; this comes to the owner."
        )

    if record:
        _record(payload)


if __name__ == "__main__":
    typer.run(main)
