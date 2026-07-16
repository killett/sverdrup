"""Phase-8 fold machinery + pool-then-max lexicographic lane selection.

Implements the pre-registered T+S fold protocol used to choose among the
calibration-field fit lanes (spec plan-obligations 1-2 + promotion):

  - ``t_folds``: 6 pinned temporal rotations over the j3 validation year;
    each holds out one ``T_FOLDS`` month pair.
  - ``s_fold_layout`` / ``s_folds``: seeded spatial partition of the 25
    2°-cell blocks into 4 folds (sizes 7,6,6,6) with a ``GUARD_RING_DEG``
    guard ring excluded from both fit and score masks.
  - ``layout_respects_partition``: the >=50%-per-fit-region constraint check
    that drives salt re-draws (salt bookkeeping is the caller's job).
  - ``rho_hat`` / ``n_eff``: lag-truncated autocorrelation and the effective
    sample size correction.
  - ``merge_small_blocks``: fold-preserving merge of under-powered blocks into
    their nearest-centroid neighbour (deterministic lowest-index tie-break).
  - ``pooled_worst_region``: per-region pooled coverage -> worst |dev| over
    regions.
  - ``select``: lane-0 eligibility gate + lexicographic winner (S-fold ->
    T-fold -> smooth-lane preference), returning ``None`` for a negative
    result.

Block ids are ``row * 5 + col`` over the 5x5 grid, matching
``regions.cell_index``. Block centroids are the geometric centres of the 2°
cells: ``lon = 296 + 2*col``, ``lat = 34 + 2*row`` (cell col 0 spans
[295, 297) so its centre is 296; row 0 spans [33, 35) so its centre is 34).
"""

from __future__ import annotations

import math
from collections.abc import Iterator

import numpy as np

from sverdrup.application.calibration.constants import (
    COVERAGE_TARGET,
    GUARD_RING_DEG,
    MIN_N_EFF,
    RHO_CUTOFF,
    RHO_MAX_LAG,
    S_FOLD_COUNT,
    S_FOLD_SEED_ARGS,
    T_FOLDS,
    TIE_BAND,
)
from sverdrup.application.calibration.regions import LAT_MIN, LON_MIN, cell_index
from sverdrup.application.policy import Criterion, LexicographicPolicy, Verdict
from sverdrup.core.seeding import derive_seed

# Smooth-lane preference order used to break exact selection ties.
# Lower index == more preferred.
_SMOOTH_PREFERENCE: tuple[str, ...] = ("poly", "covariate", "piecewise")

_N_BLOCKS = 25
_S_FOLD_SIZES: tuple[int, ...] = (7, 6, 6, 6)


# ---------------------------------------------------------------------------
# Block geometry helpers
# ---------------------------------------------------------------------------


def _block_row_col(block: int) -> tuple[int, int]:
    """Return (row, col) for a block id in ``0..24``."""
    return block // 5, block % 5


def _block_centroid(block: int) -> tuple[float, float]:
    """Return the (lon, lat) geometric centre of a 2°-cell block.

    Args:
        block: Block id in ``0..24`` (``row * 5 + col``).

    Returns:
        Tuple ``(lon_centre, lat_centre)`` in degrees.
    """
    row, col = _block_row_col(block)
    # Cell spans [LON_MIN + 2*col, LON_MIN + 2*(col+1)); centre is + 1 deg.
    lon = LON_MIN + 2.0 * col + 1.0
    lat = LAT_MIN + 2.0 * row + 1.0
    return lon, lat


def _block_bounds(block: int) -> tuple[float, float, float, float]:
    """Return (lon_lo, lon_hi, lat_lo, lat_hi) edges of a block."""
    row, col = _block_row_col(block)
    lon_lo = LON_MIN + 2.0 * col
    lon_hi = lon_lo + 2.0
    lat_lo = LAT_MIN + 2.0 * row
    lat_hi = lat_lo + 2.0
    return lon_lo, lon_hi, lat_lo, lat_hi


