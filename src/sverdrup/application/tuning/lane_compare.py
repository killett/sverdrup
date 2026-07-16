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

from sverdrup.application.policy import Criterion, LexicographicPolicy, Verdict
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


# Fraction of the sealed λ resamples that must produce a value on BOTH sides
# for the λ band to be usable (spec-review Task-5 finding: a band on too few
# successful spectral resamples must not fire the tie-break).
_LAMBDA_USED_FLOOR_FRACTION = 0.5


def _lambda_usable(bv: BandValues, protocol: BandProtocol) -> tuple[bool, str | None]:
    """Return (usable, note) for the λ tie-break under the sealed rules.

    Degradation branches (spec §5 self-calibration): a band wider than the
    informativeness rule, an under-sampled band, or a failed point estimate
    all degrade the rule to µ-primary with a recorded note — never a noisy
    verdict.
    """
    if not np.isfinite(bv.delta_lambda_x):
        return False, "λx point estimate failed on the full track — µ-primary"
    floor = int(np.ceil(_LAMBDA_USED_FLOOR_FRACTION * protocol.n_lambda_resamples))
    if bv.n_lambda_used < floor:
        return False, (
            f"λx band under-sampled (n_used={bv.n_lambda_used} < floor {floor} "
            f"of {protocol.n_lambda_resamples} sealed resamples) — µ-primary"
        )
    if not bv.lambda_informative:
        return False, (
            f"λx uninformative at measured band "
            f"(band={bv.band_lambda_x:.1f} km > {LAMBDA_INFORMATIVE_KM} km) — "
            "µ-primary"
        )
    return True, None


def _one_sided_criteria(bv: BandValues, usable: bool) -> tuple[Criterion[str], ...]:
    """Primary-verdict criteria closing over ONE :class:`BandValues`.

    Orientation: challenger = side a (the lat lane), incumbent = side b
    (lane-0). µ stage: A_WINS iff Δµ > band; B_WINS iff a is WORSE beyond
    band (decisive non-positive — the legacy ``abs(Δµ) <= band`` gate on the
    λ stage, expressed as a verdict); TIE inside the band. λ stage (present
    iff usable — degradation = the site DROPPING the criterion, the seam has
    no conditionals): A_WINS iff −Δλx > band (finer beyond band), else TIE.
    """

    def _mu(a: str, b: str) -> Verdict:
        if bv.delta_mu > bv.band_mu:
            return Verdict.A_WINS
        if -bv.delta_mu > bv.band_mu:
            return Verdict.B_WINS
        return Verdict.TIE

    def _lam(a: str, b: str) -> Verdict:
        if -bv.delta_lambda_x > bv.band_lambda_x:
            return Verdict.A_WINS
        return Verdict.TIE

    criteria: list[Criterion[str]] = [Criterion("mu", _mu, banded=True)]
    if usable:
        criteria.append(Criterion("lambda_x", _lam, banded=True))
    return tuple(criteria)


def adjudicate_primary(bv: BandValues, usable: bool) -> tuple[str, bool]:
    """Seam-backed PRIMARY branch selection (the reproduction entry point).

    Accepts :class:`BandValues` directly — computed by the site at read
    time, or RECONSTRUCTED from persisted verdict fields (bands-as-data;
    gate ii replays the Phase-10 verdict through this function).

    Args:
        bv: The pair's band values (side a = the candidate lane).
        usable: The :func:`_lambda_usable` outcome (λ criterion dropped
            when False).

    Returns:
        ``(branch, positive)`` with branch in
        {"beats-mu", "beats-lambda-at-flat-mu", "within-band"} — emitted
        from the audit trail, verbatim mapping.
    """
    policy: LexicographicPolicy[str] = LexicographicPolicy(
        _one_sided_criteria(bv, usable)
    )
    _winner, audits = policy.winner(["lane0", "candidate"])
    last = audits[0][-1]
    if last.criterion == "mu" and last.verdict == "A_WINS":
        return "beats-mu", True
    if last.criterion == "lambda_x" and last.verdict == "A_WINS":
        return "beats-lambda-at-flat-mu", True
    return "within-band", False


