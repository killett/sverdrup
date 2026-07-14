"""Method-agnostic lane-comparison bands: sealed PROTOCOL, read-time values.

Band PROTOCOL (Phase-10 spec §5/§9, owner plan-review correction 1 —
supersedes number-pre-registration): the pre-registered artifact carries the
PROCEDURE (seed, block unit, resample counts, machinery reference, the
λ-informative rule, the single-execution rule) and NO operative band values.
Band values are computed AT READ TIME on each actually-consulted pair via
:func:`compute_bands` — paired SE = f(Var_a + Var_b − 2Cov), so nested tuned
winners' error correlation is priced correctly; a probe-pair band would
over-size the noise and bias the PRIMARY verdict negative by construction.
Shopping is impossible: sealed seed, ONE seeded execution per consulted pair
(values + write-times land in the CONSUMING record), and every returned band
carries ``protocol_sha`` == sha256 of the sealed artifact bytes.

The refusal clock (:func:`assert_band_predates`) compares the PROTOCOL's
``created_utc`` against winner-record write-times INSIDE the JSON artifacts —
never file mtimes (spec §9, batch-3 fold 3).

This module is method-agnostic: no OI parameter names, no lane names — those
live in ``validation/phase10_lanes.py`` (Task 6).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from sverdrup.eval.skill_score import leaderboard_nrmse
from sverdrup.eval.spectral import (
    ShortTrackError,
    UnresolvedScaleError,
    effective_resolution_lambda_x,
)

# λ-informative rule (spec §5): a computed band wider than the λx grid
# resolution scale cannot separate physically plausible gains.
LAMBDA_INFORMATIVE_KM = 25.0

# Along-track pass segmentation gap (mirrors harness._PASS_GAP_SEC intent):
# the validation-track cadence is ~1.08 s; anything > 60 s is a new pass.
_PASS_GAP_SEC = 60.0


class PreRegistrationError(RuntimeError):
    """A band was requested outside the sealed protocol's discipline."""


@dataclass(frozen=True)
class BandProtocol:
    """The sealed band procedure (no operative values).

    Attributes:
        created_utc: Seal time (ISO 8601), the refusal clock's reference.
        resample_seed: The single seed for every read-time computation.
        block_unit: Human-readable block definition (contiguous day/pass).
        n_resamples: Block-bootstrap resamples for the Δµ band.
        n_lambda_resamples: Resamples for the Δλx band (the spectral
            estimator is orders of magnitude costlier than µ; a smaller,
            sealed count is pre-registered with rationale in the artifact).
        machinery: Reference to the segmentation machinery reused.
        lambda_informative_rule: The recorded λ rule text.
        single_execution_rule: The recorded single-execution rule text.
        protocol_sha: sha256 hex of the sealed artifact bytes.
    """

    created_utc: str
    resample_seed: int
    block_unit: str
    n_resamples: int
    n_lambda_resamples: int
    machinery: str
    lambda_informative_rule: str
    single_execution_rule: str
    protocol_sha: str


@dataclass(frozen=True)
class BandValues:
    """Read-time band values for ONE consulted pair (a vs b).

    Attributes:
        delta_mu: Point estimate µ_a − µ_b on the full paired track.
        delta_lambda_x: Point estimate λx_a − λx_b (NaN if either side
            failed the spectral estimate on the full track).
        band_mu: 2·SE of Δµ over the block-bootstrap resamples.
        band_lambda_x: 2·SE of Δλx over the λ resamples.
        lambda_informative: ``band_lambda_x <= 25 km`` (the sealed rule).
        n_segments: Number of contiguous day/pass blocks resampled.
        n_lambda_used: λ resamples that produced a value on BOTH sides.
        protocol_sha: The sealed protocol's sha256 (binding).
    """

    delta_mu: float
    delta_lambda_x: float
    band_mu: float
    band_lambda_x: float
    lambda_informative: bool
    n_segments: int
    n_lambda_used: int
    protocol_sha: str


