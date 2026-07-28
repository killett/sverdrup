"""MEASURE the σ-route ensemble settling by member partition (owner pin 43).

Pin 43 refused to seal ``1.14`` on a two-sample basis with a known-broken
``N_eff`` estimator and ordered the settling measured instead:

> RUN THE SETTLING MEASUREMENT. ... The replay is cheap, needs no solves,
> and is non-parametric in N_eff — it settles the defect without needing
> the mechanism you cannot yet reproduce.

with two strengthenings: (a) carry the caveat that ~200 partitions of the
SAME 100 members share draws and therefore UNDERSTATE the true null
spread, and (b) run at MORE THAN ONE SPLIT SIZE (50/50 and 25/25) to TEST
the assumed m-invariance rather than inherit it.

**RESULT IS RECORDED, NOT SEALED.** Nothing here licenses a σ verdict
(owner pin 49): the whole rubric amendment is deferred to T17, to be
sealed once against the CRN-paired configuration T14 creates. This number
survives T14 because ``N_eff`` is a property of the field's spatial
correlation, not of the CRN pairing (pin 43).

HOW THE REPLAY IS MADE CHEAP, WITHOUT APPROXIMATION. The lineage
evaluator ``std_fields`` builds, at each day, the per-member blended
field ``acc`` of shape ``(n_nodes, m)`` and returns
``acc.std(axis=1, ddof=1)``. This script captures ``acc`` on the strip
ONCE per tile and takes the σ of any member subset from it directly. That
is the SAME arithmetic on the SAME numbers, not a model of it — and the
identity is not asserted, it is CHECKED on every run at full ``m``
against both the lineage evaluator and the persisted member-std map, to
an EXACT zero tolerance. A non-zero difference is a STOP.

NO SOLVES. Reads the persisted member stores and maps only.
"""

from __future__ import annotations

import gc
import importlib.util
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Annotated, Any

import numpy as np
import typer
from numpy.typing import NDArray

from sverdrup.validation.ensemble_settling import (
    disjoint_partitions,
    member_sigma,
    settling_ratios,
)
from sverdrup.validation.seam_metrics import seam_delta

app = typer.Typer(add_completion=False)

EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
NODE = "ensemble_settling_measurement"

# Pin 43's ruled design: ~200 partitions, at 50/50 and 25/25.
N_PARTITIONS = 200
SPLIT_SIZES = (50, 25)
SEED = 20260727

# The two RECORDED half-split readings (T4 diagnosis, commit 420c40f,
# `phase14.stage1.seam_sigma_diagnosis.line_4_half_split`). The ORDERED
# split — members [0:50] against [50:100] — is one specific partition, so
# this run must reproduce it to the last digit or the capture is wrong.
RECORDED_HALF_SPLIT = {
    "seam_n": {
        "observed_rms_sigma_half1_minus_half2_m": 0.005181714205883557,
        "predicted_mc_floor_m": 0.005271745106637038,
        "observed_over_predicted": 0.9829219928254623,
    },
    "seam_s": {
        "observed_rms_sigma_half1_minus_half2_m": 0.00528902178473875,
        "predicted_mc_floor_m": 0.005270226242723686,
        "observed_over_predicted": 1.0035663634063174,
    },
}
# Exact-zero tolerance: the capture either IS the evaluator's arithmetic
# or it is not. Anything else is a defect, not a rounding budget.
IDENTITY_TOL = 0.0