def primary_wording(a_lane_label: str, positive: bool, branch: str) -> str:
    """The pinned verdict wording (batch-2 fold 1), from the branch.

    A non-positive outcome reads "improvements within band", never "worse".
    """
    return (
        f"{a_lane_label} beats lane-0 beyond the measured band ({branch})"
        if positive
        else "improvements within band"
    )


def adjudicate_lane_pair(bv: BandValues, usable: bool) -> str:
    """Seam-backed within-lane top-2 branch selection.

    Symmetric variants of the criteria (|Δ| > band picks the side); the λ
    criterion is DROPPED when unusable. Orientation: challenger = side a
    (the µ leader), incumbent = side b (the runner-up).

    Args:
        bv: Band values for (leader, runner_up).
        usable: The :func:`_lambda_usable` outcome.

    Returns:
        Branch in {"mu-clear", "mu-primary-degraded", "lambda-tiebreak",
        "mu-leader-tie-held"} — emitted from the audit trail. The CALLER maps
        the branch to the winning record (lambda-tiebreak → runner-up,
        everything else → leader; legacy semantics).
    """

    def _mu(a: str, b: str) -> Verdict:
        if abs(bv.delta_mu) > bv.band_mu:
            return Verdict.A_WINS if bv.delta_mu > 0 else Verdict.B_WINS
        return Verdict.TIE

    def _lam(a: str, b: str) -> Verdict:
        if -bv.delta_lambda_x > bv.band_lambda_x:
            return Verdict.A_WINS
        if bv.delta_lambda_x > bv.band_lambda_x:
            return Verdict.B_WINS
        return Verdict.TIE

    criteria: list[Criterion[str]] = [Criterion("mu", _mu, banded=True)]
    if usable:
        criteria.append(Criterion("lambda_x", _lam, banded=True))
    policy: LexicographicPolicy[str] = LexicographicPolicy(tuple(criteria))
    _winner, audits = policy.winner(["runner_up", "leader"])
    last = audits[0][-1]
    if last.criterion == "mu" and last.verdict != "TIE":
        return "mu-clear"
    if not usable:
        return "mu-primary-degraded"
    if last.criterion == "lambda_x" and last.verdict == "B_WINS":
        return "lambda-tiebreak"
    return "mu-leader-tie-held"


def _adjudication_block(
    bv: BandValues, branch: str, note: str | None, written_utc: str
) -> dict[str, Any]:
    """Return the evidence-ready adjudication block.

    Single-execution rule: the computed values + write-time land in the
    CONSUMING record, never back into the protocol artifact.
    """
    return {
        "delta_mu": bv.delta_mu,
        "band_mu": bv.band_mu,
        "delta_lambda_x": bv.delta_lambda_x,
        "band_lambda_x": bv.band_lambda_x,
        "lambda_informative": bv.lambda_informative,
        "n_segments": bv.n_segments,
        "n_lambda_used": bv.n_lambda_used,
        "branch": branch,
        "note": note,
        "protocol_sha": bv.protocol_sha,
        "written_utc": written_utc,
    }


def _now_utc(now_utc: str | None) -> str:
    """Return ``now_utc`` if given, else the current UTC time (ISO 8601)."""
    if now_utc is not None:
        return now_utc
    from datetime import UTC  # noqa: PLC0415

    return datetime.now(UTC).isoformat()


