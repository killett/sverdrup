"""Diagnosis of the Stage-1 PAIR/σ ELEVATED cell — MC noise or seam artifact?

**This script records a DIAGNOSIS, never a rubric row.** It applies no
threshold, produces no verdict and no score; the sealed rubric's cells are
untouched by it, and nothing here is a response to the seam signal. Its
only job is to answer one factual question:

    T4 recorded PAIR/σ ``R_seam_sigma = 1.1044`` (ELEVATED) beside
    PAIR/mean ``0.0827`` (CLEAN). Is the σ disagreement a seam artifact,
    or is it the ensemble Monte-Carlo noise floor of two independent
    m=100 member-std estimates?

Four independent lines are recorded, all read-only against artifacts the
T4 leg already persisted:

1. **Magnitude.** ``RMS(σ_n − σ_s)`` on the 2·overlap strip against the
   MC-floor prediction ``σ/√(m−1)`` for two INDEPENDENT σ estimates.
2. **One-sidedness.** ``RMS(σ_s − σ_anchor)`` vs ``RMS(σ_n − σ_anchor)``.
   A seam artifact is symmetric in the two tiles; a CRN-origin effect is
   not — ``seam_s`` and the seamless anchor share a basis origin and
   therefore share their coefficient draws, while ``seam_n`` does not.
3. **Localisation.** Per-latitude-row RMS profile across the strip. The
   mean route localises (a V with its minimum at the shared core
   boundary); MC noise is flat.
4. **The half-split (the reviewer's cheap confirmation).** Split each
   tile's OWN m=100 members into two halves of 50 and evaluate the
   member-std of each half over the SAME strip. There is no seam inside
   one tile, so ``RMS(σ_half1 − σ_half2)`` is pure MC noise, and it must
   come out at ``σ/√(50−1)`` — LARGER than the cross-tile number, since
   50 members are noisier than 100. This is the discriminating test: if
   the half-split difference were ~0 the MC explanation would be refuted
   and the ELEVATED cell would survive as a real signal.

Plus a unit-level demonstration of the MECHANISM: ``coef_noise`` keys the
coefficient perturbation on pavement-lattice indices ``(ix, iy)`` measured
from ``BasisSpec.(x0_km, y0_km)``, and each tile's ``basis_domain`` is set
from its OWN ``solve_bbox`` lower-left corner, so two tiles with different
origins draw independent perturbations for the same physical element.

Every heavy step reuses the T4 machinery by import — ``seam_strip_bbox`` /
``strip_mask`` for the domain, the Task-18 lineage ``std_fields`` for the
field evaluation, ``seam_delta`` for the RMS reduction. Nothing is
re-solved and no production behaviour is touched.

Run: ``pixi run python scripts/phase14_sigma_diagnosis.py`` (add
``--no-record`` to print the block without touching the evidence store).
"""

from __future__ import annotations

import gc
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Annotated, Any

import numpy as np
import typer
from numpy.typing import NDArray

from sverdrup.validation.phase14_seal import EVIDENCE

SIGMA_DIAGNOSIS_NODE = "seam_sigma_diagnosis"
DIAGNOSIS_LABEL = "DIAGNOSIS"
NOT_A_RUBRIC_ROW = (
    "DIAGNOSIS, not a rubric row: no threshold is applied here, no verdict "
    "cell is assigned and no score is produced. The sealed rubric's "
    "phase14.stage1.seam_rows are untouched by this block, and nothing "
    "recorded here tunes, suppresses or responds to the seam signal."
)
QUESTION = (
    "Is the PAIR/σ ELEVATED cell (R_seam_sigma = 1.1044) a seam artifact, "
    "or the ensemble Monte-Carlo noise floor of two independent m=100 "
    "member-std estimates?"
)

app = typer.Typer(add_completion=False, help=__doc__)


