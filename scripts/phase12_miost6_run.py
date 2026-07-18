"""Phase-12 six-mission MIOST production runner (plan Task 5; spec §§1,4,5).

The ONE new runner of the phase: ``--smoke`` (Task 6), ``--run`` (the single
authorized full-year evidence solve), ``--c2-touch`` (Task 8; a refusing stub
until then). Never imports from ``stage_miost_gate_run.py``; its evidence
store is the NEW ``phase12_miost6_results.json`` — the phase-8 store is not
named anywhere in this file (pinned by test).

Everything frozen from the signed record: winner params verbatim (literal
below, asserted against the signed record at launch), s(x) field by cal_key,
m=100, seed root ``derive_seed("miost","stage-b-winner","members",0)``
(= 4836134738817689931 exact int), caps (500, 2000, 8000), pcg_rtol 1e-6.

ZERO c2 capability in --run and --smoke: no code path here opens the c2
file; the c2_track_path is carried as scope metadata only.
"""

from __future__ import annotations

import argparse
import json
import resource
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import numpy as np

if TYPE_CHECKING:
    from sverdrup.core.observations import ObsWindow
    from sverdrup.distributions.calibration import CalibrationField
    from sverdrup.methods.miost_windows import WindowPlan

from sverdrup.validation.phase12_config import Phase12Scope, load_phase12_scope
from sverdrup.validation.phase12_evidence import (
    DEV_SMOKE_PREFIX as DEV_SMOKE_KEY,
)
from sverdrup.validation.phase12_evidence import (
    MIOST6_PREFIX,
    provenance_block,
    sha256_file,
    write_pack_entry,
)

OURS = Path("data/2021a_ssh_mapping_ose/ours")
RESULTS = OURS / "phase12_miost6_results.json"
GEOMETRY = OURS / "phase12_orbit_geometry_miost6.json"
FIVE_MEAN = OURS / "stage_miost_acceptance.nc"
FIVE_VAR = OURS / "stage_b_var_maps.nc"
FIELD_ART = OURS / "phase8_field.json"
TIER3_THEIRS = Path("data/2021a_ssh_mapping_ose/dc_maps/OSE_ssh_mapping_MIOST.nc")
SCOPE_DEFAULT = Path("tests/validation/fixtures/phase12_miost6_scope.json")

# The signed Stage-A winner, verbatim (full precision; asserted against the
# signed record at --run launch — both results["winner"]["params"] and
# stage_b.winner_params must equal these EXACTLY).
WINNER_PARAMS = {
    "spacing_alpha": 1.0656719505786896,
    "log10_rho": -1.5990709075704217,
    "q_slope": 1.4518111273646355,
    "l_t_days": 6.00630128569901,
}
M_MEMBERS = 100
CAPS = (500, 2000, 8000)
RTOL = 1e-6

# Tier-3 anchor (fork c): the five-mission product's similarity row vs the
# pinned CLS maps — the six-mission row is read BESIDE it at the T7 gate.
TIER3_ANCHOR = {"rms_mean": 0.0472, "coh_100km": 0.761, "coh_200km": 0.930}
LAT_BAND = (37.0, 39.0)
KM_PER_DEG = 111.32
ON_TRACK_DEG = 0.15  # grid node within this of a j3 obs point = on-track

_T0 = time.time()


def _log(msg: str) -> None:
    """Print a timestamped, flushed heartbeat line."""
    s = int(time.time() - _T0)
    print(f"[+{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}] {msg}", flush=True)


