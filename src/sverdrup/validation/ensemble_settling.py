"""Member-partition settling measurement for the σ route (owner pin 43).

Pin 43 refused to seal an attributability factor derived from two samples
with a known-broken ``N_eff`` estimator, and ordered the settling
measured directly instead: replay the persisted member stores into
~200 DISJOINT random member partitions per tile — no solves — and read
the realized null distribution of

    T = RMS(sigma_A - sigma_B) / F_ens ,  F_ens = sigma_pooled/sqrt(size-1)

off it. The construction is non-parametric in ``N_eff``: it never models
the spatial correlation, it resamples the field that carries it.

**NOT VERDICT-BEARING (owner pin 49).** Nothing in this module licenses a
σ verdict. The entire rubric amendment — Rule 0.a's text and Rule 0.b
together — is DEFERRED to T17, to be sealed once against the CRN-paired
configuration T14 creates. This module measures; T17 adjudicates. No
verdict path imports it.

**CAVEAT THE MEASUREMENT CARRIES (pin 43a).** Partitions of the SAME
recorded members share draws, so the between-partition spread measures
COMBINATORIAL variability, not ensemble-to-ensemble variability, and
UNDERSTATES the true null spread. It is recorded beside every number
derived from it, never left to be inferred.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from sverdrup.validation.seam_metrics import (
    ensemble_floor,
    seam_delta,
    sigma_level_rms,
)

__all__ = ["disjoint_partitions", "expected_t", "member_sigma", "settling_ratios"]


def disjoint_partitions(
    *, m_total: int, size: int, n_partitions: int, seed: int
) -> NDArray[np.int64]:
    """Draw distinct partitions of the member set into two disjoint subsets.

    Each partition is two subsets of ``size`` members with no member in
    common, so the two σ estimates built from them are as independent as
    the recorded ensemble allows. A split and its mirror are the SAME
    partition and are never both returned.

    Args:
        m_total: Members in the recorded ensemble.
        size: Members in each side of a partition.
        n_partitions: Partitions to draw.
        seed: Seed of the draw — the measurement must be reproducible by
            anyone who reads the record.

    Returns:
        ``(n_partitions, 2, size)`` member indices.

    Raises:
        ValueError: If ``size`` is below 2 (a one-member subset has no
            sample σ), if ``2*size`` exceeds ``m_total`` (the two sides
            could not be disjoint), if ``n_partitions`` is below 1, or if
            fewer than ``n_partitions`` distinct partitions exist.
    """
    if size < 2:
        raise ValueError(f"each side needs at least 2 members to have a σ: {size}")
    if 2 * size > m_total:
        raise ValueError(
            f"two disjoint sides of {size} need {2 * size} members, "
            f"ensemble has {m_total}"
        )
    if n_partitions < 1:
        raise ValueError(f"n_partitions must be positive: {n_partitions}")

    available = _distinct_partition_count(m_total, size)
    if n_partitions > available:
        raise ValueError(
            f"only {available} distinct partitions of {m_total} members into "
            f"two disjoint sides of {size} exist; {n_partitions} requested"
        )

    rng = np.random.default_rng(seed)
    seen: set[frozenset[frozenset[int]]] = set()
    drawn: list[NDArray[np.int64]] = []
    # Bounded rejection: the loop cannot outlive the space because the
    # distinct-count check above already proved enough partitions exist,
    # and every accepted draw removes one from the space.
    attempts = 0
    max_attempts = 1000 * n_partitions + 1000
    while len(drawn) < n_partitions:
        attempts += 1
        if attempts > max_attempts:  # pragma: no cover - guards a pathology
            raise RuntimeError(
                f"drew {attempts} times for {n_partitions} distinct partitions; "
                "the partition space is too small for rejection sampling"
            )
        picked = rng.permutation(m_total)[: 2 * size]
        first, second = picked[:size], picked[size:]
        key = frozenset(
            (frozenset(int(i) for i in first), frozenset(int(i) for i in second))
        )
        if key in seen:
            continue
        seen.add(key)
        drawn.append(np.stack([np.sort(first), np.sort(second)]).astype(np.int64))
    return np.stack(drawn)


def _distinct_partition_count(m_total: int, size: int) -> int:
    """Number of distinct two-disjoint-side partitions.

    A partition is the UNORDERED pair ``{A, B}``: which side is called
    first carries no meaning, so a split and its mirror are one
    partition. Choosing ``A`` then ``B`` counts ordered pairs, hence the
    factor of 2 — which applies whether or not members are left over.

    Args:
        m_total: Members in the recorded ensemble.
        size: Members in each side.

    Returns:
        Count of distinct unordered partitions.
    """
    from math import comb  # noqa: PLC0415

    return comb(m_total, size) * comb(m_total - size, size) // 2


def member_sigma(
    member_fields: ArrayLike, members: Sequence[int] | NDArray[np.int64]
) -> NDArray[np.float64]:
    """Member standard deviation over a SUBSET of the recorded members.

    Reproduces the production evaluator's own reduction: the lineage
    ``std_fields`` builds the per-member blended field ``acc`` of shape
    ``(n_nodes, m)`` and takes ``acc.std(axis=1, ddof=1)``, so a σ built
    here from the captured per-member fields is the same arithmetic on
    the same numbers — not an approximation of it.

    **The member axis is the LAST one, and that is load-bearing, not a
    convention.** With members fastest-varying, the reduction runs over
    a unit-stride block of exactly ``m`` values, the way the evaluator's
    does, and reproduces the persisted map BIT-FOR-BIT. With members on
    axis 0 the same values reduce in a different order and land a few
    ULP away — measured at ``4.2e-17`` on the real strip, which is
    harmless in size but forfeits the exactness claim the whole replay
    rests on.

    Non-finite member values propagate (land stays land). ``nanstd`` is
    deliberately NOT used: it would silently vary the member count per
    node, and the floor's ``m`` would no longer describe the field.

    Args:
        member_fields: ``(..., m)`` per-member fields, member LAST.
        members: Indices of the members to pool.

    Returns:
        The subset's σ field, shape ``member_fields.shape[:-1]``.

    Raises:
        ValueError: If fewer than 2 members are selected — the ``(m-1)``
            denominator is undefined there, and a NaN would enter the
            record as a missing row rather than a broken one.
    """
    idx = np.asarray(members, dtype=np.int64)
    if idx.size < 2:
        raise ValueError(f"σ needs at least 2 members, got {idx.size}")
    fields = np.asarray(member_fields, dtype=np.float64)
    out: NDArray[np.float64] = fields[..., idx].std(axis=-1, ddof=1)
    return out


def settling_ratios(
    member_fields: ArrayLike, partitions: ArrayLike
) -> NDArray[np.float64]:
    """The realized ``T = RMS(Δσ)/F_ens`` for each partition.

    The floor uses the POOLED σ level of the two fields being differenced
    (owner pin 38, the quadratic mean) rather than the arithmetic mean of
    their two levels: ``Var(σ_a − σ_b) = (σa² + σb²)/(2(m−1))``. The two
    forms coincide on the null and diverge as the levels separate, so the
    pooled form is the one that stays right where it has to work.

    Args:
        member_fields: ``(..., m)`` per-member fields, member LAST — see
            :func:`member_sigma` for why the axis order is load-bearing.
        partitions: ``(n, 2, size)`` member indices, as returned by
            :func:`disjoint_partitions`.

    Returns:
        ``(n,)`` ratios, one per partition, in partition order — the
        distribution itself, which is what pin 43 ordered measured.

    Raises:
        ValueError: If ``partitions`` is not ``(n, 2, size)``, or if any
            index falls outside ``[0, m)``. Negative indices are refused
            rather than wrapped: numpy would silently select a member
            from the other end and the two sides would share it.
    """
    fields = np.asarray(member_fields, dtype=np.float64)
    parts = np.asarray(partitions, dtype=np.int64)
    if parts.ndim != 3 or parts.shape[1] != 2:
        raise ValueError(f"partitions must have shape (n, 2, size), got {parts.shape}")
    m_total = fields.shape[-1]
    if parts.size and (int(parts.min()) < 0 or int(parts.max()) >= m_total):
        raise ValueError(
            f"member index out of range for a {m_total}-member ensemble: "
            f"[{int(parts.min())}, {int(parts.max())}]"
        )

    size = int(parts.shape[2])
    ratios = np.empty(parts.shape[0], dtype=np.float64)
    for i, (first, second) in enumerate(parts):
        sigma_a = member_sigma(fields, first)
        sigma_b = member_sigma(fields, second)
        floor = ensemble_floor(sigma_level_rms(sigma_a, sigma_b), size)
        ratios[i] = seam_delta(sigma_a, sigma_b) / floor
    return ratios


def expected_t(m: int) -> float:
    """Exact ``E[T]`` under the iid-node Gaussian null (owner pin 54).

    The floor ``F_ens = sigma/sqrt(m-1)`` is the ASYMPTOTIC standard
    deviation of a sigma difference. The exact one is smaller, because a
    sample standard deviation is a biased estimate of sigma with
    ``E[s] = c4(m) * sigma`` and ``Var(s) = sigma^2 (1 - c4^2)``. For two
    independent estimates ``E[(s_a - s_b)^2] = 2 sigma^2 (1 - c4^2)``, so

        E[T] = sqrt(2 (m-1) (1 - c4(m)^2)) ,
        c4(m) = sqrt(2/(m-1)) * Gamma(m/2) / Gamma((m-1)/2) .

    This is why the measured null sits just BELOW 1 and why it drifts
    with ``m``: pin 43(b)'s m-invariance assumption is FALSE, and this
    closed form is the whole of the departure. Owner pin 54 endorsed
    using it EXACTLY rather than covering the drift with margin, on the
    standing condition that it be **test-pinned at the m actually used**,
    since it will be sealed and applied at m values the settling
    measurement never ran.

    **NOT VERDICT-BEARING (owner pin 49)**, and note the companion
    condition of pin 54: the settling measurement's ``n = 200`` supports
    quantiles to about q95-q99 only. ``q999`` is NOT estimable from it,
    and **no threshold may rely on a quantile the measurement cannot
    reach.**

    Args:
        m: Members behind each of the two sigma estimates.

    Returns:
        The exact expected value of ``T`` under the null.

    Raises:
        ValueError: If ``m`` is below 2 — a single member has no sample
            sigma, so there is no ``T`` to take an expectation of.
    """
    if m < 2:
        raise ValueError(f"E[T] needs at least 2 members per side, got {m}")
    log_c4 = (
        0.5 * math.log(2.0 / (m - 1))
        + math.lgamma(m / 2.0)
        - math.lgamma((m - 1) / 2.0)
    )
    c4 = math.exp(log_c4)
    return math.sqrt(2.0 * (m - 1) * (1.0 - c4 * c4))