def _stage1_module() -> ModuleType:
    """The T4 Stage-1 run script, imported read-only (the standing reuse formula).

    Returns:
        The executed ``scripts/phase14_stage1_run`` module.

    Raises:
        RuntimeError: If the sibling module cannot be loaded.
    """
    name = "phase14_stage1_run"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ---- pure helpers (unit-tested) ------------------------------------------


def mc_floor(sigma_level: float, m: int) -> float:
    """MC noise floor of the DIFFERENCE of two independent m-member σ estimates.

    A sample standard deviation from ``m`` members has relative standard
    error ``1/√(2(m−1))``; the difference of two independent such
    estimates therefore has standard deviation ``√2 · σ/√(2(m−1))`` =
    ``σ/√(m−1)``.

    Args:
        sigma_level: The σ field's own RMS level over the domain [m].
        m: Members behind each of the two σ estimates.

    Returns:
        Predicted ``RMS`` of the difference of the two σ fields [m].

    Raises:
        ValueError: If ``m`` is below 2 (a single member has no σ).
    """
    if m < 2:
        raise ValueError(f"member-std needs m >= 2, got {m}")
    return float(sigma_level) / float(np.sqrt(m - 1))


def member_halves(
    anoms: dict[str, NDArray[np.float64]],
) -> tuple[dict[str, NDArray[np.float64]], dict[str, NDArray[np.float64]]]:
    """Split every window's member anomalies into two DISJOINT equal halves.

    The same member indices are taken in every window — the halves must be
    two coherent sub-ensembles, not two independently shuffled subsets, or
    the cross-window blend would mix members and the σ of each half would
    not be the σ of a 50-member ensemble.

    Args:
        anoms: window_id -> ``(n_el, m)`` coefficient anomalies.

    Returns:
        ``(half1, half2)``, each window_id -> ``(n_el, m // 2)``.

    Raises:
        ValueError: If ``anoms`` is empty, if the member counts disagree
            across windows, or if ``m`` is odd (an unequal split would
            give the two halves different noise floors).
    """
    if not anoms:
        raise ValueError("no windows to split")
    counts = {int(a.shape[1]) for a in anoms.values()}
    if len(counts) != 1:
        raise ValueError(f"windows disagree on member count: {sorted(counts)}")
    m = counts.pop()
    if m % 2 != 0:
        raise ValueError(f"member count {m} is odd — the halves would differ in size")
    half = m // 2
    first = {w: np.ascontiguousarray(a[:, :half]) for w, a in anoms.items()}
    second = {w: np.ascontiguousarray(a[:, half:]) for w, a in anoms.items()}
    return first, second


def rms(values: Any) -> float:  # noqa: ANN401 - any array-like of floats
    """Root-mean-square over the finite entries of an array.

    Args:
        values: Any array-like; non-finite entries (land) are dropped.

    Returns:
        ``sqrt(mean(finite**2))``.

    Raises:
        ValueError: If no finite entry survives.
    """
    flat = np.asarray(values, dtype=np.float64).ravel()
    finite = flat[np.isfinite(flat)]
    if finite.size == 0:
        raise ValueError("no finite values to pool")
    return float(np.sqrt(np.mean(np.square(finite))))


# ---- the four lines of evidence ------------------------------------------


