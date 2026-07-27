"""Null distribution of the σ-route ensemble-floor ratio (owner pin 36b).

The Rule-0.b attributability factor is DERIVED here, not picked. Owner
ruling 2026-07-27 pin 36: the solver floor's 3× margin does not transfer
to the ensemble floor, because ``F_ens`` is the EXPECTATION of a sampling
statistic whose null distribution is tightly concentrated — a 3× threshold
discards any true artifact below ~2.8× the floor and leaves the σ
instrument with no reachable CLEAN or ELEVATED cell.

**The null is exactly scale-free.** For Gaussian members the sample std of
an ``m``-member ensemble satisfies ``s = (sigma/sqrt(m-1)) * sqrt(chi2)``
with ``chi2`` on ``m-1`` degrees of freedom, so for two INDEPENDENT
estimates of the same field (no seam)

    T = RMS(sigma_delta) / F_ens = weighted-RMS( sqrt(chi2_a) - sqrt(chi2_b) )

over the effectively-independent nodes. ``T`` therefore depends only on
``m``, the effective independent node count ``N_eff``, and the σ-level
weights — never on ``sigma`` itself. Two consequences worth stating:

- ``E[T] = sqrt(2(1 - c4^2)(m-1))`` exactly, where ``c4 = E[s]/sigma``.
  This is 0.99835 at m=100: the ``sigma/sqrt(m-1)`` floor sits 0.17%
  ABOVE the exact expected RMS. That gap is the asymptotic-approximation
  error the ruling asks to be given explicit margin.
- The spatial and TEMPORAL correlation of the σ field enters only through
  ``N_eff`` (:func:`effective_node_count`). Time dominates here: the σ
  error at a node is a function of the member draws, which are shared
  across every output day, so counting days as independent nodes would
  overstate ``N_eff`` by ~365× and understate the null spread by ~19×.

Pure numpy — no solver imports, no file I/O.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import ArrayLike, NDArray


def null_t_samples(
    *,
    m: int,
    n_eff: int,
    k: int,
    seed: int,
    weights: ArrayLike | None = None,
) -> NDArray[np.float64]:
    """Draw ``k`` samples of the null ratio ``T`` at member count ``m``.

    Each sample is the (optionally σ²-weighted) RMS over ``n_eff``
    independent nodes of ``sqrt(chi2_a) - sqrt(chi2_b)``, with both chi2
    variates on ``m-1`` degrees of freedom — the exact null of
    ``RMS(sigma_delta)/F_ens`` for two independent m-member σ estimates of
    the same field.

    Args:
        m: Members behind each σ estimate.
        n_eff: Effectively-independent node count of the evaluation domain.
        k: Replications to draw.
        seed: Seed (explicit — the derivation is reproducible).
        weights: Optional per-node σ² weights (length ``n_eff``); the
            recorded σ field is not flat, and heterogeneity widens the
            null. Defaults to equal weights.

    Returns:
        ``(k,)`` array of null ``T`` values.

    Raises:
        ValueError: If ``m`` is below 2 (no member-std, hence no null), if
            ``k`` or ``n_eff`` is below 1, or if ``weights`` has the wrong
            length or is not positive.
    """
    if m < 2:
        raise ValueError(f"member-std needs m >= 2, got {m}")
    if n_eff < 1 or k < 1:
        raise ValueError(f"n_eff and k must be >= 1, got n_eff={n_eff}, k={k}")
    dof = m - 1
    rng = np.random.default_rng(seed)
    if weights is None:
        w = np.full(n_eff, 1.0 / n_eff)
    else:
        w_in = np.asarray(weights, dtype=np.float64).ravel()
        if w_in.size != n_eff:
            raise ValueError(
                f"weights length {w_in.size} != n_eff {n_eff}: the weights are "
                "per effectively-independent node"
            )
        if not np.all(w_in > 0) or not np.all(np.isfinite(w_in)):
            raise ValueError("weights must be finite and positive")
        w = w_in / w_in.sum()
    out = np.empty(k, dtype=np.float64)
    # Chunked so a large k x n_eff draw never materializes at once.
    chunk = max(1, int(4_000_000 // n_eff))
    done = 0
    while done < k:
        rows = min(chunk, k - done)
        a = np.sqrt(rng.chisquare(dof, size=(rows, n_eff)))
        b = np.sqrt(rng.chisquare(dof, size=(rows, n_eff)))
        d = a - b
        out[done : done + rows] = np.sqrt(np.einsum("ij,j->i", d * d, w))
        done += rows
    return out


def node_term_moments(
    *, m: int, n_pool: int = 100_000_000, seed: int = 20260727
) -> dict[str, float]:
    """Per-node moments of ``u = (sqrt(chi2_a) - sqrt(chi2_b))^2``.

    Measured once from a large pool of independent draws, so the null
    quantile at ANY ``N_eff`` follows analytically (see
    :func:`null_t_quantile`) instead of requiring ``k * N_eff`` draws per
    replication — at the recorded ``N_eff`` of ~2.3e4 the direct product
    is ~1e10 draws, which is not a derivation anyone re-runs.

    Args:
        m: Members behind each σ estimate.
        n_pool: Pool size for the moment estimates.
        seed: Explicit seed — the derivation is reproducible.

    Returns:
        ``{"mean", "var", "skew", "n_pool", "m"}`` for the per-node term.

    Raises:
        ValueError: If ``m`` is below 2 or ``n_pool`` below 1000.
    """
    if m < 2:
        raise ValueError(f"member-std needs m >= 2, got {m}")
    if n_pool < 1000:
        raise ValueError(f"n_pool must be >= 1000, got {n_pool}")
    dof = m - 1
    rng = np.random.default_rng(seed)
    total = np.zeros(3, dtype=np.float64)  # sum u, sum u^2, sum u^3
    done = 0
    chunk = 20_000_000
    while done < n_pool:
        rows = min(chunk, n_pool - done)
        d = np.sqrt(rng.chisquare(dof, size=rows)) - np.sqrt(
            rng.chisquare(dof, size=rows)
        )
        u = d * d
        total[0] += float(u.sum())
        total[1] += float((u * u).sum())
        total[2] += float((u * u * u).sum())
        done += rows
    mean = total[0] / n_pool
    m2 = total[1] / n_pool - mean**2
    m3 = total[2] / n_pool - 3.0 * mean * (total[1] / n_pool) + 2.0 * mean**3
    return {
        "m": float(m),
        "n_pool": float(n_pool),
        "mean": float(mean),
        "var": float(m2),
        "skew": float(m3 / m2**1.5),
    }


def null_t_quantile(
    *,
    moments: dict[str, float],
    n_eff: int,
    confidence: float,
    weights: ArrayLike | None = None,
) -> float:
    """Upper ``confidence`` quantile of the null ``T`` at ``n_eff`` nodes.

    ``T^2`` is a weighted mean of iid per-node terms, so its mean is the
    per-node mean, its variance is ``var * sum(w^2)`` and its skewness is
    ``skew * sum(w^3)/sum(w^2)^1.5`` — exact for any weights. The quantile
    uses a Cornish-Fisher expansion (normal quantile plus the skewness
    term), which :func:`null_t_samples` validates against direct
    simulation.

    Args:
        moments: Output of :func:`node_term_moments`.
        n_eff: Effective independent node count.
        confidence: One-sided confidence (e.g. 0.999).
        weights: Optional per-node σ² weights (length ``n_eff``).

    Returns:
        The quantile of ``T`` (not ``T^2``).

    Raises:
        ValueError: If ``n_eff`` < 1, ``confidence`` is outside (0, 1), or
            ``weights`` has the wrong length.
    """
    if n_eff < 1:
        raise ValueError(f"n_eff must be >= 1, got {n_eff}")
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence must be in (0, 1), got {confidence}")
    if weights is None:
        w = np.full(n_eff, 1.0 / n_eff)
    else:
        w_in = np.asarray(weights, dtype=np.float64).ravel()
        if w_in.size != n_eff:
            raise ValueError(f"weights length {w_in.size} != n_eff {n_eff}")
        w = w_in / w_in.sum()
    s2 = float(np.sum(w**2))
    s3 = float(np.sum(w**3))
    mean = moments["mean"]
    sd = math.sqrt(moments["var"] * s2)
    skew = moments["skew"] * s3 / s2**1.5
    z = _normal_quantile(confidence)
    z_cf = z + (z * z - 1.0) * skew / 6.0
    return math.sqrt(max(mean + sd * z_cf, 0.0))


def _normal_quantile(p: float) -> float:
    """Standard-normal quantile via the inverse error function."""
    from math import erf  # noqa: PLC0415 - local, tiny

    lo, hi = -10.0, 10.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if 0.5 * (1.0 + erf(mid / math.sqrt(2.0))) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def effective_node_count(field: ArrayLike) -> float:
    """Effective independent node count of a (time, lat, lon) null field.

    For a mean-zero field with correlation ``rho``, the variance of
    ``mean(d^2)`` is ``2 sigma_d^4 sum_{x,y} rho(x,y)^2 / N^2``, which is
    the iid formula with ``N`` replaced by
    ``N_eff = N^2 / sum_{x,y} rho(x,y)^2``. Under stationarity that sum
    factorizes over lags, so

        N_eff = N / prod_axes( 1 + 2 * sum_{lag>0} (1 - lag/L) rho(lag)^2 )

    The ``(1 - lag/L)`` weight is the exact finite-domain pair count
    (``L - |lag|`` pairs at lag ``|lag|``), not a taper: with it, a fully
    correlated axis of length ``L`` divides by exactly ``L`` and an
    uncorrelated axis divides by exactly 1. A flat two-sided lag sum
    overcounts a fully correlated axis by nearly 2x.

    Separability across axes is an assumption, stated: it is exact for a
    product correlation and approximate otherwise.

    NaN (land) nodes are excluded pairwise from each lag correlation.

    Args:
        field: A null-realization field, ``(time, lat, lon)``.

    Returns:
        The effective independent node count (``1 <= N_eff <= N``).

    Raises:
        ValueError: If the field is not 3-D or has no finite values.
    """
    a = np.asarray(field, dtype=np.float64)
    if a.ndim != 3:
        raise ValueError(f"expected a (time, lat, lon) field, got shape {a.shape}")
    finite = np.isfinite(a)
    if not finite.any():
        raise ValueError("all-NaN field: no finite values to estimate N_eff from")
    n = int(finite.sum())
    centred = np.where(finite, a - float(np.mean(a[finite])), np.nan)
    total = 1.0
    for axis, length in enumerate(a.shape):
        # Sum of squared autocorrelations along this axis, lag 0 included.
        acc = 1.0
        for lag in range(1, length):
            x = np.take(centred, range(0, length - lag), axis=axis)
            y = np.take(centred, range(lag, length), axis=axis)
            both = np.isfinite(x) & np.isfinite(y)
            if not both.any():
                continue
            xv, yv = x[both], y[both]
            denom = float(np.sqrt(np.sum(xv * xv) * np.sum(yv * yv)))
            if denom == 0.0:
                continue
            rho = float(np.sum(xv * yv)) / denom
            # Two-sided (+lag and -lag) weighted by the finite-domain pair
            # count (L - lag)/L, so perfect correlation divides by exactly L.
            acc += 2.0 * (1.0 - lag / length) * rho * rho
        total *= acc
    return float(min(max(n / total, 1.0), n))


def clean_reachable(
    *, factor: float, f_ens: float, clean_max: float, d_int_sigma: float
) -> bool:
    """Owner pin 36c: is a CLEAN σ verdict reachable AT ALL?

    A σ verdict is attributable only above ``factor * F_ens`` and reads
    CLEAN only at or below ``clean_max * D_int_sigma``. Both can hold for
    some measurement iff

        factor * F_ens < clean_max * D_int_sigma

    A configuration failing this has no reachable CLEAN cell: every
    attributable σ verdict is ELEVATED or worse, and the only other
    outcome is UNMEASURED. This is the standing property every future
    threshold or floor change is checked against BEFORE sealing.

    Args:
        factor: The Rule-0.b attributability factor.
        f_ens: The ensemble floor for the pair.
        clean_max: The sealed CLEAN ceiling on the ratio.
        d_int_sigma: The σ-route interior reference dispersion.

    Returns:
        ``True`` if some measurement could read CLEAN.
    """
    return factor * f_ens < clean_max * d_int_sigma


def min_m_for_clean(
    *, factor: float, sigma_level: float, clean_max: float, d_int_sigma: float
) -> int:
    """Smallest ``m`` at which a CLEAN σ verdict becomes reachable.

    Substituting ``F_ens = sigma/sqrt(m-1)`` into
    :func:`clean_reachable` gives

        m - 1 > (factor * sigma / (clean_max * D_int_sigma))^2

    Args:
        factor: The Rule-0.b attributability factor.
        sigma_level: The pooled σ level of the domain.
        clean_max: The sealed CLEAN ceiling on the ratio.
        d_int_sigma: The σ-route interior reference dispersion.

    Returns:
        The smallest integer ``m >= 2`` satisfying the condition.

    Raises:
        ValueError: If any input is non-positive.
    """
    if min(factor, sigma_level, clean_max, d_int_sigma) <= 0:
        raise ValueError("factor, sigma_level, clean_max and d_int_sigma must be > 0")
    need = (factor * sigma_level / (clean_max * d_int_sigma)) ** 2
    m = int(np.floor(need)) + 2  # strict inequality on m-1
    return max(m, 2)
