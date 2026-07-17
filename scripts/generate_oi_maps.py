r"""Generate full-year daily OI mean/variance maps at the signed baseline config.

Thin driver over :func:`sverdrup.validation.run.run_mean_var_maps`.

Scope discipline (set ``SVERDRUP_OI_MAPS_SCOPE`` before running):

    SVERDRUP_OI_MAPS_SCOPE=dev   → 12-day window (days 60-71); writes ONLY
                                    oi_{mean,var}_maps_dev.nc (NEVER the full-year
                                    filenames ``oi_{mean,var}_maps.nc``).
    (default / full)             → 2017-01-01..2017-12-31 (days 0-364); writes
                                    oi_{mean,var}_maps.nc — controller-owned, run
                                    detached via nohup.

Config pinning (§5 obligation):
    - ``baseline_config()`` supplies provider + grid + temporal half-window.
    - ``baseline_kernel()`` supplies the faithful Gaussian degree-space kernel.
    - Script asserts resolved values match the audit-trail constants; mismatch
      raises ``AssertionError`` before any solve (NEVER re-tuned).

Obs split (standing protocol, §5 criterion 2):
    - ``load_mapping_obs`` loads alg / h2g / j2g / j2n / j3 / s3a (NO c2).
    - ``make_splits(by="mission", locked_missions=["c2"],
      validation_missions=["j3"])`` → train indices.
    - ``_subset(obs, split.train_idx)`` → train-only obs (alg, h2g, j2g, j2n, s3a).
    - j3 is NEVER assimilated; c2 is NEVER touched.

Map-level config audit:
    After generation the dev-smoke mean is compared against the signed
    ``OSE_ssh_mapping_OURS_OI.nc`` on matched days.  A config mismatch (wrong
    kernel / params / grid) would show up as a systematic bias beyond the expected
    difference caused by obs-set divergence.  Comparison result is written to nc
    attrs and reported.

Config-audit PROOF mode (``SVERDRUP_OI_MAPS_AUDIT=j3_inclusive``):
    The train-only maps CANNOT be bit-compared against the signed artifact
    (different obs set: j3 excluded vs included).  This mode reruns the SAME
    signed config through the SAME producer path as Phase-4
    (``run_challenge_map`` — ``run_year`` delegates to it) with the signed
    artifact's obs set (ALL mapping missions INCLUDING j3, no split) over the
    12 smoke days, and compares means against the signed artifact:

    - BIT-IDENTICAL → code path + constants PROVEN to be the signed config.
    - tight rtol (< 1e-6 m max abs) → config proven; residual is solver/BLAS
      version noise (report which).
    - worse → REAL config mismatch → SystemExit (STOP, report BLOCKED).

    Output goes ONLY to ``oi_mean_maps_audit_j3incl.nc`` — never the descriptor
    artifact paths; the harness never consumes it.  On PASS the result is
    stamped as ``config_audit`` onto that audit file and persisted to the
    ``oi_config_audit.json`` sidecar, which upgrades the train-only maps'
    obs-set-divergence verdict to attributed-BY-CONSTRUCTION.
    ``SVERDRUP_OI_MAPS_SCOPE`` is IGNORED in audit mode (a note is printed):
    the audit always runs the 12 smoke days and never writes scope outputs.

One writer per nc file (race discipline):
    A SCOPE=dev or SCOPE=full run may be executing while the audit runs.
    Audit mode therefore NEVER touches ANY generation output — it stamps
    only its own ``oi_mean_maps_audit_j3incl.nc`` and writes the verdict to
    the ``oi_config_audit.json`` sidecar.  Each generation run (dev or full)
    stamps its OWN outputs from the sidecar after it finishes writing them,
    so every nc file has exactly one writer:

    - audit mode  → ``oi_mean_maps_audit_j3incl.nc`` + the JSON sidecar
    - SCOPE=dev   → ``oi_{mean,var}_maps_dev.nc``
    - SCOPE=full  → ``oi_{mean,var}_maps.nc``

Reference-frame note:
    The signed artifact is in SSH space (SLA + MDT from the mapping tracks).
    Our maps use the SAME MDT via ``load_mdt_grid`` so the comparison is in a
    consistent reference frame.

Usage::

    SVERDRUP_OI_MAPS_SCOPE=dev pixi run python scripts/generate_oi_maps.py
    SVERDRUP_OI_MAPS_SCOPE=full pixi run python scripts/generate_oi_maps.py
    SVERDRUP_OI_MAPS_AUDIT=j3_inclusive pixi run python scripts/generate_oi_maps.py

Full-year controller launch (detached, log to scratchpad)::

    nohup pixi run python scripts/generate_oi_maps.py \\
        > /tmp/claude-1000/-workspace/3a35cde9-6803-4625-888e-832d34763eb1/scratchpad/oi_maps_full.log \\
        2>&1 &
"""