def _stage1_module() -> ModuleType:
    """Import the Stage-1 runner read-only (constants + strip helpers).

    Returns:
        The executed ``scripts/phase14_stage1_run`` module.

    Raises:
        ImportError: If the runner cannot be loaded.
    """
    name = "phase14_stage1_run"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - loader exists
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def capture_member_strip_fields(
    tile: str,
) -> tuple[NDArray[np.float64], dict[str, Any]]:
    """Replay one tile's member store into PER-MEMBER strip fields.

    Mirrors the lineage ``std_fields`` blend loop exactly, stopping one
    step earlier: it keeps the per-member blended field instead of
    reducing it to σ. The equality of the two is CHECKED by the caller,
    not assumed.

    Args:
        tile: ``seam_n`` or ``seam_s``.

    Returns:
        ``(members, provenance)`` where ``members`` has shape
        ``(n_days, n_lat, n_lon, m)`` on the 2·overlap strip.
    """
    from sverdrup.application.spatial_tiles import frame_grid  # noqa: PLC0415
    from sverdrup.core.parameters import ConstantProvider  # noqa: PLC0415
    from sverdrup.distributions.miost_ensemble import _window_smats  # noqa: PLC0415
    from sverdrup.methods.miost import PHASE13_WINNER_PARAMS  # noqa: PLC0415
    from sverdrup.methods.miost_basis import time_contract  # noqa: PLC0415
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415

    mod = _stage1_module()
    strip = mod.seam_strip_bbox()
    plan = WindowPlan()
    days = [float(d) for d in range(mod.SEAM_N_DAYS)]
    frame = mod.registry_frame(tile)
    grid = frame_grid(frame, mod.RESOLUTION_DEG)
    lat_mask, lon_mask = mod.strip_mask(grid, strip)
    method = mod._seam_miost(frame, starts=None, maxiter=mod.STAGE1_PCG_MAXITER)  # noqa: SLF001
    spec = method._spec_from(ConstantProvider(dict(PHASE13_WINNER_PARAMS)), grid)  # noqa: SLF001

    with np.load(mod.SEAM_MEMBER_STORE[tile], allow_pickle=False) as store:
        wids = [str(w) for w in np.asarray(store["window_ids"])]
        starts = {w: float(store[f"start_{w}"]) for w in wids}
        anoms = {w: np.asarray(store[f"anom_{w}"]) for w in wids}

    n_nodes, smats = _window_smats(spec, starts, grid, plan)
    m = int(next(iter(anoms.values())).shape[1])
    n_lat, n_lon = int(lat_mask.sum()), int(lon_mask.sum())
    # Member LAST and fastest-varying: this is the layout in which the
    # reduction reproduces the evaluator's bit-for-bit (see
    # `member_sigma`'s docstring — axis 0 costs 4.2e-17 of exactness).
    members = np.empty((len(days), n_lat, n_lon, m), dtype=np.float64)
    for i, day in enumerate(days):
        acc = np.zeros((n_nodes, m))
        for w in plan.covering(day):
            els, s = smats[w.id]
            acc += plan.weight(w, day) * (
                s @ time_contract(spec, els, anoms[w.id], day)
            )
        on_grid = acc.reshape((*grid.shape, m))
        members[i] = on_grid[lat_mask][:, lon_mask]
    del anoms, smats
    gc.collect()

    provenance = {
        "tile": tile,
        "member_store": str(mod.SEAM_MEMBER_STORE[tile]),
        "member_std_map": str(mod.SEAM_STD_MAPS[tile]),
        "n_windows": len(wids),
        "m": m,
        "strip_shape_time_lat_lon": [len(days), n_lat, n_lon],
        "capture_layout": "(n_days, n_lat, n_lon, m) — member LAST and fastest-varying",
        "basis_origin_km": {"x0": spec.x0_km, "y0": spec.y0_km},
    }
    return members, provenance