def _block_of_points(lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
    """Return the block id (0..24) each point falls in via ``cell_index``."""
    row, col = cell_index(lon, lat)
    block: np.ndarray = np.asarray(row * 5 + col, dtype=int)
    return block


# ---------------------------------------------------------------------------
# T-folds
# ---------------------------------------------------------------------------


def t_folds(months: np.ndarray) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Yield the 6 pinned temporal rotations as (fit_mask, verify_mask).

    Each of the ``T_FOLDS`` month pairs is held out in turn: the verify mask
    selects the points whose month label is one of the pair; the fit mask is
    the complement. Rotations are yielded in ``T_FOLDS`` order.

    Args:
        months: Per-point month labels as two-character strings ("01".."12"),
            shape ``(N,)``.

    Yields:
        ``(fit_mask, verify_mask)`` boolean arrays of shape ``(N,)`` for each
        of the 6 rotations.
    """
    months = np.asarray(months)
    for pair in T_FOLDS:
        verify_mask = np.isin(months, np.asarray(pair))
        fit_mask = ~verify_mask
        yield fit_mask, verify_mask


# ---------------------------------------------------------------------------
# S-fold layout
# ---------------------------------------------------------------------------


def s_fold_layout(salt: int = 0) -> tuple[frozenset[int], ...]:
    """Return the seeded spatial fold layout of the 25 blocks.

    The 25 block ids are permuted by ``default_rng`` seeded from
    ``derive_seed(*S_FOLD_SEED_ARGS, salt)``, then sliced into contiguous
    groups of sizes ``(7, 6, 6, 6)`` in permutation order.

    Args:
        salt: Re-draw counter; incremented by the caller when
            ``layout_respects_partition`` is False. Threaded into the seed as
            ``derive_seed``'s ``member_index``.

    Returns:
        Tuple of ``S_FOLD_COUNT`` frozensets of block ids; the sets are
        disjoint and their union is ``{0, ..., 24}``.
    """
    seed = derive_seed(*S_FOLD_SEED_ARGS, salt)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(_N_BLOCKS)

    folds_out: list[frozenset[int]] = []
    start = 0
    for size in _S_FOLD_SIZES:
        folds_out.append(frozenset(int(b) for b in perm[start : start + size]))
        start += size
    if len(folds_out) != S_FOLD_COUNT:  # pragma: no cover - invariant guard
        raise RuntimeError(f"s_fold_layout produced {len(folds_out)} folds")
    return tuple(folds_out)


def s_folds(
    lon: np.ndarray,
    lat: np.ndarray,
    labels: np.ndarray,
    layout: tuple[frozenset[int], ...],
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Return per-fold (fit_mask, score_mask) with a guard ring.

    For each fold the held-out blocks are the fold's block ids. A point scores
    if it lies in a held-out block; it is used for fit if it lies in any other
    block. A **guard ring** removes edge leakage: any point within
    ``GUARD_RING_DEG`` degrees (measured independently in lon and lat) of a
    held-out block's boundary — on **either** side of that boundary — is
    excluded from **both** masks. Concretely a point is in the ring iff its lon
    lies in ``[lon_lo - g, lon_lo + g]`` or ``[lon_hi - g, lon_hi + g]`` while
    its lat is within ``[lat_lo - g, lat_hi + g]`` of the block (and the
    symmetric lat condition), for any held-out block, where ``g =
    GUARD_RING_DEG``. This means points just inside a held-out block near its
    edge are dropped from score, and points just outside in a neighbouring fit
    block are dropped from fit — the fit and score populations are separated by
    a ``2*g``-wide buffer along every held-out edge.

    Args:
        lon: Point longitudes [deg east], shape ``(N,)``.
        lat: Point latitudes [deg north], shape ``(N,)``.
        labels: Per-point fit-partition labels, shape ``(N,)`` (unused for mask
            construction; accepted so callers pass a uniform signature).
        layout: Fold layout from :func:`s_fold_layout`.

    Returns:
        List of ``(fit_mask, score_mask)`` boolean arrays of shape ``(N,)``,
        one per fold, in layout order. The two masks are always disjoint.
    """
    del labels  # not needed for mask geometry
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    block = _block_of_points(lon, lat)

    g = GUARD_RING_DEG
    out: list[tuple[np.ndarray, np.ndarray]] = []
    for held in layout:
        held_arr = np.array(sorted(held), dtype=int)
        in_held = np.isin(block, held_arr)

        # Guard ring: within g of any held-out block's edge (either side).
        ring = np.zeros(lon.shape, dtype=bool)
        for b in held_arr:
            lon_lo, lon_hi, lat_lo, lat_hi = _block_bounds(int(b))
            # A point is near this block's frame if it sits within the
            # g-expanded box AND within g of one of the four edges.
            in_expanded = (
                (lon >= lon_lo - g)
                & (lon <= lon_hi + g)
                & (lat >= lat_lo - g)
                & (lat <= lat_hi + g)
            )
            near_lon_edge = (np.abs(lon - lon_lo) <= g) | (np.abs(lon - lon_hi) <= g)
            near_lat_edge = (np.abs(lat - lat_lo) <= g) | (np.abs(lat - lat_hi) <= g)
            ring |= in_expanded & (near_lon_edge | near_lat_edge)

        score_mask = in_held & ~ring
        fit_mask = ~in_held & ~ring
        out.append((fit_mask, score_mask))
    return out


def layout_respects_partition(
    lon: np.ndarray,
    lat: np.ndarray,
    labels: np.ndarray,
    layout: tuple[frozenset[int], ...],
) -> bool:
    """Return whether every partition label keeps >=50% on the fit side.

    For each fold the fit side is the set of points **not** in the held-out
    blocks (the guard ring is not applied here — this is a raw partition-balance
    check, not a leakage check). Every distinct label in ``labels`` must retain
    at least half of its points on the fit side of **every** fold.

    Args:
        lon: Point longitudes [deg east], shape ``(N,)``.
        lat: Point latitudes [deg north], shape ``(N,)``.
        labels: Per-point fit-partition labels (the 5 ``regions.fit_partition``
            labels), shape ``(N,)``.
        layout: Fold layout from :func:`s_fold_layout`.

    Returns:
        True iff the >=50% constraint holds for every (label, fold) pair;
        False otherwise (caller re-draws at ``salt + 1``).
    """
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    labels = np.asarray(labels)
    block = _block_of_points(lon, lat)

    for held in layout:
        held_arr = np.array(sorted(held), dtype=int)
        in_held = np.isin(block, held_arr)
        for label in np.unique(labels):
            sel = labels == label
            total = int(np.count_nonzero(sel))
            if total == 0:
                continue
            fit_side = int(np.count_nonzero(sel & ~in_held))
            if fit_side < 0.5 * total:
                return False
    return True


# ---------------------------------------------------------------------------
# rho_hat / n_eff
# ---------------------------------------------------------------------------


def rho_hat(
    z: np.ndarray, day: np.ndarray, pass_id: np.ndarray
) -> tuple[np.ndarray, float]:
    """Return the retained lag autocorrelations and the n_eff inflation factor.

    Normalised residuals ``z`` are grouped by ``pass_id`` and ordered within
    each group by ``day`` (native along-track order). For each lag ``k`` in
    ``1..RHO_MAX_LAG`` the lag-``k`` autocorrelation is computed per pass and
    **averaged across passes weighted by the number of contributing lag pairs**
    (so long passes count more than short ones). The averaged sequence is
    truncated at the first ``k`` with ``rho_k < RHO_CUTOFF``; only the lags
    strictly before that cutoff are retained.

    Args:
        z: Normalised residuals, shape ``(N,)``.
        day: Along-track ordering key within each pass, shape ``(N,)``.
        pass_id: Pass group id per point, shape ``(N,)``.

    Returns:
        Tuple ``(rhos_used, factor)`` where ``rhos_used`` is the retained
        lag-autocorrelation array and ``factor = 1 + 2 * sum(rhos_used)`` is the
        variance-inflation factor such that ``n_eff = n / factor``.
    """
    z = np.asarray(z, dtype=float)
    day = np.asarray(day)
    pass_id = np.asarray(pass_id)

    max_lag = int(RHO_MAX_LAG)
    num = np.zeros(max_lag + 1)  # weighted sum of per-pass rho_k
    wgt = np.zeros(max_lag + 1)  # total pair count per lag

    for pid in np.unique(pass_id):
        sel = pass_id == pid
        order = np.argsort(day[sel], kind="stable")
        series = z[sel][order]
        m = series.size
        if m < 2:
            continue
        s = series - series.mean()
        denom = float(np.dot(s, s))
        if denom == 0.0:
            continue
        for k in range(1, min(max_lag, m - 1) + 1):
            pairs = m - k
            rho_k = float(np.dot(s[:-k], s[k:])) / denom
            num[k] += rho_k * pairs
            wgt[k] += pairs

    rhos_all = np.zeros(max_lag)
    for k in range(1, max_lag + 1):
        rhos_all[k - 1] = num[k] / wgt[k] if wgt[k] > 0 else 0.0

    # Truncate at the first lag below the cutoff.
    below = np.where(rhos_all < RHO_CUTOFF)[0]
    cut = int(below[0]) if below.size else max_lag
    rhos_used = rhos_all[:cut]

    factor = 1.0 + 2.0 * float(np.sum(rhos_used))
    return rhos_used, factor


def n_eff(n: float, rhos: np.ndarray) -> float:
    """Return the effective sample size ``n / (1 + 2*sum(rhos))``.

    Args:
        n: Raw sample count.
        rhos: Retained lag autocorrelations from :func:`rho_hat`.

    Returns:
        Effective sample size. With an empty ``rhos`` the correction is 1 and
        ``n_eff == n``.

    Raises:
        ValueError: If ``1 + 2*sum(rhos) <= 0``. :func:`rho_hat`'s truncation
            (only lags with ``rho_k >= RHO_CUTOFF > 0`` are retained)
            guarantees ``factor >= 1``; arbitrary negative rhos are a caller
            error, not a valid input.
    """
    factor = 1.0 + 2.0 * float(np.sum(rhos))
    if factor <= 0.0:
        raise ValueError(
            f"n_eff factor must be positive, got {factor}; rho_hat truncation "
            "guarantees factor >= 1 — arbitrary negative rhos are caller error"
        )
    return float(n) / factor


# ---------------------------------------------------------------------------
# merge_small_blocks
# ---------------------------------------------------------------------------


def merge_small_blocks(
    layout: tuple[frozenset[int], ...],
    n_eff_per_block: dict[int, float],
) -> tuple[tuple[frozenset[int], ...], dict[int, int]]:
    """Merge under-powered blocks into their nearest same-fold neighbour.

    A block whose ``n_eff`` is below ``MIN_N_EFF`` is merged into the block of
    the **same fold** with the nearest centroid (Euclidean distance in the
    lon/lat plane). Ties in centroid distance resolve to the lowest target
    block index. Only above-threshold blocks are eligible merge targets; if a
    fold has no above-threshold block a tiny block is left un-merged
    (maps to itself).

    Args:
        layout: Fold layout from :func:`s_fold_layout`.
        n_eff_per_block: Effective sample size per block id (0..24).

    Returns:
        Tuple ``(merged_layout, mapping)`` where ``mapping`` sends every block
        id to the block id it now belongs to (identity for un-merged blocks),
        and ``merged_layout`` has the same fold structure with each tiny block's
        id relabelled to its target's id (so a merged block joins its target's
        set and no longer stands alone).
    """
    mapping: dict[int, int] = {b: b for b in range(_N_BLOCKS)}

    for fold in layout:
        fold_blocks = sorted(fold)
        eligible = [b for b in fold_blocks if n_eff_per_block.get(b, 0.0) >= MIN_N_EFF]
        tiny = [b for b in fold_blocks if n_eff_per_block.get(b, 0.0) < MIN_N_EFF]
        if not eligible:
            continue
        for b in tiny:
            cx, cy = _block_centroid(b)
            best_target = None
            best_dist = math.inf
            for t in eligible:
                tx, ty = _block_centroid(t)
                dist = math.hypot(cx - tx, cy - ty)
                # Lowest-index tie-break: `eligible` is ascending, so `<`
                # keeps the first (lowest-index) block on exact ties.
                if dist < best_dist:
                    best_dist = dist
                    best_target = t
            if best_target is None:  # pragma: no cover - eligible non-empty
                continue
            mapping[b] = best_target

    # Rebuild folds with tiny blocks relabelled to their target id.
    merged: list[frozenset[int]] = []
    for fold in layout:
        new_ids = {mapping[b] for b in fold}
        merged.append(frozenset(new_ids))
    return tuple(merged), mapping


# ---------------------------------------------------------------------------
# pooled_worst_region
# ---------------------------------------------------------------------------


def pooled_worst_region(
    cov_by_region: dict[str, tuple[int, int]],
) -> tuple[float, dict[str, float]]:
    """Return the worst per-region coverage deviation and the per-region table.

    Held-out points are pooled per region across the family's folds (the caller
    accumulates ``(n_covered, n_total)`` before calling). For each region the
    coverage is ``n_covered / n_total`` and its score is
    ``|coverage - COVERAGE_TARGET|``. The worst value is the max over regions.

    Args:
        cov_by_region: Region -> ``(n_covered, n_total)`` pooled across folds.

    Returns:
        Tuple ``(worst_value, per_region_table)`` where ``per_region_table``
        maps region -> ``|coverage - COVERAGE_TARGET|``.
    """
    table: dict[str, float] = {}
    for region, (n_cov, n_tot) in cov_by_region.items():
        if n_tot == 0:
            table[region] = float("nan")
            continue
        coverage = n_cov / n_tot
        table[region] = abs(coverage - COVERAGE_TARGET)
    finite = [v for v in table.values() if not math.isnan(v)]
    worst = max(finite) if finite else float("nan")
    return worst, table


# ---------------------------------------------------------------------------
# select
# ---------------------------------------------------------------------------


def _beats_beyond_band(candidate: float, baseline: float) -> bool:
    """Return whether ``candidate`` beats ``baseline`` beyond the tie band.

    Lower is better. "Beyond" means strictly better than ``baseline`` by more
    than the ABSOLUTE ``TIE_BAND``: ``candidate < baseline - TIE_BAND``. The
    band is absolute per the owner ruling 2026-07-11 (band ≈ 2×pooled-coverage-
    SE ≈ 0.01; the earlier relative reading was rejected as inside noise).
    """
    return candidate < baseline - TIE_BAND


def _no_worse_than(candidate: float, baseline: float) -> bool:
    """Return whether ``candidate`` is no worse than ``baseline`` within band.

    True when ``candidate`` is better or ties within the ABSOLUTE ``TIE_BAND``
    (``candidate <= baseline + TIE_BAND``); False only when ``candidate`` is
    worse than ``baseline`` beyond the band.
    """
    return candidate <= baseline + TIE_BAND


def select(
    lanes: list[dict[str, object]],
) -> tuple[dict[str, object] | None, list[dict[str, object]]]:
    """Select the winning lane by lane-0 eligibility + lexicographic order.

    ``lanes[0]`` is the lane-0 baseline (the shipped scalar). The tie band is
    ABSOLUTE ±``TIE_BAND`` on the selection statistic (owner ruling 2026-07-11:
    band ≈ 2×pooled-coverage-SE ≈ 0.01; the earlier relative reading was
    rejected). A candidate lane is **eligible** iff it beats lane-0 on the
    PRIMARY statistic (``s_stat``, the S-fold pooled-worst-region) beyond the
    band — ``s_stat < lane0_s − TIE_BAND`` — AND is no worse than lane-0 on the
    SECONDARY statistic (``t_stat``, the T-fold pooled-worst-region) within the
    band — ``t_stat <= lane0_t + TIE_BAND``. Lower statistics are better.

    Among eligible lanes the winner is chosen lexicographically:

    1. lowest ``s_stat`` (beating the running winner by more than ``TIE_BAND``
       wins outright);
    2. on an S tie within band, lowest ``t_stat``;
    3. on a further T tie within band, the smooth-lane preference order
       ``poly > covariate > piecewise``.

    Args:
        lanes: Lane records; each a mapping with keys ``name`` (str),
            ``s_stat`` (float, S-fold statistic), ``t_stat`` (float, T-fold
            statistic). ``lanes[0]`` is lane-0.

    Returns:
        Tuple ``(winner, table)``. ``winner`` is the selected lane record, or
        ``None`` for a negative result (no eligible lane). ``table`` is the
        input lane list (unchanged) for downstream serialisation.
    """
    if not lanes:
        return None, lanes
    lane0 = lanes[0]
    l0_s = float(lane0["s_stat"])  # type: ignore[arg-type]
    l0_t = float(lane0["t_stat"])  # type: ignore[arg-type]

    eligible: list[dict[str, object]] = []
    for lane in lanes[1:]:
        s = float(lane["s_stat"])  # type: ignore[arg-type]
        t = float(lane["t_stat"])  # type: ignore[arg-type]
        if _beats_beyond_band(s, l0_s) and _no_worse_than(t, l0_t):
            eligible.append(lane)

    if not eligible:
        return None, lanes

    def _pref_rank(lane: dict[str, object]) -> int:
        name = str(lane["name"])
        return (
            _SMOOTH_PREFERENCE.index(name)
            if name in _SMOOTH_PREFERENCE
            else len(_SMOOTH_PREFERENCE)
        )

    # Winner reduction through the Phase-11 Policy seam: three criteria
    # mirroring the legacy loop EXACTLY — the S/T stages are banded closures
    # over the ABSOLUTE ±TIE_BAND helpers (A_WINS iff the challenger beats
    # beyond band, B_WINS iff the incumbent does, else TIE); the smooth
    # preference stage: A_WINS iff strictly lower _pref_rank. Candidate order
    # pinned = `eligible` list order — winner() is the same
    # keep-running-winner loop shape (gate i: leaf-identical harness
    # evidence pre/post migration).

    def _stat_criterion(key: str) -> Criterion[dict[str, object]]:
        def _compare(a: dict[str, object], b: dict[str, object]) -> Verdict:
            ca = float(a[key])  # type: ignore[arg-type]
            cb = float(b[key])  # type: ignore[arg-type]
            if _beats_beyond_band(ca, cb):
                return Verdict.A_WINS
            if _beats_beyond_band(cb, ca):
                return Verdict.B_WINS
            return Verdict.TIE

        return Criterion(key, _compare, banded=True)

    def _pref_criterion(a: dict[str, object], b: dict[str, object]) -> Verdict:
        if _pref_rank(a) < _pref_rank(b):
            return Verdict.A_WINS
        if _pref_rank(b) < _pref_rank(a):
            return Verdict.B_WINS
        return Verdict.TIE

    policy: LexicographicPolicy[dict[str, object]] = LexicographicPolicy(
        (
            _stat_criterion("s_stat"),
            _stat_criterion("t_stat"),
            Criterion("smooth_preference", _pref_criterion),
        )
    )
    winner, _audit = policy.winner(eligible)
    return winner, lanes