from __future__ import annotations

import json
import os
import resource
import time
from pathlib import Path

import numpy as np
import xarray as xr

from sverdrup.application.splits import make_splits
from sverdrup.validation.input_adapter import load_mapping_obs, load_mdt_grid
from sverdrup.validation.params import (
    SIGNAL_VARIANCE,
    SPATIAL_CORR_DEG,
    TEMPORAL_CORR_DAYS,
    TEMPORAL_HALF_WINDOW_DAYS,
    baseline_config,
    baseline_kernel,
)
from sverdrup.validation.run import _subset, run_challenge_map, run_mean_var_maps

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_ROOT = Path("data/2021a_ssh_mapping_ose")
_OBS_DIR = _DATA_ROOT / "dc_obs"
_OUT_ROOT = _DATA_ROOT / "ours"
_SIGNED_OI_NC = _OUT_ROOT / "OSE_ssh_mapping_OURS_OI.nc"

_MAPPING_OBS_PATHS: list[Path] = [
    _OBS_DIR / "dt_gulfstream_alg_phy_l3_20161201-20180131_285-315_23-53.nc",
    _OBS_DIR / "dt_gulfstream_h2g_phy_l3_20161201-20180131_285-315_23-53.nc",
    _OBS_DIR / "dt_gulfstream_j2g_phy_l3_20161201-20180131_285-315_23-53.nc",
    _OBS_DIR / "dt_gulfstream_j2n_phy_l3_20161201-20180131_285-315_23-53.nc",
    _OBS_DIR / "dt_gulfstream_j3_phy_l3_20161201-20180131_285-315_23-53.nc",
    _OBS_DIR / "dt_gulfstream_s3a_phy_l3_20161201-20180131_285-315_23-53.nc",
]

# c2 must NEVER appear here — the input_adapter guard rejects it as a safety net
# but we never pass it in the first place.

# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------
_SCOPE = os.environ.get("SVERDRUP_OI_MAPS_SCOPE", "full")
if _SCOPE not in {"dev", "full"}:
    raise SystemExit(f"SVERDRUP_OI_MAPS_SCOPE must be 'dev' or 'full', got {_SCOPE!r}")

# Config-audit proof mode (see module docstring). When set, NO train-only maps
# are generated; only the j3-inclusive comparison against the signed artifact.
_AUDIT_MODE = os.environ.get("SVERDRUP_OI_MAPS_AUDIT")
if _AUDIT_MODE is not None and _AUDIT_MODE != "j3_inclusive":
    raise SystemExit(
        f"SVERDRUP_OI_MAPS_AUDIT must be 'j3_inclusive' (or unset), got {_AUDIT_MODE!r}"
    )

# Audit output — clearly separated from the descriptor artifact paths
# (oi_{mean,var}_maps.nc); the harness NEVER consumes this file.
_AUDIT_MEAN_DEST = _OUT_ROOT / "oi_mean_maps_audit_j3incl.nc"

# Sidecar carrying the audit verdict.  ONE WRITER PER NC FILE: audit mode
# writes ONLY this sidecar + its own audit output nc; each generation run
# (dev or full) stamps its OWN outputs from the sidecar after finishing
# them, so the audit never races a live generation run on any nc file.
_AUDIT_SIDECAR = _OUT_ROOT / "oi_config_audit.json"

# Max abs threshold for the j3-inclusive proof: anything worse than 1e-6 m
# cannot be solver/BLAS version noise and is a REAL config mismatch.
_AUDIT_RTOL_THRESHOLD_M = 1e-6