def select_lane_winner(
    records: list[dict[str, Any]],
    protocol: BandProtocol,
    load_track: Callable[[dict[str, Any]], Mapping[str, np.ndarray]],
    lambda_x_fn: Callable[..., float] = effective_resolution_lambda_x,
    now_utc: str | None = None,
) -> dict[str, Any]:
    """Select one lane's winner: lexicographic µ → λx over bar-passing records.

    The refusal clock runs FIRST. Records are ranked by ``mu_score``; the
    within-lane top-2 adjudication band is computed AT READ TIME on that
    pair via :func:`compute_bands` (single seeded execution; values +
    write-time + protocol_sha land in the returned winner record). λx LOWER
    is finer/better. Degradation branches per :func:`_lambda_usable`.

    Args:
        records: The lane's trial records (each with ``created_utc``,
            ``scores`` and ``admissible``).
        protocol: The sealed band protocol.
        load_track: Maps a record to its persisted validation-track arrays.
        lambda_x_fn: The λx estimator (injectable for tests).
        now_utc: Override for the adjudication write-time (tests).

    Returns:
        A COPY of the winning record with an ``"adjudication"`` block.

    Raises:
        PreRegistrationError: If the protocol does not predate every record.
        ValueError: If no record is admissible.
    """
    assert_band_predates(protocol, records)  # refusal clock FIRST
    ok = [r for r in records if r.get("admissible")]
    if not ok:
        raise ValueError("no bar-passing records — no lane winner")
    ranked = sorted(ok, key=lambda r: float(r["scores"]["mu_score"]), reverse=True)
    leader = ranked[0]
    if len(ranked) == 1:
        return {
            **leader,
            "adjudication": {
                "branch": "single-admissible",
                "note": "only one bar-passing record; no pair to adjudicate",
                "protocol_sha": protocol.protocol_sha,
                "written_utc": _now_utc(now_utc),
            },
        }
    runner_up = ranked[1]
    bv = compute_bands(load_track(leader), load_track(runner_up), protocol, lambda_x_fn)
    usable, note = _lambda_usable(bv, protocol)
    written = _now_utc(now_utc)
    # Branch selection through the Policy seam (Phase-11): criteria close
    # over the ONE BandValues computed above; λ degradation = dropping the
    # criterion. Record mapping stays HERE (legacy semantics): the runner-up
    # displaces the leader only on lambda-tiebreak.
    branch = adjudicate_lane_pair(bv, usable)
    record = runner_up if branch == "lambda-tiebreak" else leader
    return {
        **record,
        "adjudication": _adjudication_block(
            bv, branch, note if branch == "mu-primary-degraded" else None, written
        ),
    }


def primary_verdict(
    w_a: dict[str, Any],
    w_lane0: dict[str, Any],
    protocol: BandProtocol,
    load_track: Callable[[dict[str, Any]], Mapping[str, np.ndarray]],
    lambda_x_fn: Callable[..., float] = effective_resolution_lambda_x,
    now_utc: str | None = None,
) -> dict[str, Any]:
    """Return the comparison verdict for a lat lane's winner vs lane-0's.

    The spec-§5 lexicographic rule: BEATS iff Δµ > band_µ; if |Δµ| ≤ band_µ,
    then Δλx-improvement > band_λx breaks the tie (finer resolution wins —
    the L(lat) physics signature); both within bands → tie, counted toward
    the negative result. Wording pin (batch-2 fold 1): a non-positive
    outcome reads "improvements within band", never "worse".

    Args:
        w_a: The lat lane's winner record (side a).
        w_lane0: The lane-0 winner record (side b).
        protocol: The sealed band protocol.
        load_track: Maps a record to its persisted validation-track arrays.
        lambda_x_fn: The λx estimator (injectable for tests).
        now_utc: Override for the verdict write-time (tests).

    Returns:
        The evidence-ready verdict block (bands + branch + wording +
        protocol_sha + write-time).
    """
    assert_band_predates(protocol, [w_a, w_lane0])  # refusal clock FIRST
    bv = compute_bands(load_track(w_a), load_track(w_lane0), protocol, lambda_x_fn)
    usable, note = _lambda_usable(bv, protocol)
    # Branch + wording through the Policy seam (Phase-11): bands stay
    # read-time DATA; the seam only compares (gate ii replays this exact
    # adjudication from persisted verdict fields).
    branch, positive = adjudicate_primary(bv, usable)
    wording = primary_wording(str(w_a.get("lane", "lat-varying")), positive, branch)
    return {
        "rule": "lexicographic mu->lambda_x (spec §5)",
        "a_lane": w_a.get("lane"),
        "b_lane": w_lane0.get("lane"),
        "positive": positive,
        "branch": branch,
        "wording": wording,
        "note": note,
        "delta_mu": bv.delta_mu,
        "band_mu": bv.band_mu,
        "delta_lambda_x": bv.delta_lambda_x,
        "band_lambda_x": bv.band_lambda_x,
        "lambda_informative": bv.lambda_informative,
        "n_segments": bv.n_segments,
        "n_lambda_used": bv.n_lambda_used,
        "protocol_sha": bv.protocol_sha,
        "written_utc": _now_utc(now_utc),
    }


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