def seal_protocol(
    path: Path,
    *,
    created_utc: str,
    probe_pair_reference: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """Write the sealed protocol artifact and return its sha256.

    Args:
        path: Destination JSON path (``phase10_band_artifact.json``).
        created_utc: ISO-8601 seal time written into the artifact.
        probe_pair_reference: Optional DEMOTED shakedown block (machinery
            shakedown + dissimilar-pair noise scale; never operative).
        extra: Optional co-sealed constants (the screening contingency block
            lives in the SAME artifact — spec §4); keys must not collide with
            the protocol schema.

    Returns:
        sha256 hex digest of the exact bytes written.
    """
    doc: dict[str, Any] = {
        "created_utc": created_utc,
        "resample_seed": 271828,
        "block_unit": "contiguous day/pass segments",
        "n_resamples": 2000,
        "n_lambda_resamples": 200,
        "n_lambda_resamples_rationale": (
            "the spectral λx estimator re-runs the vendored PSD pipeline per "
            "resample (~seconds each); 200 seeded resamples estimate SE(Δλx) "
            "to ~5% relative — adequate against the 25 km informativeness "
            "rule; sealed here BEFORE any trial"
        ),
        "machinery": "application/calibration folds rho/n_eff segmentation",
        "lambda_informative_rule": (
            "band_lambda_x <= 25 km, evaluated per computed pair"
        ),
        "single_execution_rule": (
            "one seeded computation per consulted pair; values recorded in "
            "the consuming record with write-times"
        ),
    }
    if probe_pair_reference is not None:
        doc["probe_pair_reference"] = probe_pair_reference
    if extra is not None:
        collisions = set(extra) & set(doc)
        if collisions:
            raise ValueError(
                f"extra keys collide with the protocol schema: {collisions}"
            )
        doc.update(extra)
    raw = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def load_protocol(path: Path, expected_sha: str | None = None) -> BandProtocol:
    """Load the sealed protocol, verifying its sha when a reference is given.

    Args:
        path: The sealed artifact path.
        expected_sha: The seal-time sha256 recorded in the evidence JSON;
            when given, a mismatch (any edit to the artifact) refuses.

    Returns:
        The loaded :class:`BandProtocol` (``protocol_sha`` = actual bytes').

    Raises:
        PreRegistrationError: If ``expected_sha`` is given and does not match
            the artifact bytes on disk.
    """
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if expected_sha is not None and sha != expected_sha:
        raise PreRegistrationError(
            f"band protocol sha mismatch: artifact {path} hashes to {sha}, "
            f"sealed reference is {expected_sha} — the protocol was modified "
            "after sealing; refuse every band"
        )
    d = json.loads(raw)
    return BandProtocol(
        created_utc=str(d["created_utc"]),
        resample_seed=int(d["resample_seed"]),
        block_unit=str(d["block_unit"]),
        n_resamples=int(d["n_resamples"]),
        n_lambda_resamples=int(d["n_lambda_resamples"]),
        machinery=str(d["machinery"]),
        lambda_informative_rule=str(d["lambda_informative_rule"]),
        single_execution_rule=str(d["single_execution_rule"]),
        protocol_sha=sha,
    )


def _day_float(time: np.ndarray) -> np.ndarray:
    """Return float days from a time column (datetime64 or numeric days)."""
    t = np.asarray(time)
    if np.issubdtype(t.dtype, np.datetime64):
        epoch = np.datetime64("2017-01-01")
        return np.asarray((t - epoch) / np.timedelta64(1, "s"), float) / 86400.0
    return np.asarray(t, float)


def _segments(day: np.ndarray) -> list[np.ndarray]:
    """Return contiguous day/pass block index arrays (the sealed block unit).

    A new block starts where the time gap exceeds the pass gap (the folds
    rho/n_eff pass segmentation) OR the integer day changes.

    Args:
        day: Float days, in track order.

    Returns:
        List of index arrays, one per contiguous block.
    """
    sec = day * 86400.0
    if np.any(np.diff(sec) < 0):
        raise ValueError(
            "track time must be non-decreasing for day/pass segmentation "
            "(backward jump found — corrupted or unsorted track)"
        )
    new_pass = np.diff(sec) > _PASS_GAP_SEC
    new_day = np.diff(np.floor(day)) != 0
    starts = np.concatenate([[0], np.flatnonzero(new_pass | new_day) + 1])
    bounds = np.concatenate([starts, [day.size]])
    return [np.arange(bounds[i], bounds[i + 1]) for i in range(starts.size)]


def _mu(ssh: np.ndarray, interp: np.ndarray, idx: np.ndarray) -> float:
    return leaderboard_nrmse(ssh[idx], interp[idx])


def compute_bands(
    track_a: Mapping[str, np.ndarray],
    track_b: Mapping[str, np.ndarray],
    protocol: BandProtocol,
    lambda_x_fn: Callable[..., float] = effective_resolution_lambda_x,
) -> BandValues:
    """Compute the pair's Δµ/Δλx point estimates and 2·SE bands at read time.

    Blocks are contiguous day/pass segments; each resample draws blocks with
    replacement (moving-block bootstrap) and re-scores BOTH sides on the
    identical resampled point set — the paired design that prices the error
    correlation between nested tuned winners.

    Args:
        track_a: Side-a arrays: ``time, lat, lon, ssh, mean_interp``.
        track_b: Side-b arrays, SAME consulted track (asserted).
        protocol: The sealed protocol (seed, counts, rules).
        lambda_x_fn: The λx estimator (injectable for tests).

    Returns:
        The :class:`BandValues` carrying the protocol's sha.

    Raises:
        ValueError: If the two sides are not the same consulted track.
    """
    for key in ("time", "lat", "lon", "ssh"):
        if not np.array_equal(np.asarray(track_a[key]), np.asarray(track_b[key])):
            raise ValueError(
                f"paired band requires the SAME consulted track on both sides; "
                f"{key!r} differs"
            )
    time = np.asarray(track_a["time"])
    lat = np.asarray(track_a["lat"], float)
    lon = np.asarray(track_a["lon"], float)
    ssh = np.asarray(track_a["ssh"], float)
    ia = np.asarray(track_a["mean_interp"], float)
    ib = np.asarray(track_b["mean_interp"], float)

    day = _day_float(time)
    blocks = _segments(day)
    n_blocks = len(blocks)
    if n_blocks < 2:
        raise ValueError(
            f"need >= 2 day/pass blocks for a block bootstrap, got {n_blocks}"
        )

    delta_mu = _mu(ssh, ia, np.arange(ssh.size)) - _mu(ssh, ib, np.arange(ssh.size))
    try:
        lx_a = float(lambda_x_fn(time, lat, lon, ssh, ia))
        lx_b = float(lambda_x_fn(time, lat, lon, ssh, ib))
        delta_lx = lx_a - lx_b
    except (ShortTrackError, UnresolvedScaleError):
        delta_lx = float("nan")

    rng = np.random.default_rng(protocol.resample_seed)
    d_mu = np.empty(protocol.n_resamples)
    for r in range(protocol.n_resamples):
        draw = rng.integers(0, n_blocks, size=n_blocks)
        idx = np.concatenate([blocks[j] for j in draw])
        d_mu[r] = _mu(ssh, ia, idx) - _mu(ssh, ib, idx)
    band_mu = 2.0 * float(np.std(d_mu, ddof=1))

    d_lx: list[float] = []
    for _ in range(protocol.n_lambda_resamples):
        draw = rng.integers(0, n_blocks, size=n_blocks)
        idx = np.concatenate([blocks[j] for j in draw])
        try:
            va = float(lambda_x_fn(time[idx], lat[idx], lon[idx], ssh[idx], ia[idx]))
            vb = float(lambda_x_fn(time[idx], lat[idx], lon[idx], ssh[idx], ib[idx]))
        except (ShortTrackError, UnresolvedScaleError):
            continue
        d_lx.append(va - vb)
    band_lx = 2.0 * float(np.std(np.asarray(d_lx), ddof=1)) if len(d_lx) >= 2 else 0.0

    return BandValues(
        delta_mu=float(delta_mu),
        delta_lambda_x=float(delta_lx),
        band_mu=band_mu,
        band_lambda_x=band_lx,
        lambda_informative=band_lx <= LAMBDA_INFORMATIVE_KM,
        n_segments=n_blocks,
        n_lambda_used=len(d_lx),
        protocol_sha=protocol.protocol_sha,
    )


def assert_band_predates(protocol: BandProtocol, records: list[dict[str, Any]]) -> None:
    """Refuse unless the sealed protocol predates every consulted record.

    Timestamps are read INSIDE the artifacts (``created_utc`` fields), never
    from file mtimes (spec §9, batch-3 fold 3).

    Args:
        protocol: The sealed protocol.
        records: Winner/verdict records, each carrying ``created_utc``.

    Raises:
        PreRegistrationError: If any record's write-time does not postdate
            the protocol's seal time (a post-hoc protocol proves nothing).
    """
    sealed = datetime.fromisoformat(protocol.created_utc)
    if sealed.tzinfo is None:
        raise PreRegistrationError(
            f"protocol created_utc {protocol.created_utc!r} is not timezone-"
            "aware — the refusal clock refuses ambiguous timestamps"
        )
    for rec in records:
        written = datetime.fromisoformat(str(rec["created_utc"]))
        if written.tzinfo is None:
            raise PreRegistrationError(
                f"record created_utc {rec['created_utc']!r} is not timezone-"
                "aware — the refusal clock refuses ambiguous timestamps"
            )
        if written <= sealed:
            raise PreRegistrationError(
                f"protocol (sealed {protocol.created_utc}) must predate every "
                f"consulted record; record written {rec['created_utc']} does "
                "not postdate the seal"
            )