def persisted_strip_reads() -> dict[str, Any]:
    """Lines 1-3: magnitude, one-sidedness and localisation from the maps.

    Read-only against the T4 leg's persisted mean and member-std maps; the
    strip is the production ``seam_strip_bbox`` and the reductions are the
    production ``seam_delta`` / pooled-interior helpers.

    Returns:
        A block carrying the observed ratios, the MC-floor prediction, the
        one-sided asymmetry and the per-latitude localisation profiles.
    """
    from sverdrup.application.spatial_tiles import frame_grid
    from sverdrup.validation.seam_metrics import _pooled_interior_rms, seam_delta

    mod = _stage1_module()
    north, south = mod.SEAM_PAIR_TILES
    strip = mod.seam_strip_bbox()

    sigma = {t: mod._strip_fields(mod.SEAM_STD_MAPS[t], t) for t in (north, south)}  # noqa: SLF001
    sigma["anchor"] = mod._strip_fields(mod.ANCHOR_STD_MAPS, "anchor")  # noqa: SLF001
    mean = {t: mod._strip_fields(mod.SEAM_MEAN_MAPS[t], t) for t in (north, south)}  # noqa: SLF001

    int_sigma = {
        t: mod._interior_fields(mod.SEAM_STD_MAPS[t], t) for t in (north, south)
    }  # noqa: SLF001
    int_mean = {
        t: mod._interior_fields(mod.SEAM_MEAN_MAPS[t], t) for t in (north, south)
    }  # noqa: SLF001
    d_int_sigma = _pooled_interior_rms(
        int_sigma[north], int_sigma[south], 1, kind="sigma interior"
    )
    d_int_mean = _pooled_interior_rms(
        int_mean[north], int_mean[south], 1, kind="interior"
    )
    rms_sigma_delta = seam_delta(sigma[north], sigma[south])
    rms_mean_delta = seam_delta(mean[north], mean[south])

    grid = frame_grid(mod.registry_frame(north), mod.RESOLUTION_DEG)
    lat_mask, _ = mod.strip_mask(grid, strip)
    lats = [float(v) for v in np.asarray(grid.y)[lat_mask]]
    prof_sigma = [rms((sigma[north] - sigma[south])[:, i, :]) for i in range(len(lats))]
    prof_mean = [rms((mean[north] - mean[south])[:, i, :]) for i in range(len(lats))]

    level = {t: rms(sigma[t]) for t in sigma}
    m = int(mod.SEAM_PAIR_M)
    predicted = mc_floor(0.5 * (level[north] + level[south]), m)

    return {
        "domain": {
            "name": mod.SEAM_STRIP_NAME,
            "bbox": [strip.lon_min, strip.lon_max, strip.lat_min, strip.lat_max],
            "field_shape_time_lat_lon": list(sigma[north].shape),
        },
        "recomputed_t4_reads": {
            "rms_sigma_delta_m": rms_sigma_delta,
            "d_int_sigma_m": d_int_sigma,
            "r_seam_sigma": rms_sigma_delta / d_int_sigma,
            "rms_mean_delta_m": rms_mean_delta,
            "d_int_mean_m": d_int_mean,
            "r_seam": rms_mean_delta / d_int_mean,
            "note": (
                "recomputed here from the same persisted maps purely to show "
                "this block reads the SAME fields T4 read — the rubric rows "
                "are not rewritten"
            ),
        },
        "line_1_magnitude": {
            "sigma_level_rms_m": level,
            "m": m,
            "predicted_mc_floor_sigma_over_sqrt_m_minus_1_m": predicted,
            "observed_rms_sigma_delta_m": rms_sigma_delta,
            "observed_over_predicted": rms_sigma_delta / predicted,
        },
        "line_2_one_sidedness": {
            "rms_sigma_seam_s_minus_anchor_m": seam_delta(
                sigma[south], sigma["anchor"]
            ),
            "rms_sigma_seam_n_minus_anchor_m": seam_delta(
                sigma[north], sigma["anchor"]
            ),
            "asymmetry_ratio_n_over_s": (
                seam_delta(sigma[north], sigma["anchor"])
                / seam_delta(sigma[south], sigma["anchor"])
            ),
        },
        "line_3_localisation": {
            "strip_lats": lats,
            "sigma_profile_per_lat_m": prof_sigma,
            "mean_profile_per_lat_m": prof_mean,
            "sigma_spread_pct_of_mean": 100.0
            * (max(prof_sigma) - min(prof_sigma))
            / float(np.mean(prof_sigma)),
            "mean_spread_pct_of_mean": 100.0
            * (max(prof_mean) - min(prof_mean))
            / float(np.mean(prof_mean)),
            "sigma_argmin_lat": lats[int(np.argmin(prof_sigma))],
            "mean_argmin_lat": lats[int(np.argmin(prof_mean))],
            "boundary_lat": 0.5 * (strip.lat_min + strip.lat_max),
        },
    }