# Dev smoke: days 60-71 (2017-03-02 to 2017-03-13, matching the stage_a fixture).
# Full year: days 0-364 (2017-01-01 to 2017-12-31).
_DEV_DAYS: list[float] = [float(d) for d in range(60, 72)]  # 12 days
_FULL_DAYS: list[float] = [float(d) for d in range(0, 365)]  # 365 days

if _SCOPE == "dev":
    _OUTPUT_DAYS = _DEV_DAYS
    _MEAN_DEST = _OUT_ROOT / "oi_mean_maps_dev.nc"
    _VAR_DEST = _OUT_ROOT / "oi_var_maps_dev.nc"
else:
    _OUTPUT_DAYS = _FULL_DAYS
    _MEAN_DEST = _OUT_ROOT / "oi_mean_maps.nc"
    _VAR_DEST = _OUT_ROOT / "oi_var_maps.nc"


def _peak_rss_mb() -> float:
    """Return peak RSS in MiB (Linux: RUSAGE_SELF in KB → MiB)."""
    kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return kb / 1024.0  # Linux reports KB; macOS reports bytes but we run on Linux


def _update_nc_attrs(path: Path, attrs: dict[str, object]) -> None:
    """Atomically merge global attrs into an existing NetCDF file.

    Loads the dataset into memory, updates the attrs, writes to a ``.tmp.nc``
    sibling, and renames over the original (the single tmp+replace dance).

    Args:
        path: Path to the NetCDF file to update in place.
        attrs: Global attrs to merge (existing keys are overwritten).
    """
    ds = xr.open_dataset(path)
    ds = ds.load()
    ds.close()
    ds.attrs.update(attrs)
    tmp = path.with_suffix(".tmp.nc")
    ds.to_netcdf(tmp)
    tmp.replace(path)


def _add_provenance_attrs(
    path: Path,
    *,
    framing: str,
    params_key: str,
    kernel_name: str,
    signal_variance: float,
    spatial_corr_deg: float,
    temporal_corr_days: float,
    temporal_half_window_days: float,
    audit_note: str,
) -> None:
    """Append extra provenance attrs to an already-written NetCDF file.

    Args:
        path: Path to the NetCDF file to update in place.
        framing: Spatial obs framing description.
        params_key: Short key identifying the parameter set.
        kernel_name: Name of the covariance kernel used.
        signal_variance: Signed baseline signal variance (audit constant).
        spatial_corr_deg: Signed baseline spatial correlation scale (degrees).
        temporal_corr_days: Signed baseline temporal correlation scale (days).
        temporal_half_window_days: Temporal half-window used for obs selection.
        audit_note: Free-form audit-trail note.
    """
    _update_nc_attrs(
        path,
        {
            "framing": framing,
            "params_key": params_key,
            "kernel_name": kernel_name,
            "signal_variance": signal_variance,
            "spatial_corr_deg": spatial_corr_deg,
            "temporal_corr_days": temporal_corr_days,
            "temporal_half_window_days": temporal_half_window_days,
            "audit_note": audit_note,
        },
    )


def _compare_on_matched_days(
    regen_path: Path, signed_path: Path
) -> tuple[int, bool, float, float, float]:
    """Compare two ssh map files on their overlapping time steps.

    The single implementation of the matched-day comparison shared by the
    train-only audit and the j3-inclusive proof: time intersection,
    ``datetime64`` selection, absolute/relative diffs with a denominator
    clamp against near-zero SSH values.

    Args:
        regen_path: Path to the regenerated map NetCDF (variable ``ssh``).
        signed_path: Path to the signed reference NetCDF (variable ``ssh``).

    Returns:
        ``(n_matched, bit_identical, max_abs, mean_abs, max_rel)``. When
        ``n_matched == 0`` the float stats are NaN and ``bit_identical`` is
        False; callers own the zero-match policy (skip vs abort).
    """
    regen = xr.open_dataset(regen_path)
    signed = xr.open_dataset(signed_path)
    matched = sorted(set(regen.time.values.tolist()) & set(signed.time.values.tolist()))
    n_matched = len(matched)
    if n_matched == 0:
        regen.close()
        signed.close()
        return 0, False, float("nan"), float("nan"), float("nan")

    matched_arr = np.array(matched, dtype="datetime64[ns]")
    regen_sel = regen.sel(time=matched_arr)["ssh"].values
    signed_sel = signed.sel(time=matched_arr)["ssh"].values
    regen.close()
    signed.close()

    bit_identical = bool(np.array_equal(regen_sel, signed_sel))
    abs_diff = np.abs(regen_sel - signed_sel)
    max_abs = float(np.nanmax(abs_diff))
    mean_abs = float(np.nanmean(abs_diff))
    denom = np.abs(signed_sel)
    denom[denom < 1e-10] = 1e-10  # avoid div by 0 on near-zero values
    max_rel = float(np.nanmax(abs_diff / denom))
    return n_matched, bit_identical, max_abs, mean_abs, max_rel


