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

from sverdrup.validation.phase12_config import Phase12Scope, load_phase12_scope
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
    from sverdrup.methods.miost import shipped_miost

    cal = shipped_miost()._calibration
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
) -> dict[str, Any]:
    """The frozen-config six-mission solve: members -> day fields -> maps.

    Args:
        scope: The validated phase12 scope.
        days: Output days (smoke: the 12-day list; run: 0..364).
        mean_out: Mean maps NetCDF destination.
        var_out: Variance maps NetCDF destination.
        member_store_out: Member-store npz destination (None = skip, smoke).

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

    plan = WindowPlan()
    provider = ConstantProvider(dict(WINNER_PARAMS))
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
            on_window=lambda wid, day: _log(f"  members solved: {wid} (day {day:.0f})"),
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
    _log(
        "LAUNCH: budget recorded "
        f"(t_full_est_s={budget.get('t_full_est_s')}, "
        f"peak_est_mib={budget.get('peak_est_mib')}, "
        f"launch_ok={budget.get('launch_ok')}); winner params verified "
        f"against the signed record: {winner}"
    )
    if not budget.get("launch_ok"):
        raise SystemExit("REFUSED: recorded budget derivation says launch_ok=false")

    write_pack_entry(
        RESULTS,
        f"{MIOST6_PREFIX}.geometry",
        {"sha256": sha256_file(GEOMETRY), "path": str(GEOMETRY)},
    )

    days = [float(d) for d in range(365)]
    telemetry = solve_maps(
        scope, days, scope.mean_map_out, scope.var_map_out, scope.member_store_out
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


def smoke_main(scope_path: Path) -> None:
    """--smoke arrives in Task 6."""
    raise SystemExit("REFUSED: --smoke is implemented in Task 6")


def c2_touch_main() -> None:
    """--c2-touch arrives in Task 8 (fresh owner authorization required)."""
    raise SystemExit(
        "REFUSED: --c2-touch is not implemented until T8 (the ONE touch "
        "requires fresh owner authorization; zero c2 before then)"
    )


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
        c2_touch_main()


if __name__ == "__main__":
    main()