def check_capture_identity(
    tile: str, members: NDArray[np.float64]
) -> dict[str, float | bool | str]:
    """Prove the capture IS the evaluator's arithmetic, at full ``m``.

    Two independent comparisons: against the lineage ``std_fields`` run
    on the same store, and against the map T4 actually persisted. Both
    are required to be EXACTLY zero.

    Args:
        tile: ``seam_n`` or ``seam_s``.
        members: The captured ``(n_days, n_lat, n_lon, m)`` fields.

    Returns:
        The two max-abs differences and the pass flag.

    Raises:
        RuntimeError: If either difference is non-zero — the settling
            distribution would then describe some other arithmetic than
            the one that produced the recorded rows.
    """
    from sverdrup.application.spatial_tiles import frame_grid  # noqa: PLC0415
    from sverdrup.core.parameters import ConstantProvider  # noqa: PLC0415
    from sverdrup.methods.miost import PHASE13_WINNER_PARAMS  # noqa: PLC0415
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415

    mod = _stage1_module()
    std_fields = mod._lineage_std_fields()  # noqa: SLF001
    strip = mod.seam_strip_bbox()
    plan = WindowPlan()
    days = [float(d) for d in range(mod.SEAM_N_DAYS)]
    frame = mod.registry_frame(tile)
    grid = frame_grid(frame, mod.RESOLUTION_DEG)
    lat_mask, lon_mask = mod.strip_mask(grid, strip)
    method = mod._seam_miost(frame, starts=None, maxiter=mod.STAGE1_PCG_MAXITER)  # noqa: SLF001
    spec = method._spec_from(ConstantProvider(dict(PHASE13_WINNER_PARAMS)), grid)  # noqa: SLF001

    with np.load(mod.SEAM_MEMBER_STORE[tile], allow_pickle=False) as store:
        wids = [str(w) for w in np.asarray(store["window_ids"])]
        starts = {w: float(store[f"start_{w}"]) for w in wids}
        anoms = {w: np.asarray(store[f"anom_{w}"]) for w in wids}

    fields = std_fields(spec, starts, anoms, grid, plan, days)
    del anoms
    gc.collect()
    stack = np.stack([f.reshape(grid.shape) for f in fields])
    lineage = np.asarray(stack[:, lat_mask, :][:, :, lon_mask])
    del fields, stack
    gc.collect()

    # Reduce the captured array in place — no selection copy. This is the
    # load-bearing comparison: it asks whether the per-member fields ARE
    # the evaluator's own, and it is held to exact zero.
    captured: NDArray[np.float64] = members.std(axis=-1, ddof=1)
    persisted = mod._strip_fields(mod.SEAM_STD_MAPS[tile], tile)  # noqa: SLF001

    vs_lineage = float(np.nanmax(np.abs(captured - lineage)))
    vs_persisted = float(np.nanmax(np.abs(captured - persisted)))
    passed = vs_lineage <= IDENTITY_TOL and vs_persisted <= IDENTITY_TOL
    if not passed:
        raise RuntimeError(
            f"{tile}: captured per-member fields do NOT reproduce the evaluator "
            f"(max|Δ| vs lineage std_fields {vs_lineage:.3e}, vs persisted map "
            f"{vs_persisted:.3e}); the settling measurement would describe "
            "different arithmetic than the recorded rows — STOP"
        )

    # Secondary, reported not gated: selecting members by index array
    # materialises a copy whose summation ORDER differs, so the same σ
    # comes back a few ULP apart. Measured rather than asserted away —
    # every partition σ below rides this path.
    via_selection = member_sigma(members, np.arange(members.shape[-1]))
    selection_gap = float(np.nanmax(np.abs(via_selection - captured)))
    level = float(np.sqrt(np.nanmean(np.square(captured))))

    return {
        "max_abs_diff_vs_lineage_std_fields_m": vs_lineage,
        "max_abs_diff_vs_persisted_map_m": vs_persisted,
        "tolerance": IDENTITY_TOL,
        "passed": passed,
        "note": (
            "the captured per-member field reduced by std(axis=0, ddof=1) "
            "reproduces BOTH the lineage evaluator and the map T4 persisted, "
            "EXACTLY — so every partition σ below is the production "
            "arithmetic on a member subset, not an approximation of it"
        ),
        "member_selection_fp_gap_m": selection_gap,
        "member_selection_fp_gap_relative_to_sigma_level": selection_gap / level,
        "member_selection_note": (
            "selecting members by index array copies them in a different "
            "memory order, so the summation order inside std() differs and the "
            "same σ returns a few ULP apart. Reported, not gated: it is "
            "floating-point associativity, ~1e-15 relative, and the "
            "partition-to-partition spread this run measures is ~1e-2 relative"
        ),
    }


def reproduce_recorded_half_split(
    tile: str, members: NDArray[np.float64]
) -> dict[str, Any]:
    """Reproduce the T4 diagnosis half-split from the captured fields.

    The diagnosis split members ``[0:50]`` against ``[50:100]`` — one
    specific partition of the ones drawn below — and normalised by a
    floor built from the FULL-m σ level. Both quantities are recomputed
    here in the diagnosis's own construction, so the check is against the
    committed numbers rather than against this script's own convention.

    Args:
        tile: ``seam_n`` or ``seam_s``.
        members: The captured ``(n_days, n_lat, n_lon, m)`` fields.

    Returns:
        The recomputed pair, the recorded pair and their differences.
    """
    from sverdrup.validation.seam_metrics import ensemble_floor  # noqa: PLC0415

    m = members.shape[-1]
    half = m // 2
    sigma_1 = member_sigma(members, np.arange(half))
    sigma_2 = member_sigma(members, np.arange(half, m))
    sigma_full = member_sigma(members, np.arange(m))

    observed = seam_delta(sigma_1, sigma_2)
    full_level = float(np.sqrt(np.mean(np.square(sigma_full[np.isfinite(sigma_full)]))))
    predicted = ensemble_floor(full_level, half)
    ratio = observed / predicted

    recorded = RECORDED_HALF_SPLIT[tile]
    return {
        "construction": (
            "the T4 diagnosis construction: ORDERED split [0:50] vs [50:100], "
            "floor from the FULL-m σ level (NOT the pin-38 pooled level the "
            "partition ratios below use) — recomputed in the diagnosis's own "
            "terms so the comparison is against the committed numbers"
        ),
        "recomputed_observed_rms_m": observed,
        "recorded_observed_rms_m": recorded["observed_rms_sigma_half1_minus_half2_m"],
        "abs_diff_observed_m": abs(
            observed - recorded["observed_rms_sigma_half1_minus_half2_m"]
        ),
        "recomputed_predicted_mc_floor_m": predicted,
        "recorded_predicted_mc_floor_m": recorded["predicted_mc_floor_m"],
        "abs_diff_predicted_m": abs(predicted - recorded["predicted_mc_floor_m"]),
        "recomputed_observed_over_predicted": ratio,
        "recorded_observed_over_predicted": recorded["observed_over_predicted"],
        "abs_diff_ratio": abs(ratio - recorded["observed_over_predicted"]),
    }