def _matched_day_audit(mean_path: Path, signed_path: Path) -> dict[str, object]:
    """Compare regenerated OI means against the signed artifact on matched days.

    Args:
        mean_path: Path to the regenerated mean maps NetCDF.
        signed_path: Path to the signed ``OSE_ssh_mapping_OURS_OI.nc``.

    Returns:
        A dict with keys: ``matched_days``, ``max_abs_diff``, ``max_rel_diff``,
        ``mean_abs_diff``, ``obs_set_note``, ``verdict``.

    Raises:
        SystemExit: If the comparison reveals a config mismatch (systematic
            bias inconsistent with the expected obs-set difference).
    """
    if not signed_path.exists():
        return {
            "matched_days": 0,
            "verdict": "SKIPPED — signed artifact not found",
            "signed_path": str(signed_path),
        }

    n_matched, _bit, max_abs, mean_abs, max_rel = _compare_on_matched_days(
        mean_path, signed_path
    )
    if n_matched == 0:
        return {
            "matched_days": 0,
            "verdict": "SKIPPED — no overlapping time steps between regen and signed",
        }

    # Obs-set divergence note (pre-registered determination):
    # The signed artifact used all 6 mapping missions (alg, h2g, j2g, j2n, j3, s3a)
    # because Phase-4 run_year loaded ALL mapping missions without a train/val split.
    # Our regenerated maps use TRAIN-ONLY (alg, h2g, j2g, j2n, s3a — j3 excluded),
    # per the Phase-9 standing split.  Differences are therefore EXPECTED (obs-set
    # divergence) and are not a config mismatch.  A config mismatch (wrong kernel /
    # params / grid) would manifest as a systematic offset inconsistent with the
    # ~5 cm level noise seen in the SLA field.
    obs_set_note = (
        "EXPECTED DIFFERENCE — regenerated maps use train-only obs (j3 excluded); "
        "signed artifact used all 5 mapping missions including j3 (Phase-4 run_year "
        "protocol, no train/val split). Differences at this scale are obs-set "
        "divergence, NOT a config mismatch."
    )

    # Config-mismatch STOP criterion: a systematic mean offset >> field std is
    # the Phase-7 0.16 m lesson pattern.  The MDT offset was ~0.3 m; a correct
    # obs-set diff should be O(cm), consistent with the SLA signal (~0.1 m std).
    # We use 0.1 m as the STOP threshold for the mean absolute difference.
    _STOP_THRESHOLD_M = 0.1
    if mean_abs > _STOP_THRESHOLD_M:
        # This looks like the Phase-7 MDT bug or a kernel/grid mismatch — STOP.
        print(
            f"\n[AUDIT STOP] mean_abs_diff={mean_abs:.4f} m exceeds "
            f"stop threshold {_STOP_THRESHOLD_M} m. "
            "This is inconsistent with an obs-set difference alone and suggests "
            "a config mismatch (wrong kernel, missing MDT, wrong grid). "
            "REPORT: BLOCKED — investigate the attribution.",
            flush=True,
        )
        raise SystemExit(
            f"MAP-LEVEL CONFIG AUDIT FAILED: mean_abs_diff={mean_abs:.4f} m "
            f"(threshold {_STOP_THRESHOLD_M} m). STOP — see report."
        )

    verdict = (
        f"PASS (obs-set divergence) — max_abs={max_abs:.4f} m, "
        f"mean_abs={mean_abs:.4f} m, max_rel={max_rel:.4f}; "
        f"differences consistent with j3-exclusion (train-only vs all-5-missions). "
        f"Config constants VERIFIED consistent with signed baseline."
    )

    return {
        "matched_days": n_matched,
        "max_abs_diff_m": max_abs,
        "mean_abs_diff_m": mean_abs,
        "max_rel_diff": max_rel,
        "obs_set_note": obs_set_note,
        "verdict": verdict,
    }