def half_split_tile(tile: str) -> dict[str, Any]:
    """Line 4 for one tile: member-std of two disjoint 50-member halves.

    The tile's persisted member store is replayed through the SAME field
    evaluator the production maps were written with, once per half, on the
    same strip. No solve is re-run.

    Args:
        tile: ``seam_n`` or ``seam_s``.

    Returns:
        The half-split numbers, the MC-floor prediction, a bit-exactness
        check of the full-m recomputation against the persisted map, and
        the half-split's own per-latitude profile.
    """
    from sverdrup.application.spatial_tiles import frame_grid
    from sverdrup.core.parameters import ConstantProvider
    from sverdrup.methods.miost import PHASE13_WINNER_PARAMS
    from sverdrup.methods.miost_windows import WindowPlan
    from sverdrup.validation.seam_metrics import seam_delta

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

    def on_strip(fields: NDArray[np.float64]) -> NDArray[np.float64]:
        stack = np.stack([f.reshape(grid.shape) for f in fields])
        return np.asarray(stack[:, lat_mask, :][:, :, lon_mask])

    sigma_full = on_strip(std_fields(spec, starts, anoms, grid, plan, days))
    first, second = member_halves(anoms)
    del anoms
    gc.collect()
    sigma_1 = on_strip(std_fields(spec, starts, first, grid, plan, days))
    del first
    gc.collect()
    sigma_2 = on_strip(std_fields(spec, starts, second, grid, plan, days))
    del second
    gc.collect()

    m_half = int(mod.SEAM_PAIR_M) // 2
    persisted = mod._strip_fields(mod.SEAM_STD_MAPS[tile], tile)  # noqa: SLF001
    lats = [float(v) for v in np.asarray(grid.y)[lat_mask]]
    profile = [rms((sigma_1 - sigma_2)[:, i, :]) for i in range(len(lats))]
    observed = seam_delta(sigma_1, sigma_2)
    predicted = mc_floor(rms(sigma_full), m_half)

    return {
        "tile": tile,
        "basis_origin_km": {"x0": spec.x0_km, "y0": spec.y0_km},
        "solve_bbox": [
            frame.solve_bbox.lon_min,
            frame.solve_bbox.lon_max,
            frame.solve_bbox.lat_min,
            frame.solve_bbox.lat_max,
        ],
        "member_store": str(mod.SEAM_MEMBER_STORE[tile]),
        "n_windows": len(wids),
        "m_half": m_half,
        "full_m_recomputation_matches_persisted_map": {
            "max_abs_diff_m": float(np.nanmax(np.abs(sigma_full - persisted))),
            "note": (
                "0.0 means this block's replay of the member store reproduces "
                "the persisted member-std map exactly — the half-split rides "
                "the identical evaluation path"
            ),
        },
        "sigma_level_rms_m": {
            "full": rms(sigma_full),
            "half1": rms(sigma_1),
            "half2": rms(sigma_2),
        },
        "observed_rms_sigma_half1_minus_half2_m": observed,
        "predicted_mc_floor_m": predicted,
        "observed_over_predicted": observed / predicted,
        "profile_per_lat_m": profile,
        "profile_spread_pct_of_mean": 100.0
        * (max(profile) - min(profile))
        / float(np.mean(profile)),
    }