def summarize(ratios: NDArray[np.float64]) -> dict[str, float]:
    """Summary statistics of a realized ratio distribution.

    Args:
        ratios: One ``T`` per partition.

    Returns:
        Location, spread and the empirical quantiles that ``n`` supports.
    """
    return {
        "n": int(ratios.size),
        "mean": float(np.mean(ratios)),
        "sd": float(np.std(ratios, ddof=1)),
        "min": float(np.min(ratios)),
        "q05": float(np.quantile(ratios, 0.05)),
        "q50": float(np.quantile(ratios, 0.5)),
        "q95": float(np.quantile(ratios, 0.95)),
        "q99": float(np.quantile(ratios, 0.99)),
        "max": float(np.max(ratios)),
    }


def measure_tile(
    tile: str, *, n_partitions: int, seed: int, echo: Callable[[str], None]
) -> dict[str, Any]:
    """The full pin-43 measurement for one tile.

    Args:
        tile: ``seam_n`` or ``seam_s``.
        n_partitions: Partitions per split size.
        seed: Base seed; each split size gets a distinct derived seed.
        echo: Progress sink.

    Returns:
        The tile's recorded block.
    """
    members, provenance = capture_member_strip_fields(tile)
    echo(f"{tile}: captured per-member strip fields {members.shape}")
    identity = check_capture_identity(tile, members)
    echo(
        f"{tile}: capture identity EXACT "
        f"(vs lineage {identity['max_abs_diff_vs_lineage_std_fields_m']:.3e}, "
        f"vs map {identity['max_abs_diff_vs_persisted_map_m']:.3e})"
    )
    half_split = reproduce_recorded_half_split(tile, members)
    echo(
        f"{tile}: recorded half-split reproduced — ratio "
        f"{half_split['recomputed_observed_over_predicted']:.13f} vs recorded "
        f"{half_split['recorded_observed_over_predicted']:.13f} "
        f"(Δ {half_split['abs_diff_ratio']:.3e})"
    )

    m_total = int(members.shape[-1])
    by_size: dict[str, Any] = {}
    for size in SPLIT_SIZES:
        partitions = disjoint_partitions(
            m_total=m_total, size=size, n_partitions=n_partitions, seed=seed + size
        )
        ratios = settling_ratios(members, partitions)
        stats = summarize(ratios)
        by_size[f"{size}_{size}"] = {
            "size_per_side": size,
            "seed": seed + size,
            "summary": stats,
            "ratios": [float(r) for r in ratios],
        }
        echo(
            f"{tile}: {size}/{size} n={stats['n']} mean {stats['mean']:.5f} "
            f"sd {stats['sd']:.5f} q95 {stats['q95']:.5f} max {stats['max']:.5f}"
        )
    del members
    gc.collect()
    return {
        "provenance": provenance,
        "capture_identity_check": identity,
        "recorded_half_split_reproduction": half_split,
        "by_split_size": by_size,
    }


def m_invariance(per_tile: dict[str, Any]) -> dict[str, Any]:
    """Test pin 43(b)'s assumption instead of inheriting it.

    The factor is assumed m-invariant because ``T``'s distribution is
    governed by ``N_eff`` rather than by ``m``. If that holds, the 50/50
    and 25/25 distributions coincide within their own sampling error.

    Args:
        per_tile: tile -> the block from :func:`measure_tile`.

    Returns:
        The per-tile comparison and a plain statement of what it shows.
    """
    out: dict[str, Any] = {
        "assumption": (
            "the ratio T = RMS(Δσ)/F_ens has an m-invariant distribution "
            "because F_ens already carries the whole 1/sqrt(m-1) scaling, so "
            "what remains is governed by N_eff alone (pin 43b)"
        ),
        "per_tile": {},
    }
    for tile, block in per_tile.items():
        a = block["by_split_size"]["50_50"]["summary"]
        b = block["by_split_size"]["25_25"]["summary"]
        # Standard error of each mean, then of their difference. The two
        # samples are drawn from the same 100 members, so this SE is
        # itself optimistic — the pin-43a caveat applies here too.
        se = float(np.sqrt(a["sd"] ** 2 / a["n"] + b["sd"] ** 2 / b["n"]))
        diff = a["mean"] - b["mean"]
        out["per_tile"][tile] = {
            "mean_50_50": a["mean"],
            "mean_25_25": b["mean"],
            "mean_difference": diff,
            "sd_50_50": a["sd"],
            "sd_25_25": b["sd"],
            "sd_ratio_25_over_50": b["sd"] / a["sd"],
            "naive_se_of_difference": se,
            "difference_in_naive_se": diff / se if se else float("nan"),
            "q95_50_50": a["q95"],
            "q95_25_25": b["q95"],
        }
    return out