def _stamp_config_audit_attr(paths: list[Path], config_audit: str) -> None:
    """Stamp the ``config_audit`` proof line onto existing map files.

    Args:
        paths: NetCDF files to update (missing files are skipped).
        config_audit: The proof line, e.g.
            ``"j3-inclusive matched-day: bit-identical (12 days)"``.
    """
    for p in paths:
        if not p.exists():
            continue
        _update_nc_attrs(p, {"config_audit": config_audit})
        print(f"  [OK] config_audit attr stamped on {p}", flush=True)


def run_config_audit() -> None:
    """PROOF-BY-CONSTRUCTION config audit: reproduce the signed artifact.

    Reruns the signed config through the SAME producer path as Phase-4
    (``run_challenge_map``; ``run_year`` delegates to it) with the signed
    artifact's obs set (ALL mapping missions INCLUDING j3 — no split) over
    the 12 smoke days, then compares means against the signed
    ``OSE_ssh_mapping_OURS_OI.nc`` on those days.

    Raises:
        SystemExit: If max abs diff exceeds ``_AUDIT_RTOL_THRESHOLD_M`` —
            a REAL config mismatch (STOP semantics, Phase-7 lesson).
    """
    t0 = time.monotonic()
    print("[generate_oi_maps] CONFIG AUDIT MODE (j3_inclusive)", flush=True)
    if "SVERDRUP_OI_MAPS_SCOPE" in os.environ:
        print(
            f"  [note] SVERDRUP_OI_MAPS_SCOPE={_SCOPE!r} is IGNORED in audit "
            "mode — the audit always runs the 12 smoke days and never writes "
            "scope outputs.",
            flush=True,
        )
    print(
        "  reproducing the signed artifact's producer run: run_challenge_map, "
        "ALL mapping missions (j3 INCLUDED), signed config, 12 smoke days",
        flush=True,
    )

    provider, grid, half = baseline_config()
    kernel = baseline_kernel()

    print(
        "  loading mapping obs (ALL missions, incl. j3; c2 never read) ...", flush=True
    )
    obs_all = load_mapping_obs(_MAPPING_OBS_PATHS, provider)
    print(f"  loaded {len(obs_all)} obs", flush=True)

    print("  loading MDT grid ...", flush=True)
    mdt_grid = load_mdt_grid(_MAPPING_OBS_PATHS, grid)

    print(
        f"  generating {len(_DEV_DAYS)}-day j3-inclusive means -> {_AUDIT_MEAN_DEST} ...",
        flush=True,
    )
    run_challenge_map(
        "oi",
        obs_all,
        provider,
        grid,
        half,
        _DEV_DAYS,
        _AUDIT_MEAN_DEST,
        kernel=kernel,
        halo_deg=1.0,
        mdt_grid=mdt_grid,
    )

    print(f"  comparing vs {_SIGNED_OI_NC} on matched days ...", flush=True)
    n_matched, bit_identical, max_abs, _mean_abs, max_rel = _compare_on_matched_days(
        _AUDIT_MEAN_DEST, _SIGNED_OI_NC
    )
    if n_matched == 0:
        raise SystemExit("CONFIG AUDIT: no matched days — cannot prove config.")

    if bit_identical:
        config_audit = f"j3-inclusive matched-day: bit-identical ({n_matched} days)"
    elif max_abs < _AUDIT_RTOL_THRESHOLD_M:
        config_audit = (
            f"j3-inclusive matched-day: tight-rtol PASS ({n_matched} days, "
            f"max_abs={max_abs:.3e} m, max_rel={max_rel:.3e}; "
            f"residual attributed to solver/BLAS version noise, not config)"
        )
    else:
        print(
            f"\n[AUDIT STOP] j3-inclusive rerun does NOT reproduce the signed "
            f"artifact: max_abs={max_abs:.6f} m (threshold "
            f"{_AUDIT_RTOL_THRESHOLD_M} m), max_rel={max_rel:.3e}, "
            f"bit_identical={bit_identical}. This is a REAL config mismatch "
            "(same obs set, same nominal config) — the kernel, params, grid, "
            "framing, or MDT differ from the Phase-4 producer. "
            "REPORT: BLOCKED with attribution.",
            flush=True,
        )
        raise SystemExit(
            f"MAP-LEVEL CONFIG AUDIT FAILED (j3-inclusive proof): "
            f"max_abs={max_abs:.6f} m exceeds {_AUDIT_RTOL_THRESHOLD_M} m. STOP."
        )

    print(f"  [PASS] {config_audit}", flush=True)

    # Persist the verdict to the sidecar (atomic write).  NO generation
    # outputs are stamped here — a live SCOPE=dev or SCOPE=full run may be
    # writing its files right now (one writer per nc file).  Every
    # generation run stamps its OWN outputs from this sidecar after
    # finishing them.
    payload = {
        "config_audit": config_audit,
        "matched_days": n_matched,
        "bit_identical": bit_identical,
        "max_abs_diff_m": max_abs,
        "max_rel_diff": max_rel,
        "producer_path": "run_challenge_map (Phase-4 run_year delegate)",
        "obs_set": "all mapping missions incl. j3 (signed-artifact producer set)",
    }
    tmp_json = _AUDIT_SIDECAR.with_name(_AUDIT_SIDECAR.name + ".tmp")
    tmp_json.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    tmp_json.replace(_AUDIT_SIDECAR)
    print(f"  [OK] audit verdict persisted to {_AUDIT_SIDECAR}", flush=True)

    # Stamp ONLY the audit's own output file (the single file this mode owns).
    _stamp_config_audit_attr([_AUDIT_MEAN_DEST], config_audit)

    wall = time.monotonic() - t0
    print(
        f"\n[generate_oi_maps] CONFIG AUDIT DONE wall={wall:.1f}s "
        f"peak_rss={_peak_rss_mb():.0f} MiB — {config_audit}",
        flush=True,
    )