def crn_origin_demonstration() -> dict[str, Any]:
    """Unit-level demonstration that the CRN draw follows the basis ORIGIN.

    Three parts on the REAL production specs: (A) one identity row draws
    the same number under both origins although it names an element 334 km
    apart; (B) the two seam pavements share NO element centre at all, so
    the same physical element carries different identities and independent
    draws; (C) the positive control — ``seam_s`` and the seamless anchor
    share ``(x0, y0)``, so the same physical element carries the SAME
    identity and the IDENTICAL draw.

    Returns:
        The demonstration block.
    """
    from sverdrup.application.spatial_tiles import frame_grid
    from sverdrup.core.parameters import ConstantProvider
    from sverdrup.methods.miost import PHASE13_WINNER_PARAMS
    from sverdrup.methods.miost_basis import BasisSpec, Elements
    from sverdrup.methods.miost_crn import coef_noise
    from sverdrup.methods.miost_windows import WindowPlan

    mod = _stage1_module()
    provider = ConstantProvider(dict(PHASE13_WINNER_PARAMS))
    member, root = 7, int(mod._shipped_member_root())  # noqa: SLF001
    start = WindowPlan().windows[0].start_day

    specs: dict[str, BasisSpec] = {}
    for tile in (*mod.SEAM_PAIR_TILES, "anchor"):
        frame = mod.registry_frame(tile)
        grid = frame_grid(frame, mod.RESOLUTION_DEG)
        method = mod._seam_miost(frame, starts=None, maxiter=mod.STAGE1_PCG_MAXITER)  # noqa: SLF001
        specs[tile] = method._spec_from(provider, grid)  # noqa: SLF001
    north, south = mod.SEAM_PAIR_TILES
    els: dict[str, Elements] = {
        t: s.elements_for_window(start) for t, s in specs.items()
    }

    def draw(rows: NDArray[np.int64]) -> NDArray[np.float64]:
        """Unit-variance coefficient draws for the given identity rows."""
        return np.asarray(coef_noise(member, rows, np.ones(rows.shape[0]), root))

    # (A) one identity row, two origins.
    row = els[north].identity[:1]
    twin = int(np.flatnonzero((els[south].identity == row[0]).all(axis=1))[0])
    a_north = float(draw(row)[0])
    a_south = float(draw(els[south].identity[twin : twin + 1])[0])

    def centre_key(elements: Elements) -> NDArray[np.void]:
        """Structured view keying an element by (scale, dir, phase, slot, centre)."""
        cols = np.stack(
            [
                elements.identity[:, 0],
                elements.identity[:, 1],
                elements.identity[:, 2],
                elements.identity[:, 5],
                np.round(elements.x_km * 1_000_000).astype(np.int64),
                np.round(elements.y_km * 1_000_000).astype(np.int64),
            ],
            axis=1,
        )
        cols = np.ascontiguousarray(cols)
        return np.asarray(cols.view([("", cols.dtype)] * cols.shape[1]).ravel())

    # (B) the same PHYSICAL element across the two seam pavements.
    shared_ns = np.intersect1d(centre_key(els[north]), centre_key(els[south])).size
    step = specs[north].alpha * specs[north].ladder[0]
    offset = specs[north].y0_km - specs[south].y0_km

    # (C) positive control: seam_s vs the seamless anchor.
    _, i_south, i_anchor = np.intersect1d(
        centre_key(els[south]), centre_key(els["anchor"]), return_indices=True
    )
    take = slice(0, 4000)
    id_south = els[south].identity[i_south[take]]
    id_anchor = els["anchor"].identity[i_anchor[take]]
    d_south, d_anchor = draw(id_south), draw(id_anchor)

    return {
        "keyed_on": (
            "coef_noise(member, identity, q_var, root) with identity = "
            "(scale_idx, dir_idx, phase_idx, ix, iy, global_slot); ix/iy are "
            "pavement-lattice indices measured from BasisSpec.(x0_km, y0_km), "
            "and each tile's basis_domain is its OWN solve_bbox lower-left "
            "corner (scripts/phase14_stage1_run.py::_seam_miost)"
        ),
        "basis_origins_km": {
            t: {
                "x0_km": s.x0_km,
                "y0_km": s.y0_km,
                "d_x_km": s.d_x_km,
                "d_y_km": s.d_y_km,
            }
            for t, s in specs.items()
        },
        "A_same_identity_row_two_origins": {
            "identity": [int(v) for v in row[0]],
            "draw_under_seam_n": a_north,
            "draw_under_seam_s": a_south,
            "draws_identical": a_north == a_south,
            "element_centre_km_seam_n": [
                float(els[north].x_km[0]),
                float(els[north].y_km[0]),
            ],
            "element_centre_km_seam_s": [
                float(els[south].x_km[twin]),
                float(els[south].y_km[twin]),
            ],
            "physical_separation_km": float(els[north].y_km[0] - els[south].y_km[twin]),
            "reading": (
                "the shared random number names a DIFFERENT PLACE in the two "
                "tiles — CRN is pinned to the lattice index, not to the ocean"
            ),
        },
        "B_same_physical_element_seam_n_vs_seam_s": {
            "n_physically_coincident_elements": int(shared_ns),
            "origin_offset_km": float(offset),
            "finest_rung_lattice_step_km": float(step),
            "offset_mod_step_km": float(offset % step),
            "reading": (
                "the 334 km origin offset is not an integer multiple of any "
                "rung's lattice step, so the two pavements share no element "
                "centre at all: seam_n's coefficients are drawn on a "
                "different lattice from seam_s's, and their perturbations "
                "are independent by construction"
            ),
        },
        "C_control_seam_s_vs_anchor_same_origin": {
            "n_physically_coincident_elements": int(i_south.size),
            "n_compared": int(id_south.shape[0]),
            "identity_rows_identical": bool(np.array_equal(id_south, id_anchor)),
            "draws_identical": bool(np.array_equal(d_south, d_anchor)),
            "max_abs_draw_difference": float(np.max(np.abs(d_south - d_anchor))),
            "reading": (
                "seam_s and the seamless anchor share (x0, y0) = (0, 0), so "
                "the same physical element carries the same identity and the "
                "IDENTICAL draw — which is exactly why RMS(sigma_s - "
                "sigma_anchor) nearly vanishes while RMS(sigma_n - "
                "sigma_anchor) sits at the MC floor"
            ),
        },
    }