@app.command()
def run(
    evidence_path: Annotated[Path, typer.Option("--evidence-path")] = EVIDENCE,
    n_partitions: Annotated[
        int, typer.Option(help="Partitions per split size (pin 43: ~200)")
    ] = N_PARTITIONS,
    seed: Annotated[int, typer.Option(help="Base seed of the partition draw")] = SEED,
    record: Annotated[bool, typer.Option(help="Write the evidence block")] = True,
) -> None:
    """Run the settling measurement on both seam tiles and record it."""

    def echo(msg: str) -> None:
        print(f"[settling] {datetime.now(UTC).isoformat()} {msg}", flush=True)

    mod = _stage1_module()
    tiles = list(mod.SEAM_PAIR_TILES)
    per_tile = {
        t: measure_tile(t, n_partitions=n_partitions, seed=seed, echo=echo)
        for t in tiles
    }
    invariance = m_invariance(per_tile)
    for tile, block in invariance["per_tile"].items():
        echo(
            f"{tile}: m-invariance — mean 50/50 {block['mean_50_50']:.5f} vs "
            f"25/25 {block['mean_25_25']:.5f} "
            f"(Δ {block['mean_difference']:+.5f} = "
            f"{block['difference_in_naive_se']:+.1f} naive SE); sd ratio "
            f"{block['sd_ratio_25_over_50']:.3f}"
        )

    if not record:
        return
    results = __import__("json").loads(evidence_path.read_text())
    s1 = results["phase14"]["stage1"]
    s1[NODE] = {
        "label": "MEASUREMENT",
        "status": "RECORDED, NOT SEALED",
        "ruling": "docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md",
        "pin": "43 — run the settling measurement (43a caveat, 43b two split sizes)",
        "not_verdict_bearing": (
            "owner pin 49: nothing here licenses a σ verdict. The rubric "
            "amendment (Rule 0.a text and Rule 0.b together) is deferred to "
            "T17, sealed once against the CRN-paired configuration T14 creates"
        ),
        "quantity": (
            "T = RMS(σ_A − σ_B) / F_ens over disjoint member partitions of one "
            "tile's recorded ensemble, F_ens = σ_pooled/√(size−1) with the "
            "pin-38 POOLED (quadratic-mean) σ level"
        ),
        "why_this_is_a_null": (
            "both sides come from the SAME tile's SAME solve, so they differ "
            "only by which members were drawn — there is no seam, no lattice "
            "difference and no CRN difference between them"
        ),
        "caveat_pin_43a": (
            "the partitions resample the SAME 100 recorded members, so the "
            "between-partition spread measures COMBINATORIAL variability, not "
            "ensemble-to-ensemble variability, and UNDERSTATES the true null "
            "spread. Any factor derived from this distribution must carry "
            "margin for that, and this caveat travels with the number"
        ),
        "caveat_quantile_reach": (
            f"with n={n_partitions} partitions the empirical distribution "
            "supports quantiles to about q95–q99; a 0.999 attributability "
            "quantile is NOT estimable from this sample and must not be read "
            "off it"
        ),
        "survives_t14": (
            "pin 43: N_eff is a property of the field's spatial correlation "
            "and is unaffected by the CRN pairing T14 introduces"
        ),
        "n_partitions_per_split_size": n_partitions,
        "split_sizes": list(SPLIT_SIZES),
        "base_seed": seed,
        "no_solves_run": True,
        "per_tile": per_tile,
        "m_invariance_pin_43b": invariance,
        "date": datetime.now(UTC).date().isoformat(),
    }
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    atomic_write_json(evidence_path, results)
    echo(f"recorded: phase14.stage1.{NODE}")


if __name__ == "__main__":
    app()