def main() -> None:
    """Run OI mean/variance map generation at the signed baseline config.

    Raises:
        AssertionError: If the resolved baseline_config values do not match
            the audit-trail constants (config integrity check).
        SystemExit: If the matched-day audit detects a config mismatch.
    """
    if _AUDIT_MODE == "j3_inclusive":
        run_config_audit()
        return

    t0 = time.monotonic()
    print(f"[generate_oi_maps] scope={_SCOPE!r}", flush=True)
    print(
        f"  output_days: {len(_OUTPUT_DAYS)} days "
        f"({_OUTPUT_DAYS[0]}..{_OUTPUT_DAYS[-1]})",
        flush=True,
    )

    # ------------------------------------------------------------------
    # 1. Resolve baseline config and ASSERT audit constants match.
    # ------------------------------------------------------------------
    provider, grid, half = baseline_config()
    kernel = baseline_kernel()

    # Resolved scalar checks — these assert the signed config constants.
    resolved_variance = float(provider.resolve("variance", grid))
    resolved_length_scale = float(provider.resolve("length_scale", grid))
    resolved_time_scale = float(provider.resolve("time_scale", grid))

    if resolved_variance != SIGNAL_VARIANCE:
        raise RuntimeError(
            f"variance mismatch: {resolved_variance} != {SIGNAL_VARIANCE}"
        )
    if abs(resolved_time_scale - TEMPORAL_CORR_DAYS) >= 1e-12:
        raise RuntimeError(
            f"time_scale mismatch: {resolved_time_scale} != {TEMPORAL_CORR_DAYS}"
        )
    # length_scale is the degree-to-km analog (SPATIAL_CORR_DEG * _KM_PER_DEG).
    from sverdrup.validation.params import _KM_PER_DEG as _KPD  # noqa: PLC0415

    expected_length_scale = SPATIAL_CORR_DEG * _KPD
    if abs(resolved_length_scale - expected_length_scale) >= 1e-9:
        raise RuntimeError(
            f"length_scale mismatch: {resolved_length_scale} != {expected_length_scale}"
        )
    if half != TEMPORAL_HALF_WINDOW_DAYS:
        raise RuntimeError(
            f"temporal_half_window mismatch: {half} != {TEMPORAL_HALF_WINDOW_DAYS}"
        )
    # Kernel scalar checks.
    if kernel.variance != SIGNAL_VARIANCE:
        raise RuntimeError(
            f"kernel.variance mismatch: {kernel.variance} != {SIGNAL_VARIANCE}"
        )
    if kernel.lx_deg != SPATIAL_CORR_DEG:
        raise RuntimeError(
            f"kernel.lx_deg mismatch: {kernel.lx_deg} != {SPATIAL_CORR_DEG}"
        )
    if kernel.ly_deg != SPATIAL_CORR_DEG:
        raise RuntimeError(
            f"kernel.ly_deg mismatch: {kernel.ly_deg} != {SPATIAL_CORR_DEG}"
        )
    if kernel.time_scale != TEMPORAL_CORR_DAYS:
        raise RuntimeError(
            f"kernel.time_scale mismatch: {kernel.time_scale} != {TEMPORAL_CORR_DAYS}"
        )

    print(
        f"  [OK] audit constants verified: variance={resolved_variance}, "
        f"spatial_corr_deg={SPATIAL_CORR_DEG}, temporal_corr_days={TEMPORAL_CORR_DAYS}, "
        f"half_window={half}d, kernel={type(kernel).__name__}",
        flush=True,
    )

    # ------------------------------------------------------------------
    # 2. Load observations and apply the standing split.
    # ------------------------------------------------------------------
    print("  loading mapping obs ...", flush=True)
    obs_all = load_mapping_obs(_MAPPING_OBS_PATHS, provider)
    print(f"  loaded {len(obs_all)} obs (all mapping missions, pre-split)", flush=True)

    split = make_splits(
        obs_all,
        by="mission",
        locked_missions=["c2"],
        validation_missions=["j3"],
    )
    train_obs = _subset(obs_all, split.train_idx)
    print(
        f"  train obs: {len(train_obs)} "
        f"(locked c2={len(split.locked_test_idx)}, "
        f"val j3={len(split.validation_idx)}, "
        f"train={len(split.train_idx)})",
        flush=True,
    )

    # ------------------------------------------------------------------
    # 3. Load MDT (reference frame: ssh = sla + mdt, matching signed artifact).
    # ------------------------------------------------------------------
    print("  loading MDT grid ...", flush=True)
    mdt_grid = load_mdt_grid(_MAPPING_OBS_PATHS, grid)
    print(f"  MDT grid shape: {mdt_grid.shape}", flush=True)

    # ------------------------------------------------------------------
    # 4. Generate mean + variance maps via run_mean_var_maps (REUSE).
    # ------------------------------------------------------------------
    print(
        f"  generating {len(_OUTPUT_DAYS)}-day OI maps -> "
        f"{_MEAN_DEST} + {_VAR_DEST} ...",
        flush=True,
    )
    t_gen_start = time.monotonic()
    mean_path, var_path = run_mean_var_maps(
        "oi",
        train_obs,
        provider,
        grid,
        half,
        _OUTPUT_DAYS,
        _MEAN_DEST,
        _VAR_DEST,
        kernel=kernel,
        halo_deg=1.0,
        mdt_grid=mdt_grid,
    )
    t_gen = time.monotonic() - t_gen_start
    rss_mb = _peak_rss_mb()
    print(
        f"  [OK] maps written in {t_gen:.1f}s  peak RSS {rss_mb:.0f} MiB",
        flush=True,
    )

    # ------------------------------------------------------------------
    # 5. Add extra provenance attrs (assimilated_missions already in file).
    # ------------------------------------------------------------------
    _framing = "grid-node halo 1.0 deg"
    _params_key = "baseline_oi_v1"
    _kernel_name = type(kernel).__name__
    _audit_note = (
        f"Phase-9 Task-6 signed baseline config: variance={SIGNAL_VARIANCE}, "
        f"spatial_corr_deg={SPATIAL_CORR_DEG}, temporal_corr_days={TEMPORAL_CORR_DAYS}, "
        f"temporal_half_window={TEMPORAL_HALF_WINDOW_DAYS}d; "
        f"kernel={_kernel_name}; train-only obs (c2 locked, j3 validation)."
    )
    for p in (mean_path, var_path):
        _add_provenance_attrs(
            p,
            framing=_framing,
            params_key=_params_key,
            kernel_name=_kernel_name,
            signal_variance=SIGNAL_VARIANCE,
            spatial_corr_deg=SPATIAL_CORR_DEG,
            temporal_corr_days=TEMPORAL_CORR_DAYS,
            temporal_half_window_days=TEMPORAL_HALF_WINDOW_DAYS,
            audit_note=_audit_note,
        )
    print("  [OK] provenance attrs written to both nc files", flush=True)

    # ------------------------------------------------------------------
    # 6. Map-level config audit on matched days.
    # ------------------------------------------------------------------
    print("\n  [MAP-LEVEL CONFIG AUDIT]", flush=True)
    print(f"  comparing {mean_path} vs {_SIGNED_OI_NC} ...", flush=True)
    audit = _matched_day_audit(mean_path, _SIGNED_OI_NC)
    print(f"  matched days: {audit.get('matched_days', 0)}", flush=True)
    print(f"  verdict: {audit.get('verdict', 'N/A')}", flush=True)
    if "obs_set_note" in audit:
        print(f"  obs_set_note: {audit['obs_set_note']}", flush=True)

    # Write audit result to nc attrs.
    audit_attrs: dict[str, object] = {
        "audit_matched_days": str(audit.get("matched_days", 0)),
        "audit_verdict": str(audit.get("verdict", "N/A")),
        "audit_max_abs_diff_m": str(audit.get("max_abs_diff_m", "N/A")),
        "audit_mean_abs_diff_m": str(audit.get("mean_abs_diff_m", "N/A")),
        "audit_obs_set_note": str(
            audit.get(
                "obs_set_note",
                "no obs-set note (signed artifact not found or no matched days)",
            )
        ),
    }
    for p in (mean_path, var_path):
        _update_nc_attrs(p, audit_attrs)
    print("  [OK] audit attrs written to both nc files", flush=True)

    # ------------------------------------------------------------------
    # 6b. Stamp the j3-inclusive config-audit proof from the sidecar, if a
    #     config audit has run.  ONE WRITER PER NC FILE: this run stamps
    #     ONLY the files IT just wrote (mean_path / var_path); audit mode
    #     never touches generation outputs.  A corrupt/incomplete sidecar
    #     (possibly mid-write by another process) must NOT abort a
    #     completed generation run — degrade to the absent-sidecar note.
    # ------------------------------------------------------------------
    config_audit_line: str | None = None
    if _AUDIT_SIDECAR.exists():
        try:
            sidecar = json.loads(_AUDIT_SIDECAR.read_text())
            config_audit_line = str(sidecar["config_audit"])
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            print(
                f"  [note] config-audit sidecar at {_AUDIT_SIDECAR} is "
                f"unreadable ({type(exc).__name__}: {exc}); skipping the "
                "config_audit stamp — rerun SVERDRUP_OI_MAPS_AUDIT="
                "j3_inclusive to regenerate it.",
                flush=True,
            )
    if config_audit_line is not None:
        _stamp_config_audit_attr([mean_path, var_path], config_audit_line)
    elif not _AUDIT_SIDECAR.exists():
        print(
            f"  [note] no config-audit sidecar at {_AUDIT_SIDECAR}; "
            "run SVERDRUP_OI_MAPS_AUDIT=j3_inclusive first to stamp the proof.",
            flush=True,
        )

    # ------------------------------------------------------------------
    # 7. Shape / attrs verification.
    # ------------------------------------------------------------------
    mean_ds = xr.open_dataset(mean_path)
    var_ds = xr.open_dataset(var_path)
    print("\n  [shape check]", flush=True)
    print(f"  mean shape: {mean_ds['ssh'].shape}", flush=True)
    print(f"  var  shape: {var_ds['ssh'].shape}", flush=True)
    print(f"  mean attrs: {dict(mean_ds.attrs)}", flush=True)
    mean_ds.close()
    var_ds.close()

    wall = time.monotonic() - t0
    print(
        f"\n[generate_oi_maps] DONE "
        f"scope={_SCOPE!r} wall={wall:.1f}s peak_rss={rss_mb:.0f} MiB",
        flush=True,
    )


if __name__ == "__main__":
    main()