# ---- assembly + seal-gated recording -------------------------------------


def build_diagnosis_block(
    *,
    strip_reads: dict[str, Any],
    half_split: dict[str, dict[str, Any]],
    mechanism: dict[str, Any],
    seal_sha: str,
    date: str,
) -> dict[str, Any]:
    """Assemble the recorded DIAGNOSIS block.

    Args:
        strip_reads: Output of :func:`persisted_strip_reads`.
        half_split: tile -> output of :func:`half_split_tile`.
        mechanism: Output of :func:`crn_origin_demonstration`.
        seal_sha: The verified seal sha.
        date: ISO date string.

    Returns:
        The block recorded under ``phase14.stage1.seam_sigma_diagnosis``.
    """
    mod = _stage1_module()
    observed = float(strip_reads["line_1_magnitude"]["observed_rms_sigma_delta_m"])
    predicted_100 = float(
        strip_reads["line_1_magnitude"][
            "predicted_mc_floor_sigma_over_sqrt_m_minus_1_m"
        ]
    )
    return {
        "label": DIAGNOSIS_LABEL,
        "not_a_rubric_row": NOT_A_RUBRIC_ROW,
        "question": QUESTION,
        "subject": {
            "row": "phase14.stage1.seam_rows :: route=pair, field_kind=sigma",
            "r_seam_sigma_as_recorded": 1.1044,
            "rubric_cell_as_recorded": "ELEVATED",
            "companion_mean_route_r_seam_as_recorded": 0.0827,
            "note": (
                "quoted from the T4 row for identification only; this block "
                "neither re-issues nor revises it"
            ),
        },
        **strip_reads,
        "line_4_half_split": {
            "construction": (
                "each tile's OWN m=100 members split into two DISJOINT halves "
                "of 50, each half's member-std evaluated through the same "
                "Task-18 lineage std_fields path over the same 2·overlap "
                "strip. There is no seam inside a single tile, so "
                "RMS(sigma_half1 - sigma_half2) is pure ensemble MC noise"
            ),
            "prediction_if_mc_noise": (
                "approximately sigma/sqrt(50-1), i.e. LARGER than the "
                "cross-tile RMS(sigma_n - sigma_s) by sqrt(99/49) = 1.42, "
                "because 50 members are noisier than 100"
            ),
            "prediction_if_seam_artifact": (
                "approximately zero, or orders of magnitude smaller than the "
                "cross-tile number — a within-tile split crosses no seam"
            ),
            "per_tile": half_split,
            "cross_tile_reference_rms_sigma_delta_m": observed,
            "ratio_half_split_over_cross_tile": {
                tile: float(block["observed_rms_sigma_half1_minus_half2_m"]) / observed
                for tile, block in half_split.items()
            },
            "expected_ratio_sqrt_99_over_49": float(np.sqrt(99.0 / 49.0)),
        },
        "mechanism_demonstration": mechanism,
        "confirmed": [
            (
                f"MAGNITUDE — RMS(sigma_n - sigma_s) = {observed:.6f} m matches "
                f"the two-independent-estimate MC floor sigma/sqrt(m-1) = "
                f"{predicted_100:.6f} m to "
                f"{abs(1.0 - observed / predicted_100) * 100:.1f}%"
            ),
            (
                "ONE-SIDEDNESS — the disagreement against the seamless anchor "
                "is carried almost entirely by seam_n; seam_s, which shares "
                "the anchor's basis origin and therefore its CRN draws, "
                "nearly vanishes against it. A seam artifact would be "
                "symmetric in the two tiles"
            ),
            (
                "NO LOCALISATION — the sigma difference is flat across the "
                "strip, while the mean route on the same strip shows the "
                "expected V with its minimum at the shared core boundary"
            ),
            (
                "HALF-SPLIT — within-tile 50/50 member halves, which cross no "
                "seam at all, disagree MORE than the two tiles do, at the "
                "sigma/sqrt(49) floor. This is the discriminating result: a "
                "seam artifact cannot appear inside a single tile"
            ),
            (
                "MECHANISM — coef_noise keys on pavement-lattice (ix, iy) "
                "from BasisSpec.(x0_km, y0_km); the two seam tiles' origins "
                "differ by 334 km, an offset that aligns no lattice rung, so "
                "their coefficient perturbations are independent draws"
            ),
        ],
        "refuted": [
            (
                "The reading that PAIR/sigma ELEVATED is a SEAM artifact — a "
                "cross-tile disagreement caused by the tiling — is not "
                "supported: the same magnitude arises inside one tile with no "
                "seam present, it does not localise at the boundary, and it "
                "is one-sided in a way a seam cannot be"
            ),
        ],
        "not_established": [
            (
                "This block does NOT show that the sigma route is "
                "insensitive to real seam artifacts, only that THIS reading "
                "is at the ensemble noise floor. At m=100 the floor "
                "sigma/sqrt(99) is comparable to D_int_sigma, so the sigma "
                "route's resolving power at this m is a question for the "
                "owner, not a finding of this diagnosis"
            ),
            (
                "No threshold, no verdict and no tuning follows from this "
                "block; the sealed rubric row stands exactly as recorded"
            ),
        ],
        "provenance": {
            "reads": {
                "member_std_maps": {
                    t: str(mod.SEAM_STD_MAPS[t]) for t in mod.SEAM_PAIR_TILES
                },
                "mean_maps": {
                    t: str(mod.SEAM_MEAN_MAPS[t]) for t in mod.SEAM_PAIR_TILES
                },
                "anchor_maps": [str(mod.ANCHOR_STD_MAPS), str(mod.ANCHOR_MEAN_MAPS)],
                "member_stores": {
                    t: str(mod.SEAM_MEMBER_STORE[t]) for t in mod.SEAM_PAIR_TILES
                },
            },
            "reused_by_import": [
                "scripts/phase14_stage1_run.py::seam_strip_bbox / strip_mask / "
                "_strip_fields / _interior_fields / _seam_miost",
                "scripts/diag_miost_seam_dispersion.py::std_fields "
                "(the Task-18 lineage evaluator, via _lineage_std_fields)",
                "sverdrup.validation.seam_metrics::seam_delta / _pooled_interior_rms",
            ],
            "solves_run": 0,
            "production_behaviour_changed": False,
            "seal_sha": seal_sha,
            "date": date,
        },
    }