def _peak_rss_mib() -> float:
    """Peak RSS of this process [MiB] (linux ru_maxrss is KiB)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def assert_winner_matches_signed(signed_record: Path) -> dict[str, float]:
    """Assert the literal winner params equal the signed record's, exactly.

    Args:
        signed_record: Path to the signed gate evidence JSON (passed on the
            command line — this file's name never appears in this script).

    Returns:
        The verified winner params (the literal).

    Raises:
        SystemExit: On any exact-float mismatch (frozen record violated).
    """
    rec = json.loads(signed_record.read_text())
    for src_name, params in (
        ("winner.params", rec["winner"]["params"]),
        ("stage_b.winner_params", rec["stage_b"]["winner_params"]),
    ):
        if params != WINNER_PARAMS:
            raise SystemExit(
                f"REFUSED: signed-record {src_name} != frozen literal winner "
                f"params ({params!r} vs {WINNER_PARAMS!r})"
            )
    return dict(WINNER_PARAMS)


def shipped_calibration() -> CalibrationField:
    """The shipped s(x) field, cal_key-asserted against phase8_field.json.

    Returns:
        The PolyCalibration the shipped factory carries.

    Raises:
        SystemExit: If the factory field's cal_key drifts from the SIGNED
            artifact.
    """
    from sverdrup.methods.miost import shipped_miost6

    cal = shipped_miost6()._calibration
    art = json.loads(FIELD_ART.read_text())
    if cal.key() != art["cal_key"]:
        raise SystemExit(
            "REFUSED: factory calibration cal_key != signed phase8_field.json"
        )
    return cal


def load_obs_for(scope: Phase12Scope, paths: list[Path] | None = None) -> ObsWindow:
    """Load + halo-frame the mapping obs (production framing).

    Args:
        scope: The validated phase12 scope.
        paths: Override obs paths (the CRN assert loads a j3-less set).

    Returns:
        The halo-framed ObsWindow.
    """
    from sverdrup.validation.input_adapter import load_mapping_obs
    from sverdrup.validation.params import baseline_config
    from sverdrup.validation.run import halo_obs

    provider, grid, _ = baseline_config()
    obs = load_mapping_obs(list(paths or scope.mapping_obs_paths), provider)
    return halo_obs(obs, grid)


def crn_shared_mission_assert(scope: Phase12Scope, member: int = 0) -> dict[str, Any]:
    """Prove s3a member draws replay bit-equal vs the five-mission derivation.

    Identity-keyed CRN (spec 6.2): a draw depends on (root, member, obs
    identity row) only — adding j3 must NOT move any shared mission's
    perturbations. Loads the obs six-mission and five-mission (j3 path
    dropped), builds the s3a identity rows both ways, and asserts the rows
    AND the obs_noise draws are bit-equal.

    Args:
        scope: The validated phase12 scope.
        member: Member index to replay.

    Returns:
        Evidence block with counts and the bit-equality verdict.

    Raises:
        SystemExit: If any s3a identity row or draw differs (CRN broken).
    """
    from sverdrup.core.seeding import derive_seed
    from sverdrup.methods.miost import _obs_identity
    from sverdrup.methods.miost_basis import R_REF
    from sverdrup.methods.miost_crn import obs_noise

    root = derive_seed("miost", "stage-b-winner", "members", 0)

    def _s3a_rows(obs: ObsWindow) -> np.ndarray:
        mission = np.asarray(obs.mission)
        mask = mission == "s3a"
        coords = obs.coords()
        return _obs_identity(
            coords[mask, 0], coords[mask, 1], coords[mask, 2], mission[mask]
        )

    six = _s3a_rows(load_obs_for(scope))
    five_paths = [p for p in scope.mapping_obs_paths if "_j3_" not in p.name]
    five = _s3a_rows(load_obs_for(scope, five_paths))

    rows_equal = six.shape == five.shape and bool(np.array_equal(six, five))
    if not rows_equal:
        raise SystemExit(
            "REFUSED: s3a identity rows differ between five- and six-mission "
            f"loads (shapes {five.shape} vs {six.shape}) — CRN identity broken"
        )
    r = np.full(six.shape[0], R_REF)
    draws_six = obs_noise(member, six, r, root)
    draws_five = obs_noise(member, five, r, root)
    if not np.array_equal(draws_six, draws_five):
        raise SystemExit("REFUSED: s3a obs_noise draws differ — CRN broken")
    return {
        "mission": "s3a",
        "member": member,
        "n_obs": int(six.shape[0]),
        "identity_rows_bit_equal": True,
        "obs_noise_bit_equal": True,
        "root": int(root),
    }


def solve_maps(
    scope: Phase12Scope,
    days: list[float],
    mean_out: Path,
    var_out: Path,
    member_store_out: Path | None,
    plan: WindowPlan | None = None,
    monitor_flag_s: float | None = None,
) -> dict[str, Any]:
    """The frozen-config six-mission solve: members -> day fields -> maps.

    Args:
        scope: The validated phase12 scope.
        days: Output days (smoke: the 12-day list; run: 0..364).
        mean_out: Mean maps NetCDF destination.
        var_out: Variance maps NetCDF destination.
        member_store_out: Member-store npz destination (None = skip, smoke).
        plan: Window-plan override (smoke restricts to covering windows);
            None = the full-year production plan.
        monitor_flag_s: Owner safety (a): elapsed wall beyond this FLAGS
            loudly per window (never kills); None = no flag.

    Returns:
        Telemetry block (converged, maxiter_used, batches, wall, peak RSS,
        n_obs, assimilated missions).

    Raises:
        SystemExit: On member under-convergence at every cap.
    """
    from sverdrup.core.parameters import ConstantProvider
    from sverdrup.core.seeding import derive_seed
    from sverdrup.core.types import UncertaintyCapability
    from sverdrup.distributions.calibration import CalibratedDistribution
    from sverdrup.distributions.miost_ensemble import (
        MiostEnsembleDistribution,
        ensemble_provenance,
        mean_fields,
        std_fields,
    )
    from sverdrup.methods.miost import CONVERGENCE_LOG, Miost
    from sverdrup.methods.miost_windows import WindowPlan
    from sverdrup.validation.input_adapter import load_mdt_grid
    from sverdrup.validation.output_adapter import write_map
    from sverdrup.validation.params import baseline_config

    t_start = time.time()
    _, grid, _ = baseline_config()
    cal = shipped_calibration()
    root = derive_seed("miost", "stage-b-winner", "members", 0)
    obs = load_obs_for(scope)
    n_obs = len(obs)
    _log(
        f"solve: obs {n_obs} (six missions, halo-framed); m={M_MEMBERS}; days {len(days)}"
    )

    from sverdrup.distributions.miost_ensemble import merged_members

    if plan is None:
        plan = WindowPlan()
    provider = ConstantProvider(dict(WINNER_PARAMS))
    window_log: list[dict[str, float | str]] = []

    def _on_window(wid: str, day: float) -> None:
        elapsed = time.time() - t_start
        rss = _peak_rss_mib()
        window_log.append(
            {
                "window": wid,
                "elapsed_s": round(elapsed, 1),
                "peak_rss_mib": round(rss, 1),
            }
        )
        _log(
            f"  members solved: {wid} (day {day:.0f}); elapsed {elapsed:.0f} s, "
            f"peak RSS {rss:.0f} MiB"
        )
        if monitor_flag_s is not None and elapsed > monitor_flag_s:
            _log(
                f"  ⚑ MONITOR FLAG: elapsed {elapsed:.0f} s exceeds "
                f"1.5x amended estimate ({monitor_flag_s:.0f} s) — owner "
                "informed at the pack; run continues (flag, never a kill)"
            )

    esc: dict[str, Any] = {}
    for cap in CAPS:
        method = Miost(plan=plan, pcg_rtol=RTOL, pcg_maxiter=cap)
        CONVERGENCE_LOG.clear()
        spec, etas_a, anoms, starts = merged_members(
            method,
            obs,
            grid,
            provider,
            M_MEMBERS,
            root,
            on_window=lambda wid, day: _on_window(wid, day),
        )
        batches = [dict(e) for e in CONVERGENCE_LOG if e.get("kind") == "member-batch"]
        worst = max(float(cast("float", b["final_rel_residual"])) for b in batches)
        esc = {
            "converged": worst <= RTOL,
            "maxiter_used": cap,
            "member_batches": batches,
        }
        if esc["converged"]:
            break
        _log(f"under-converged at cap {cap} (worst {worst:.2e}) — escalating")
    if not esc["converged"]:
        raise SystemExit(
            "STOPPED: member batches under-converged at every cap — biased "
            "draws are not acceptable (spec 6.5); owner call"
        )

    means = mean_fields(spec, starts, etas_a, grid, plan, days)
    stds = std_fields(spec, starts, anoms, grid, plan, days)
    mdt = load_mdt_grid([Path(p) for p in scope.mdt_paths], grid)
    mean_stack = means.reshape(len(days), *grid.shape) + mdt[None]
    var_stack = (stds**2).reshape(len(days), *grid.shape)
    epoch = np.datetime64("2017-01-01")
    times = epoch + np.asarray(days, dtype="int64") * np.timedelta64(1, "D")
    assimilated = tuple(sorted({str(x) for x in np.asarray(obs.mission)}))
    write_map(
        times, grid.y, grid.x, mean_stack, mean_out, assimilated_missions=assimilated
    )
    write_map(
        times, grid.y, grid.x, var_stack, var_out, assimilated_missions=assimilated
    )
    _log(f"maps written: {mean_out.name}, {var_out.name}")

    if member_store_out is not None:
        raw = MiostEnsembleDistribution(
            grid=grid,
            mean=means[0].reshape(grid.shape),
            provenance=ensemble_provenance(M_MEMBERS),
            time_days=float(days[0]),
            m=M_MEMBERS,
            _spec=spec,
            _etas_a=etas_a,
            _anoms=anoms,
            _window_starts=starts,
            _w_days=plan.w_days,
        )
        wrapped = CalibratedDistribution(raw, cal, UncertaintyCapability.SAMPLES)
        wrapped.save_state(member_store_out)
        _log(f"member store written: {member_store_out.name} (cal_key included)")

    return {
        "converged": True,
        "maxiter_used": esc["maxiter_used"],
        "member_batches": esc["member_batches"],
        "n_obs": n_obs,
        "n_days": len(days),
        "n_windows": len(plan.windows),
        "assimilated_missions": list(assimilated),
        "wall_s": round(time.time() - t_start, 1),
        "peak_rss_mib": round(_peak_rss_mib(), 1),
        "m": M_MEMBERS,
        "pcg_rtol": RTOL,
        "budget_caps": list(CAPS),
        "per_window_log": window_log,
        "monitor_flag_s": monitor_flag_s,
        "monitor_flag_tripped": bool(
            monitor_flag_s is not None
            and any(float(w["elapsed_s"]) > monitor_flag_s for w in window_log)
        ),
    }


def report_rows_block(mean_maps: Path) -> dict[str, Any]:
    """GroundTrack + SpectralFidelity rows on the six-mission mean maps."""
    import xarray as xr

    from sverdrup.application.eval_context import (
        build_eval_context,
        build_report_rows,
        default_registry,
    )

    with xr.open_dataset(mean_maps) as ds:
        fields = np.asarray(ds["ssh"].values, dtype=float)
        lon = np.asarray(ds["lon"].values, dtype=float)
        lat = np.asarray(ds["lat"].values, dtype=float)
        missions_attr = str(ds.attrs["assimilated_missions"])
    built = build_eval_context(
        {"fields": fields, "grid_lon": lon, "grid_lat": lat},
        field_kind="mean",
        geometry_artifact=GEOMETRY,
        assimilated_missions=missions_attr,
    )
    rows = build_report_rows(default_registry(), built.result, built.context)
    return {
        "rows": rows,
        "standing_baseline_note": (
            "five-mission MIOST track_excess_log10 max repeat = 0.410 "
            "(s3a/desc) — the Phase-11 standing baseline, read beside"
        ),
    }


def deltas_block(mean6: Path, var6: Path, scope: Phase12Scope) -> dict[str, Any]:
    """Mean/σ deltas vs the shipped five-mission product + the σ-signature read.

    The Δσ j3-track-localization read is the PRE-REGISTERED structural
    signature (fork c): j3 assimilation must reduce σ preferentially along
    j3 tracks. localization_ratio = median(Δσ on-track) / median(Δσ
    off-track) with Δσ = σ5 − σ6 (positive = reduction), on-track = grid
    node within ON_TRACK_DEG of a j3 obs point.

    Returns:
        Delta block including ``sigma_signature_present``.
    """
    import xarray as xr
    from scipy.spatial import cKDTree  # type: ignore[import-untyped]

    with xr.open_dataset(mean6) as d6, xr.open_dataset(FIVE_MEAN) as d5:
        common = np.intersect1d(d6["time"].values, d5["time"].values)
        a6 = np.asarray(d6.sel(time=common)["ssh"].values, float)
        a5 = np.asarray(d5.sel(time=common)["ssh"].values, float)
        lon = np.asarray(d6["lon"].values, float)
        lat = np.asarray(d6["lat"].values, float)
    dmean = a6 - a5
    mean_delta = {
        "n_common_days": int(common.size),
        "rms": float(np.sqrt(np.nanmean(dmean**2))),
        "max_abs": float(np.nanmax(np.abs(dmean))),
        "map_rms_per_day_median": float(
            np.median(np.sqrt(np.nanmean(dmean**2, axis=(1, 2))))
        ),
    }

    with xr.open_dataset(var6) as v6, xr.open_dataset(FIVE_VAR) as v5:
        commonv = np.intersect1d(v6["time"].values, v5["time"].values)
        s6 = np.sqrt(np.asarray(v6.sel(time=commonv)["ssh"].values, float))
        s5 = np.sqrt(np.asarray(v5.sel(time=commonv)["ssh"].values, float))
    dsig = np.nanmean(s5 - s6, axis=0)  # (lat, lon); positive = reduction

    # On-track mask from the run's own j3 obs points.
    j3_paths = [p for p in scope.mapping_obs_paths if "_j3_" in p.name]
    obs = load_obs_for(scope, j3_paths)
    coords = obs.coords()
    glon, glat = np.meshgrid(lon, lat)
    tree = cKDTree(np.c_[coords[:, 0], coords[:, 1]])
    dist, _ = tree.query(np.c_[glon.ravel(), glat.ravel()])
    on_track = (dist <= ON_TRACK_DEG).reshape(glat.shape)
    med_on = float(np.nanmedian(dsig[on_track]))
    med_off = float(np.nanmedian(dsig[~on_track]))
    ratio = med_on / med_off if med_off > 0 else float("inf") if med_on > 0 else 0.0
    sigma_delta = {
        "n_common_days": int(commonv.size),
        "sigma_reduction_median_on_track": med_on,
        "sigma_reduction_median_off_track": med_off,
        "localization_ratio": ratio,
        "on_track_deg": ON_TRACK_DEG,
        "n_on_track_nodes": int(on_track.sum()),
        "sigma_signature_present": bool(ratio > 1.0),
    }
    return {"mean": mean_delta, "sigma": sigma_delta}


def tier3_block(mean6: Path) -> dict[str, Any]:
    """RMS + along-lon coherence vs the pinned CLS MIOST maps (diag method).

    Mirrors ``diag_miost_tier3.py`` exactly (inner-join days, regrid to their
    0.1° grid, mid-lat band coherence, nperseg 64) so the six-mission row is
    comparable to the anchored five-mission row.
    """
    import math

    import xarray as xr
    from scipy import signal  # type: ignore[import-untyped]

    ours = xr.open_dataset(mean6)
    theirs = xr.open_dataset(TIER3_THEIRS)
    common = np.intersect1d(ours["time"].values, theirs["time"].values)
    ours = ours.sel(time=common)
    theirs = theirs.sel(time=common)
    if (ours.sizes["lat"], ours.sizes["lon"]) != (
        theirs.sizes["lat"],
        theirs.sizes["lon"],
    ):
        ours = ours.interp(lat=theirs["lat"], lon=theirs["lon"], method="linear")
    a = np.asarray(ours["ssh"], float)
    b = np.asarray(theirs["ssh"], float)
    finite = np.isfinite(a) & np.isfinite(b)
    diff = np.where(finite, a - b, np.nan)
    rms_mean = float(np.sqrt(np.nanmean(diff**2)))

    lat = np.asarray(theirs["lat"], float)
    band = (lat >= LAT_BAND[0]) & (lat <= LAT_BAND[1])
    dx_km = (
        float(np.diff(np.asarray(theirs["lon"], float)).mean())
        * KM_PER_DEG
        * math.cos(math.radians(0.5 * (LAT_BAND[0] + LAT_BAND[1])))
    )
    cxy_sum: np.ndarray | None = None
    n_rows = 0
    f = np.array([])
    for it in range(0, a.shape[0], max(1, a.shape[0] // 60)):
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
        raise SystemExit("tier3: no finite mid-lat rows to compare")
    cxy_mean = cxy_sum / n_rows
    wavelength = np.where(f > 0, 1.0 / np.maximum(f, 1e-12), np.inf)

    def _coh_at(lam_km: float) -> float:
        return float(np.interp(lam_km, wavelength[::-1], cxy_mean[::-1]))

    return {
        "rms_mean": rms_mean,
        "coherence": {
            "100km": _coh_at(100.0),
            "150km": _coh_at(150.0),
            "200km": _coh_at(200.0),
        },
        "n_common_days": int(common.size),
        "n_coherence_rows": n_rows,
        "anchor_five_mission": dict(TIER3_ANCHOR),
    }


def run_main(scope_path: Path, signed_record: Path) -> None:
    """The one authorized full-year six-mission evidence run (Task 7 body).

    Refuses to launch without the recorded budget derivation (obligation 4).
    Writes each pack leg incrementally; provenance LAST; STOPs nonzero when
    the σ structural signature is absent (spec §4b').
    """
    scope = load_phase12_scope(scope_path)
    evidence = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    budget = evidence.get("phase12", {}).get("miost6", {}).get("budget")
    if not budget:
        raise SystemExit(
            "REFUSED: phase12.miost6.budget absent — run --smoke first; the "
            "launch is blocked on the recorded budget derivation (obligation 4)"
        )
    winner = assert_winner_matches_signed(signed_record)
    amended = budget.get("amended") or {}
    _log(
        "LAUNCH: budget recorded — sealed template "
        f"(t_full_est_s={budget.get('t_full_est_s')}, "
        f"peak_est_mib={budget.get('peak_est_mib')}, "
        f"launch_ok={budget.get('launch_ok_sealed', budget.get('launch_ok'))}); "
        f"amended per owner T7 adjudication "
        f"(t_full_est_s={amended.get('t_full_est_s')}, "
        f"peak_est_mib={amended.get('peak_est_mib')}, "
        f"launch_ok={budget.get('launch_ok')}); winner params verified "
        f"against the signed record: {winner}"
    )
    if not budget.get("launch_ok"):
        raise SystemExit("REFUSED: recorded budget derivation says launch_ok=false")
    monitor_flag_s = amended.get("monitor_flag_s")

    write_pack_entry(
        RESULTS,
        f"{MIOST6_PREFIX}.geometry",
        {"sha256": sha256_file(GEOMETRY), "path": str(GEOMETRY)},
    )

    days = [float(d) for d in range(365)]
    telemetry = solve_maps(
        scope,
        days,
        scope.mean_map_out,
        scope.var_map_out,
        scope.member_store_out,
        monitor_flag_s=monitor_flag_s,
    )
    write_pack_entry(RESULTS, f"{MIOST6_PREFIX}.telemetry", telemetry)
    _log("telemetry recorded")

    rows = report_rows_block(scope.mean_map_out)
    write_pack_entry(RESULTS, f"{MIOST6_PREFIX}.report_rows", rows)
    _log("report rows recorded")

    deltas = deltas_block(scope.mean_map_out, scope.var_map_out, scope)
    write_pack_entry(RESULTS, f"{MIOST6_PREFIX}.deltas", deltas)
    if not deltas["sigma"]["sigma_signature_present"]:
        print(
            "STOP: sigma-signature ABSENT — attribute before any touch (spec §4b')",
            flush=True,
        )
        raise SystemExit(3)
    _log(
        "deltas recorded; sigma signature PRESENT "
        f"(localization ratio {deltas['sigma']['localization_ratio']:.3f})"
    )

    tier3 = tier3_block(scope.mean_map_out)
    write_pack_entry(RESULTS, f"{MIOST6_PREFIX}.tier3", tier3)
    _log("tier3 recorded")

    cal = shipped_calibration()
    prov = provenance_block(
        mean_maps=scope.mean_map_out,
        var_maps=scope.var_map_out,
        member_store=scope.member_store_out,
        cal_key=cal.key(),
        scope_cfg=scope_path,
        geometry_artifact=GEOMETRY,
    )
    prov["written_utc"] = datetime.now(UTC).isoformat()
    write_pack_entry(RESULTS, f"{MIOST6_PREFIX}.provenance", prov)
    _log("provenance recorded LAST — pack complete; c2 NOT touched")


def _mem_available_mib() -> float:
    """MemAvailable from /proc/meminfo [MiB]."""
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return float(line.split()[1]) / 1024.0
    raise SystemExit("MemAvailable not found in /proc/meminfo")


def smoke_main(scope_path: Path) -> None:
    """--smoke: the six-job dev list on the 12-day scope (plan Task 6; spec §4).

    Evidence-dest isolation (job 6): every smoke record lands under
    ``phase12_dev_smoke.*``; the ONE cross-over is ``phase12.miost6.budget``
    (recorded with ``source: dev_smoke``) — the derivation that unblocks
    ``--run``. Smoke maps go to ``phase12_dev_smoke_{mean,var}_maps.nc``.

    Raises:
        SystemExit: Naming the failing job, or reporting LAUNCH criteria.
    """
    from sverdrup.application.tuning.feasibility import PeakFeasibility
    from sverdrup.methods.miost import _window_mask
    from sverdrup.methods.miost_windows import WindowPlan
    from sverdrup.validation.params import baseline_config
    from sverdrup.validation.phase12_config import (
        NO_VALIDATION_REFUSAL,
        Phase12ConfigError,
    )
    from sverdrup.validation.phase12_config import (
        load_phase12_scope as _load,
    )
    from sverdrup.validation.provenance_guard import (
        TrainScoreLeakError,
        assert_scored_not_assimilated,
        read_assimilated,
    )

    scope = load_phase12_scope(scope_path)
    pre_keys = set(
        (json.loads(RESULTS.read_text()) if RESULTS.exists() else {})
        .get("phase12", {})
        .get("miost6", {})
    )

    import tempfile

    # Job 2: declared-null schema round-trip.
    raw = json.loads(Path(scope_path).read_text())
    with tempfile.TemporaryDirectory() as td:
        broken = dict(raw)
        del broken["val_track_path"]
        p = Path(td) / "missing.json"
        p.write_text(json.dumps(broken))
        try:
            _load(p)
            raise SystemExit("SMOKE FAIL job2: missing val_track_path accepted")
        except Phase12ConfigError as exc:
            if "val_track_path" not in str(exc):
                raise SystemExit("SMOKE FAIL job2: missing-key error unnamed") from exc
        nonnull = dict(raw)
        nonnull["val_track_path"] = str(scope.c2_track_path)
        p2 = Path(td) / "nonnull.json"
        p2.write_text(json.dumps(nonnull))
        try:
            _load(p2)
            raise SystemExit("SMOKE FAIL job2: non-null val_track_path accepted")
        except Phase12ConfigError as exc:
            if str(exc) != NO_VALIDATION_REFUSAL:
                raise SystemExit("SMOKE FAIL job2: refusal text drifted") from exc
    write_pack_entry(
        RESULTS,
        f"{DEV_SMOKE_KEY}.schema_roundtrip",
        {"missing_key_refused": True, "non_null_refused": True},
    )
    _log("smoke job 2 PASS: declared-null schema round-trip")

    # Job 3: geometry artifact present + j3 repeat-classified (NO re-derivation).
    if not GEOMETRY.exists():
        raise SystemExit("SMOKE FAIL job3: geometry artifact absent — run Task 4")
    art = json.loads(GEOMETRY.read_text())
    fams = art["missions"].get("j3")
    if not fams or any(fams[f]["orbit_class"] != "repeat" for f in ("asc", "desc")):
        raise SystemExit("SMOKE FAIL job3: j3 not repeat-classified in artifact")
    if not art.get("key"):
        raise SystemExit("SMOKE FAIL job3: artifact stored key missing")
    write_pack_entry(
        RESULTS,
        f"{DEV_SMOKE_KEY}.geometry_present",
        {
            "sha256": sha256_file(GEOMETRY),
            "j3_orbit_class": {f: fams[f]["orbit_class"] for f in ("asc", "desc")},
            "j3_classifier_ratio": {
                f: fams[f]["classifier_ratio"] for f in ("asc", "desc")
            },
        },
    )
    _log("smoke job 3 PASS: geometry present, j3 repeat both families")

    # Job 4: CRN shared-mission assert (s3a).
    crn = crn_shared_mission_assert(scope)
    write_pack_entry(RESULTS, f"{DEV_SMOKE_KEY}.crn", crn)
    _log("smoke job 4 PASS: CRN s3a bit-equal")

    # Job 5 solve: smoke windows only (those covering the 12-day dev scope).
    full_plan = WindowPlan()
    smoke_starts = tuple(
        sorted({w.start_day for d in scope.smoke_days for w in full_plan.covering(d)})
    )
    smoke_plan = WindowPlan(starts=smoke_starts)
    smoke_mean = OURS / "phase12_dev_smoke_mean_maps.nc"
    smoke_var = OURS / "phase12_dev_smoke_var_maps.nc"
    telemetry = solve_maps(
        scope, list(scope.smoke_days), smoke_mean, smoke_var, None, plan=smoke_plan
    )
    write_pack_entry(RESULTS, f"{DEV_SMOKE_KEY}.telemetry", telemetry)

    # Job 1: guard refusal on the smoke six-mission map (needs the map).
    j3_path = next(p for p in scope.mapping_obs_paths if "_j3_" in p.name)
    try:
        assert_scored_not_assimilated(smoke_mean, j3_path)
        raise SystemExit("SMOKE FAIL job1: j3 scoring of the six-mission map PASSED")
    except TrainScoreLeakError:
        pass
    assimilated = read_assimilated(smoke_mean) or ()
    if "c2" in assimilated:
        raise SystemExit("SMOKE FAIL job1: c2 in assimilated attr")
    write_pack_entry(
        RESULTS,
        f"{DEV_SMOKE_KEY}.guard_refusal",
        {
            "j3_scoring_refused": True,
            "c2_scoring_permitted_by_attr": True,
            "assimilated": list(assimilated),
        },
    )
    _log("smoke job 1 PASS: j3-scoring refused; c2 permitted by attr logic")

    # Job 5 budget derivation (obligation 4, template verbatim).
    _, grid, _ = baseline_config()
    obs_halo = load_obs_for(scope)
    n_obs_full = len(obs_halo)
    l_t = float(WINNER_PARAMS["l_t_days"])
    per_window_counts = {
        f"{w.start_day:g}": int(_window_mask(obs_halo, w, l_t).sum())
        for w in full_plan.windows
    }
    n_obs_smoke = max(
        int(_window_mask(obs_halo, w, l_t).sum()) for w in smoke_plan.windows
    )
    n_obs_max_window = max(per_window_counts.values())
    n_windows_smoke = len(smoke_plan.windows)
    n_windows_full = len(full_plan.windows)
    t_window_smoke = telemetry["wall_s"] / n_windows_smoke
    t_full_est = t_window_smoke * n_windows_full * (n_obs_full / n_obs_smoke)
    g_full_per_window_gb = 0.78 * (n_obs_full / 54_345)
    peak = PeakFeasibility(
        n_obs_max=n_obs_max_window,
        m=M_MEMBERS,
        n_grid_nodes=int(grid.shape[0] * grid.shape[1]),
    )
    peak_est_mib = peak.predicted_peak_bytes(dict(WINNER_PARAMS)) * 1.11 / 2**20
    mem_avail_mib = _mem_available_mib()
    launch_ok = bool(peak_est_mib <= 0.5 * mem_avail_mib and t_full_est <= 12 * 3600)
    budget = {
        "source": "dev_smoke",
        "n_obs_smoke": n_obs_smoke,
        "n_obs_full": n_obs_full,
        "n_obs_max_window": n_obs_max_window,
        "per_window_obs": per_window_counts,
        "t_window_smoke_s": round(t_window_smoke, 1),
        "peak_rss_smoke_mib": telemetry["peak_rss_mib"],
        "n_windows_smoke": n_windows_smoke,
        "n_windows_full": n_windows_full,
        "g_full_per_window_gb": round(g_full_per_window_gb, 3),
        "t_full_est_s": round(t_full_est, 1),
        "peak_est_mib": round(peak_est_mib, 1),
        "peak_model": "PeakFeasibility.predicted_peak_bytes x 1.11 (Task-22)",
        "mem_available_mib": round(mem_avail_mib, 1),
        "launch_rule": "peak_est <= 0.5*MemAvailable AND t_full_est <= 12 h",
        "launch_ok": launch_ok,
    }
    write_pack_entry(RESULTS, f"{MIOST6_PREFIX}.budget", budget)
    _log(
        f"smoke job 5 PASS: budget recorded (t_full_est {t_full_est / 3600:.2f} h, "
        f"peak_est {peak_est_mib:.0f} MiB vs avail {mem_avail_mib:.0f} MiB)"
    )

    # Job 6: dest isolation — smoke added NOTHING to phase12.miost6 but budget.
    post = json.loads(RESULTS.read_text())
    post_keys = set(post.get("phase12", {}).get("miost6", {}))
    added = post_keys - pre_keys
    if added - {"budget"}:
        raise SystemExit(f"SMOKE FAIL job6: smoke wrote miost6 keys {sorted(added)}")
    if post["phase12"]["miost6"]["budget"].get("source") != "dev_smoke":
        raise SystemExit("SMOKE FAIL job6: budget missing source=dev_smoke")
    write_pack_entry(
        RESULTS,
        f"{DEV_SMOKE_KEY}.dest_isolation",
        {
            "miost6_keys_added": sorted(added),
            "smoke_maps": [str(smoke_mean), str(smoke_var)],
        },
    )
    _log("smoke job 6 PASS: dest isolation held")

    verdict = "met" if launch_ok else "NOT met"
    print(
        f"SMOKE: 6/6 jobs PASS; budget recorded; LAUNCH criteria {verdict}",
        flush=True,
    )
    if not launch_ok:
        raise SystemExit(4)


# ---------------------------------------------------------------------------
# T8 — the ONE c2 touch (owner-authorized 2026-07-18; ceremony verbatim)
# ---------------------------------------------------------------------------

C2_FLAG = "SVERDRUP_MIOST_C2"
C2_CORRECTED_FLAG = "SVERDRUP_MIOST_C2_CORRECTED"
DEFECT_KEY_PREFIX = "c2_defect_run_"
N_C2_FULL_YEAR = 44_844  # spec §5: the Task-19 signed full-year c2 count
CHALLENGE_TMIN = np.datetime64("2017-01-01")
CHALLENGE_TMAX = np.datetime64("2018-01-01")
_COVER_MIN = np.datetime64("2017-01-31")  # loaded min must be ≤ end of Jan
_COVER_MAX = np.datetime64("2017-12-01")  # loaded max must be ≥ start of Dec
TALLY = {"miost5": 2, "miost6": 1}
COVERAGE_BASELINE = 0.7350370172152351  # field-calibrated c2 aggregate (miost5)
COVERAGE_BASELINE_SCALAR_ERA = 0.7481
MU_HARD_FLOOR = 0.85


def check_authorized(env: dict[str, str] | None = None) -> None:
    """Fresh authorization: exact-string SVERDRUP_MIOST_C2 == "1" only.

    Args:
        env: Environment mapping (defaults to ``os.environ``).

    Raises:
        SystemExit: Any other value; no data loaded.
    """
    import os

    e = os.environ if env is None else env
    if e.get(C2_FLAG) != "1":
        raise SystemExit(
            f"REFUSED: set {C2_FLAG}=1 exactly (owner-gated touch; fresh "
            "authorization required). No data loaded."
        )


def check_touch_protocol(
    evidence: dict[str, Any], env: dict[str, str] | None = None
) -> None:
    """One-invocation mechanics (phase8 owner-rider-3 matrix, phase12 keys).

    C = corrected flag set, A = ``phase12.miost6.c2_acceptance`` present,
    D = any ``c2_defect_run_<date>`` key present:

    unset C:  A -> REFUSE (one-touch spent); no A -> PROCEED (first touch).
    set C:    A, no D -> PROCEED (migrate then re-evaluate);
              no A, D -> PROCEED (resume);
              A and D -> REFUSE (third invocation);
              neither -> REFUSE (flag invalid without a recorded defect).

    Args:
        evidence: The parsed phase12 evidence JSON.
        env: Environment mapping (defaults to ``os.environ``).

    Raises:
        SystemExit: On every REFUSE row; no data loaded.
    """
    import os

    e = os.environ if env is None else env
    corrected = e.get(C2_CORRECTED_FLAG) == "1"
    m = evidence.get("phase12", {}).get("miost6", {})
    acceptance = "c2_acceptance" in m
    defect = any(k.startswith(DEFECT_KEY_PREFIX) for k in m)

    if not corrected:
        if acceptance:
            raise SystemExit(
                "REFUSED: phase12.miost6.c2_acceptance already exists — the "
                "ONE touch is spent. A corrected re-touch requires "
                f"{C2_CORRECTED_FLAG}=1 + a dated defect key. No data loaded."
            )
        return  # first touch — the authorized invocation
    if acceptance and defect:
        raise SystemExit(
            "REFUSED: third invocation — c2_acceptance exists alongside a "
            "defect key; further touches are owner-gated. No data loaded."
        )
    if not acceptance and not defect:
        raise SystemExit(
            f"REFUSED: {C2_CORRECTED_FLAG}=1 is invalid without a recorded "
            "defect — nothing to correct. No data loaded."
        )
    # PROCEED rows: (A, no D) migrate-then-evaluate; (no A, D) resume.


def migrate_defect_run(evidence: dict[str, Any], date_str: str) -> bool:
    """Rename a defect-run acceptance to the dated defect key (in place).

    Args:
        evidence: The parsed phase12 evidence JSON (mutated).
        date_str: Migration date, ``YYYYMMDD``.

    Returns:
        True when a migration happened; False on the resume no-op.
    """
    m = evidence.setdefault("phase12", {}).setdefault("miost6", {})
    if any(k.startswith(DEFECT_KEY_PREFIX) for k in m) or "c2_acceptance" not in m:
        return False
    blk = m.pop("c2_acceptance")
    if isinstance(blk, dict):
        blk["defect"] = "defect run migrated; numbers are context, never evidence"
        blk["defect_recorded"] = date_str
    m[f"{DEFECT_KEY_PREFIX}{date_str}"] = blk
    return True


def window_tripwire(n_points: int, times: np.ndarray) -> dict[str, Any]:
    """Assert the loaded c2 set is the FULL challenge year (phase8 template).

    Args:
        n_points: Loaded c2 point count.
        times: Loaded per-point times.

    Returns:
        The passing tripwire record (embedded in the acceptance block).

    Raises:
        SystemExit: On count or span mismatch — record in the message,
            partial-window defect-STOP.
    """
    tt = np.asarray(times, dtype="datetime64[ns]")
    has = bool(tt.size)
    in_bounds = (
        has and bool((tt >= CHALLENGE_TMIN).all()) and bool((tt < CHALLENGE_TMAX).all())
    )
    spans = has and bool(tt.min() <= _COVER_MIN) and bool(tt.max() >= _COVER_MAX)
    n_ok = n_points == N_C2_FULL_YEAR
    record: dict[str, Any] = {
        "passed": bool(n_ok and in_bounds and spans),
        "n_points_loaded": int(n_points),
        "n_points_expected": N_C2_FULL_YEAR,
        "in_challenge_bounds": in_bounds,
        "spans_challenge_year": spans,
        "loaded_time_min": str(tt.min()) if has else None,
        "loaded_time_max": str(tt.max()) if has else None,
    }
    if not record["passed"]:
        raise SystemExit(
            "WINDOW-TRIPWIRE defect-STOP: loaded c2 set is not the full "
            f"challenge year — n_points={n_points} (expected "
            f"{N_C2_FULL_YEAR}), span ok={spans}, bounds ok={in_bounds}. "
            f"Record: {json.dumps(record)}"
        )
    return record


def provenance_tripwire(
    recorded: dict[str, Any],
    mean_maps: Path,
    var_maps: Path,
    member_store: Path,
    cal_key: str,
    scope_cfg: Path,
    geometry_artifact: Path,
) -> None:
    """Recompute ALL SIX provenance fields from disk; refuse on any mismatch.

    Runs BEFORE the c2 file is opened. Never a re-solve — a mismatch is an
    attribution task, not a regeneration order.

    Args:
        recorded: The provenance block the evidence run persisted.
        mean_maps: On-disk mean maps to re-hash.
        var_maps: On-disk var maps to re-hash.
        member_store: On-disk member store to re-hash.
        cal_key: The factory field's live cal_key.
        scope_cfg: The scope JSON to re-hash.
        geometry_artifact: The geometry artifact to re-hash.

    Raises:
        ValueError: Naming every mismatched field (assert_provenance_matches).
    """
    from sverdrup.validation.phase12_evidence import assert_provenance_matches

    recomputed = provenance_block(
        mean_maps=mean_maps,
        var_maps=var_maps,
        member_store=member_store,
        cal_key=cal_key,
        scope_cfg=scope_cfg,
        geometry_artifact=geometry_artifact,
    )
    assert_provenance_matches(recorded, recomputed)


def _interp_c2(mean_nc: Path, var_nc: Path, c2_track: Path) -> tuple[np.ndarray, ...]:
    """Interp mean/var maps on the c2 track over the FULL challenge year.

    The one place in this script that opens the c2 file. Both maps carry the
    provenance guard first.

    Returns:
        (lon, lat, time, resid, v) finite/positive-var masked arrays.
    """
    import sverdrup.validation.their_eval as te
    from sverdrup.validation.provenance_guard import assert_scored_not_assimilated

    assert_scored_not_assimilated(mean_nc, c2_track)
    assert_scored_not_assimilated(var_nc, c2_track)
    te._prepare_imports()
    from src.mod_inout import read_l3_dataset
    from src.mod_interp import interp_on_alongtrack

    box = dict(
        lon_min=295.0,
        lon_max=305.0,
        lat_min=33.0,
        lat_max=43.0,
        time_min="2017-01-01",
        time_max="2018-01-01",
    )
    ds_at = read_l3_dataset(str(c2_track), **box)
    time_a, lat_a, lon_a, ssh, mu = interp_on_alongtrack(
        str(mean_nc), ds_at, is_circle=False, **box
    )
    _, _, _, _, var = interp_on_alongtrack(str(var_nc), ds_at, is_circle=False, **box)
    ssh, mu, var = (np.asarray(a, float) for a in (ssh, mu, var))
    lon_a, lat_a = np.asarray(lon_a, float), np.asarray(lat_a, float)
    time_a = np.asarray(time_a)
    ok = np.isfinite(ssh) & np.isfinite(mu) & np.isfinite(var) & (var > 0)
    return lon_a[ok], lat_a[ok], time_a[ok], (ssh - mu)[ok], var[ok]


def _cal_stats(resid: np.ndarray, vt: np.ndarray) -> dict[str, float]:
    """Coverage / reduced chi2 / CRPS on a calibrated track variance."""
    import math

    band = np.sqrt(vt)
    sigma = band
    z = resid / sigma
    phi = np.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
    cdf = 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2.0)))
    crps = sigma * (z * (2.0 * cdf - 1.0) + 2.0 * phi - 1.0 / math.sqrt(math.pi))
    return {
        "n": int(resid.size),
        "coverage": float(np.count_nonzero(np.abs(resid) <= band) / resid.size),
        "reduced_chi2": float(np.mean(resid**2 / vt)),
        "crps": float(np.mean(crps)),
    }


def c2_touch_main(scope_path: Path, signed_record: Path) -> None:
    """The ONE c2 touch (T8; owner-authorized fresh 2026-07-18).

    Ceremony order: authorization -> protocol matrix -> provenance tripwire
    (all six fields, BEFORE the c2 file opens; never a re-solve) -> c2 load
    with the provenance guard -> window tripwire -> the sealed reading ->
    one write of ``phase12.miost6.c2_acceptance``.

    Args:
        scope_path: The phase12 scope JSON (hashed in the closed input set).
        signed_record: The signed gate evidence JSON (winner-params assert).
    """
    from datetime import UTC, datetime

    from sverdrup.application.calibration import regions as R
    from sverdrup.application.calibration.constants import (
        COVERAGE_TARGET,
        COVERAGE_TOL,
        SIGMA_OBS2,
    )
    from sverdrup.validation.their_eval import score as their_score

    check_authorized()
    evidence = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    check_touch_protocol(evidence)
    scope = load_phase12_scope(scope_path)
    assert_winner_matches_signed(signed_record)
    cal = shipped_calibration()

    m6 = evidence.get("phase12", {}).get("miost6", {})
    recorded_prov = m6.get("provenance")
    if not recorded_prov:
        raise SystemExit("REFUSED: phase12.miost6.provenance absent — run --run first")
    provenance_tripwire(
        recorded_prov,
        mean_maps=scope.mean_map_out,
        var_maps=scope.var_map_out,
        member_store=scope.member_store_out,
        cal_key=cal.key(),
        scope_cfg=scope_path,
        geometry_artifact=GEOMETRY,
    )
    _log("provenance tripwire PASS (all six fields recomputed, bit-match)")

    date_str = datetime.now(UTC).strftime("%Y%m%d")
    if migrate_defect_run(evidence, date_str):
        write_pack_entry(
            RESULTS,
            f"{MIOST6_PREFIX}.{DEFECT_KEY_PREFIX}{date_str}",
            evidence["phase12"]["miost6"][f"{DEFECT_KEY_PREFIX}{date_str}"],
        )
        _log(f"defect run migrated to {DEFECT_KEY_PREFIX}{date_str}")

    _log("opening the c2 track (the ONE authorized touch)")
    lon, lat, tt, resid, v = _interp_c2(
        scope.mean_map_out, scope.var_map_out, scope.c2_track_path
    )
    tripwire = window_tripwire(int(resid.size), tt)
    _log(f"window tripwire PASS (n={resid.size}, full challenge year)")

    triplet = [float(x) for x in their_score(scope.mean_map_out, scope.c2_track_path)]
    vt = (cal.sqrt_s_at(lon, lat) ** 2) * v + SIGMA_OBS2
    aggregate = _cal_stats(resid, vt)

    jet_cells = np.asarray(
        json.loads((OURS / "phase8_jet_core_mask.json").read_text())["mask"],
        dtype=bool,
    )
    row, col = R.cell_index(lon, lat)
    jet_pts = jet_cells[row, col]
    regional = {}
    for reg, mask in R.evaluation_masks(lon, lat, jet_pts).items():
        if mask.any():
            regional[reg] = _cal_stats(resid[mask], vt[mask])
    months = np.asarray(tt, dtype="datetime64[M]").astype(int) % 12 + 1
    monthly = {
        f"{mo:02d}": _cal_stats(resid[months == mo], vt[months == mo])
        for mo in range(1, 13)
        if (months == mo).any()
    }

    acceptance = {
        "mu_sigma_lambda_x": triplet,
        "aggregate_calibration": aggregate,
        "regional_table": regional,
        "monthly_table": monthly,
        "window_tripwire": tripwire,
        "reading_frame": {
            "coverage_bar": {"target": COVERAGE_TARGET, "tol": COVERAGE_TOL},
            "coverage_baseline_miost5": COVERAGE_BASELINE,
            "coverage_baseline_scalar_era": COVERAGE_BASELINE_SCALAR_ERA,
            "mu_hard_floor": MU_HARD_FLOOR,
            "sigma_convention": "s(x)*v + SIGMA_OBS2 (track-side, phase8)",
        },
        "c2_touch_tally": dict(TALLY),
        "semantics": (
            "the ONE phase-12 c2 touch (owner-authorized fresh 2026-07-18; "
            "everything frozen from the signed record; nothing refit on c2; "
            "three-branch ruling is the owner's message)"
        ),
        "written_utc": datetime.now(UTC).isoformat(),
    }
    write_pack_entry(RESULTS, f"{MIOST6_PREFIX}.c2_acceptance", acceptance)
    _log("c2_acceptance written — the ONE touch is spent")
    print(json.dumps(acceptance, indent=2))


def main() -> None:
    """CLI dispatch."""
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--c2-touch", action="store_true")
    ap.add_argument("--scope", type=Path, default=SCOPE_DEFAULT)
    ap.add_argument(
        "--signed-record",
        type=Path,
        default=None,
        help="signed gate evidence JSON (required for --run; the file name "
        "is deliberately never hard-coded here)",
    )
    args = ap.parse_args()
    if args.smoke:
        smoke_main(args.scope)
    elif args.run:
        if args.signed_record is None:
            raise SystemExit("--run requires --signed-record <signed evidence JSON>")
        run_main(args.scope, args.signed_record)
    else:
        if args.signed_record is None:
            raise SystemExit(
                "--c2-touch requires --signed-record <signed evidence JSON>"
            )
        c2_touch_main(args.scope, args.signed_record)


if __name__ == "__main__":
    main()