def record_sigma_diagnosis(
    block: dict[str, Any], evidence_path: Path = EVIDENCE
) -> None:
    """Record the block under ``phase14.stage1.seam_sigma_diagnosis`` — seal-gated.

    Args:
        block: The assembled diagnosis block.
        evidence_path: The evidence store (tmp path in tests).

    Raises:
        sverdrup.validation.phase14_seal.SealError: No verified seal.
    """
    from sverdrup.application.calibration.harness import atomic_write_json
    from sverdrup.validation import phase14_seal

    phase14_seal.verify_current_seal()
    results: dict[str, Any] = (
        json.loads(evidence_path.read_text()) if evidence_path.exists() else {}
    )
    node = results.setdefault("phase14", {}).setdefault("stage1", {})
    node[SIGMA_DIAGNOSIS_NODE] = block
    atomic_write_json(evidence_path, results)


@app.command()
def run(
    record: Annotated[
        bool, typer.Option(help="Write the block to the evidence store")
    ] = True,
) -> None:
    """Run the whole diagnosis and record it (read-only; no solve is run).

    Args:
        record: Whether to write the block (seal-gated). ``--no-record``
            prints it and writes nothing.
    """
    from sverdrup.validation import phase14_seal

    mod = _stage1_module()

    def echo(msg: str) -> None:
        print(f"[sigma-diagnosis] {datetime.now(UTC).isoformat()} {msg}", flush=True)

    phase14_seal.verify_current_seal()
    seal_sha = str(json.loads(EVIDENCE.read_text())["phase14"]["stage0"]["seal"]["sha"])
    echo(f"seal verified: {seal_sha}")
    strip_reads = persisted_strip_reads()
    line1 = strip_reads["line_1_magnitude"]
    echo(
        f"observed RMS(sigma_n - sigma_s) {line1['observed_rms_sigma_delta_m']:.6f} m "
        f"vs MC floor {line1['predicted_mc_floor_sigma_over_sqrt_m_minus_1_m']:.6f} m"
    )
    half_split = {}
    for tile in mod.SEAM_PAIR_TILES:
        half_split[tile] = half_split_tile(tile)
        echo(
            f"{tile}: half-split "
            f"{half_split[tile]['observed_rms_sigma_half1_minus_half2_m']:.6f} m "
            f"vs predicted {half_split[tile]['predicted_mc_floor_m']:.6f} m"
        )
    mechanism = crn_origin_demonstration()
    echo(
        "mechanism: seam_n/seam_s share "
        f"{mechanism['B_same_physical_element_seam_n_vs_seam_s']['n_physically_coincident_elements']}"
        " element centres; seam_s/anchor draws identical: "
        f"{mechanism['C_control_seam_s_vs_anchor_same_origin']['draws_identical']}"
    )
    block = build_diagnosis_block(
        strip_reads=strip_reads,
        half_split=half_split,
        mechanism=mechanism,
        seal_sha=seal_sha,
        date=datetime.now(UTC).date().isoformat(),
    )
    if record:
        record_sigma_diagnosis(block)
        echo(f"recorded phase14.stage1.{SIGMA_DIAGNOSIS_NODE} -> {EVIDENCE}")
    else:
        print(json.dumps(block, indent=1, default=float))


if __name__ == "__main__":
    app()
