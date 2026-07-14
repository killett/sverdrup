"""Band PROTOCOL machinery (Phase-10 Task 5; spec §5/§9 + owner correction 1).

Bugs caught per test: unseeded/global-state resampling (determinism);
resample_seed ignored (false determinism across protocols); a band quoted
against an edited protocol (sha binding / tamper); post-hoc protocol
sealing (refusal clock, both orders); schema drift between the sealed
artifact and the loaded object; bands computed on score LEVELS instead of
paired differences (identical-products zero-band); comparing different
consulted tracks (paired-track assert); the λ-informative rule inverted.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sverdrup.application.tuning.lane_compare import (
    BandProtocol,
    BandValues,
    PreRegistrationError,
    assert_band_predates,
    compute_bands,
    load_protocol,
    seal_protocol,
)


def _seal(
    tmp_path: Path, created: str = "2026-07-13T20:00:00+00:00"
) -> tuple[Path, str]:
    p = tmp_path / "phase10_band_artifact.json"
    sha = seal_protocol(p, created_utc=created)
    return p, sha


def _pair(
    seed_b: int = 2, shift: float = 0.0, n: int = 600
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """One consulted track, two products: sides share time/lat/lon/ssh.

    Side a's residuals come from seed 1, side b's from ``seed_b`` plus a
    constant ``shift`` (a real skill difference the bands should straddle).
    """
    day = np.repeat(np.arange(20, dtype=float), 30)  # 20 one-day passes
    within = np.tile(np.arange(30, dtype=float) * (1.2 / 86400.0), 20)
    time = day + within
    lat = np.tile(np.linspace(33.5, 42.5, 30), 20)
    lon = np.full(n, 300.0)
    ssh = np.sin(lat) + 0.05 * np.random.default_rng(0).standard_normal(n)
    base = {"time": time, "lat": lat, "lon": lon, "ssh": ssh}
    a = dict(base, mean_interp=ssh - 0.02 * np.random.default_rng(1).standard_normal(n))
    b = dict(
        base,
        mean_interp=ssh
        - (0.02 * np.random.default_rng(seed_b).standard_normal(n) + shift),
    )
    return a, b


def _cheap_lambda(
    time: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    ssh: np.ndarray,
    interp: np.ndarray,
) -> float:
    # Deterministic stand-in for the spectral estimator: scale of the
    # residual RMS (so different resamples give different values).
    return 100.0 + 1000.0 * float(np.sqrt(np.mean((ssh - interp) ** 2)))


def test_schema_round_trip(tmp_path: Path) -> None:
    p, sha = _seal(tmp_path)
    proto = load_protocol(p, expected_sha=sha)
    assert isinstance(proto, BandProtocol)
    assert proto.resample_seed == 271828
    assert proto.n_resamples == 2000
    assert proto.block_unit == "contiguous day/pass segments"
    assert proto.created_utc == "2026-07-13T20:00:00+00:00"
    assert proto.protocol_sha == sha


def test_tampered_protocol_refused(tmp_path: Path) -> None:
    p, sha = _seal(tmp_path)
    raw = p.read_text().replace("271828", "271829")
    p.write_text(raw)
    with pytest.raises(PreRegistrationError, match="sha"):
        load_protocol(p, expected_sha=sha)


def _small_proto(tmp_path: Path, seed: int = 271828, n_res: int = 64) -> BandProtocol:
    p = tmp_path / f"proto_{seed}_{n_res}.json"
    seal_protocol(p, created_utc="2026-07-13T20:00:00+00:00")
    proto = load_protocol(p)
    # Shrink the resample counts for test speed (frozen dataclass -> replace).
    from dataclasses import replace

    return replace(proto, resample_seed=seed, n_resamples=n_res, n_lambda_resamples=16)


def test_compute_bands_deterministic_under_protocol(tmp_path: Path) -> None:
    proto = _small_proto(tmp_path)
    a, b = _pair(shift=0.005)
    r1 = compute_bands(a, b, proto, lambda_x_fn=_cheap_lambda)
    r2 = compute_bands(a, b, proto, lambda_x_fn=_cheap_lambda)
    assert r1 == r2


def test_different_seed_different_draws(tmp_path: Path) -> None:
    a, b = _pair(shift=0.005)
    r1 = compute_bands(
        a, b, _small_proto(tmp_path, seed=271828), lambda_x_fn=_cheap_lambda
    )
    r2 = compute_bands(a, b, _small_proto(tmp_path, seed=99), lambda_x_fn=_cheap_lambda)
    assert r1.band_mu != r2.band_mu


def test_identical_products_zero_band(tmp_path: Path) -> None:
    # Paired differences of a product against ITSELF are identically zero in
    # every resample -> band_mu == 0. A band computed on levels would be > 0.
    proto = _small_proto(tmp_path)
    a, _ = _pair()
    r = compute_bands(a, a, proto, lambda_x_fn=_cheap_lambda)
    assert r.band_mu == 0.0
    assert r.delta_mu == 0.0


def test_mismatched_tracks_rejected(tmp_path: Path) -> None:
    proto = _small_proto(tmp_path)
    a, b = _pair()
    b = dict(b)
    b["lat"] = b["lat"] + 0.1  # not the same consulted track
    with pytest.raises(ValueError, match="track"):
        compute_bands(a, b, proto, lambda_x_fn=_cheap_lambda)


def test_lambda_informative_rule(tmp_path: Path) -> None:
    proto = _small_proto(tmp_path)
    a, b = _pair(shift=0.005)

    calls = {"n": 0}

    def noisy_lambda(*args: Any) -> float:
        calls["n"] += 1
        return 100.0 + 40.0 * (calls["n"] % 7)  # spread >> 25 km rule

    r = compute_bands(a, b, proto, lambda_x_fn=noisy_lambda)
    assert r.band_lambda_x > 25.0
    assert r.lambda_informative is False
    tight = compute_bands(a, b, proto, lambda_x_fn=lambda *args: 130.0)
    assert tight.band_lambda_x == 0.0
    assert tight.lambda_informative is True


def test_band_carries_protocol_sha(tmp_path: Path) -> None:
    p, sha = _seal(tmp_path)
    proto = load_protocol(p, expected_sha=sha)
    from dataclasses import replace

    proto = replace(proto, n_resamples=16, n_lambda_resamples=8)
    a, b = _pair(shift=0.005)
    r = compute_bands(a, b, proto, lambda_x_fn=_cheap_lambda)
    assert isinstance(r, BandValues)
    assert r.protocol_sha == sha


def test_assert_band_predates_accepts_earlier_protocol(tmp_path: Path) -> None:
    p, sha = _seal(tmp_path, created="2026-07-13T20:00:00+00:00")
    proto = load_protocol(p, expected_sha=sha)
    records = [{"created_utc": "2026-07-13T21:30:00+00:00"}]
    assert_band_predates(proto, records)  # no raise


def test_assert_band_predates_refuses_later_protocol(tmp_path: Path) -> None:
    p, sha = _seal(tmp_path, created="2026-07-13T22:00:00+00:00")
    proto = load_protocol(p, expected_sha=sha)
    records = [
        {"created_utc": "2026-07-13T23:00:00+00:00"},
        {"created_utc": "2026-07-13T21:30:00+00:00"},  # predates the protocol
    ]
    with pytest.raises(PreRegistrationError, match="predate"):
        assert_band_predates(proto, records)


def test_assert_band_predates_refuses_equal_timestamps(tmp_path: Path) -> None:
    # written == sealed is NOT "postdates" — a record stamped in the same
    # instant proves nothing about ordering; refuse.
    p, sha = _seal(tmp_path, created="2026-07-13T22:00:00+00:00")
    proto = load_protocol(p, expected_sha=sha)
    with pytest.raises(PreRegistrationError, match="predate"):
        assert_band_predates(proto, [{"created_utc": "2026-07-13T22:00:00+00:00"}])


# ---------------------------------------------------------------------------
# Selection layer (Task 6): lexicographic winner + PRIMARY verdict.
# Bugs caught: refusal clock skipped (post-hoc protocol accepted); λ
# tie-break firing on an uninformative/under-sampled band; sign flip in the
# λ rule (coarser resolution winning); the wording pin violated ("worse");
# adjudication block missing protocol_sha/write-time.
# ---------------------------------------------------------------------------

from sverdrup.application.tuning.lane_compare import (  # noqa: E402
    primary_verdict,
    select_lane_winner,
)

_NOW = "2026-07-13T23:00:00+00:00"


def _track_for(
    rid: int, *, rms: float = 0.02, offset: float = 0.0
) -> dict[str, np.ndarray]:
    """Product track keyed by ``rid``: same consulted track, own residuals."""
    day = np.repeat(np.arange(20, dtype=float), 30)
    within = np.tile(np.arange(30, dtype=float) * (1.2 / 86400.0), 20)
    lat = np.tile(np.linspace(33.5, 42.5, 30), 20)
    lon = np.full(600, 300.0)
    ssh = np.sin(lat) + 0.05 * np.random.default_rng(0).standard_normal(600)
    resid = rms * np.random.default_rng(100 + rid).standard_normal(600) + offset
    return {
        "time": day + within,
        "lat": lat,
        "lon": lon,
        "ssh": ssh,
        "mean_interp": ssh - resid,
    }


def _mirror(track: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Same track, residuals NEGATED: identical rms -> exact µ tie, zero band."""
    out = dict(track)
    out["mean_interp"] = 2.0 * track["ssh"] - track["mean_interp"]
    return out


def _tie_tracks() -> dict[int, dict[str, np.ndarray]]:
    a = _track_for(1, offset=+0.003)
    return {1: a, 2: _mirror(a)}


def _rec(rid: int, mu: float, lx: float, lane: str = "V") -> dict[str, Any]:
    return {
        "rid": rid,
        "created_utc": "2026-07-13T21:00:00+00:00",
        "lane": lane,
        "trial": {},
        "scores": {"mu_score": mu, "lambda_x": lx},
        "admissible": True,
    }


def _loader(tracks: dict[int, dict[str, np.ndarray]]) -> Any:
    return lambda rec: tracks[rec["rid"]]


def test_select_winner_mu_clear(tmp_path: Path) -> None:
    proto = _small_proto(tmp_path)
    tracks = {1: _track_for(1, rms=0.005), 2: _track_for(2, rms=0.03)}
    recs = [_rec(1, 0.92, 140.0), _rec(2, 0.86, 120.0)]
    w = select_lane_winner(
        recs, proto, _loader(tracks), lambda_x_fn=_cheap_lambda, now_utc=_NOW
    )
    assert w["rid"] == 1  # µ decides; runner-up's better λx never consulted
    adj = w["adjudication"]
    assert adj["branch"] == "mu-clear"
    assert adj["protocol_sha"] == proto.protocol_sha
    assert adj["written_utc"] == _NOW
    assert adj["delta_mu"] > adj["band_mu"]


def test_select_winner_mu_tie_lambda_flips(tmp_path: Path) -> None:
    # Same residual RMS both sides (µ tie within band); side markers via the
    # residual-mean sign drive a deterministic per-side λ: runner-up resolves
    # FINER (lower λx) beyond a zero-width band -> tie-break flips to it.
    proto = _small_proto(tmp_path)
    tracks = _tie_tracks()
    recs = [_rec(1, 0.880001, 150.0), _rec(2, 0.880000, 120.0)]

    def side_lambda(time: Any, lat: Any, lon: Any, ssh: Any, interp: Any) -> float:
        return 150.0 if float(np.mean(ssh - interp)) > 0 else 120.0

    w = select_lane_winner(
        recs, proto, _loader(tracks), lambda_x_fn=side_lambda, now_utc=_NOW
    )
    assert w["rid"] == 2
    assert w["adjudication"]["branch"] == "lambda-tiebreak"


def test_select_winner_degrades_to_mu_primary_on_wide_band(tmp_path: Path) -> None:
    proto = _small_proto(tmp_path)
    tracks = _tie_tracks()
    recs = [_rec(1, 0.880001, 150.0), _rec(2, 0.880000, 120.0)]

    calls = {"n": 0}

    def noisy_lambda(*args: Any) -> float:
        calls["n"] += 1
        return 100.0 + 40.0 * (calls["n"] % 7)  # band >> 25 km

    w = select_lane_winner(
        recs, proto, _loader(tracks), lambda_x_fn=noisy_lambda, now_utc=_NOW
    )
    assert w["rid"] == 1  # µ leader stays
    adj = w["adjudication"]
    assert adj["branch"] == "mu-primary-degraded"
    assert "uninformative" in adj["note"]


def test_select_winner_degrades_when_lambda_undersampled(tmp_path: Path) -> None:
    from sverdrup.eval.spectral import UnresolvedScaleError

    proto = _small_proto(tmp_path)
    tracks = _tie_tracks()
    recs = [_rec(1, 0.880001, 150.0), _rec(2, 0.880000, 120.0)]

    calls = {"n": 0}

    def failing_lambda(*args: Any) -> float:
        # Full-track point estimates (first two calls) succeed; every
        # RESAMPLE fails -> the band is under-sampled, not point-failed.
        calls["n"] += 1
        if calls["n"] <= 2:
            return 140.0
        raise UnresolvedScaleError("no crossing")

    w = select_lane_winner(
        recs, proto, _loader(tracks), lambda_x_fn=failing_lambda, now_utc=_NOW
    )
    assert w["rid"] == 1
    assert "under-sampled" in w["adjudication"]["note"]


def test_select_winner_refusal_clock_first(tmp_path: Path) -> None:
    p, sha = _seal(tmp_path, created="2026-07-13T22:00:00+00:00")
    proto = load_protocol(p, expected_sha=sha)
    recs = [_rec(1, 0.92, 140.0), _rec(2, 0.86, 120.0)]  # written 21:00 < sealed
    with pytest.raises(PreRegistrationError, match="predate"):
        select_lane_winner(recs, proto, _loader({}), lambda_x_fn=_cheap_lambda)


def test_primary_verdict_positive_mu(tmp_path: Path) -> None:
    proto = _small_proto(tmp_path)
    tracks = {1: _track_for(1, rms=0.005), 2: _track_for(2, rms=0.03)}
    v = primary_verdict(
        _rec(1, 0.92, 140.0, lane="VL"),
        _rec(2, 0.86, 120.0, lane="lane0"),
        proto,
        _loader(tracks),
        lambda_x_fn=_cheap_lambda,
        now_utc=_NOW,
    )
    assert v["positive"] is True and v["branch"] == "beats-mu"
    assert v["protocol_sha"] == proto.protocol_sha


def test_primary_verdict_lambda_win_at_flat_mu(tmp_path: Path) -> None:
    proto = _small_proto(tmp_path)
    tracks = _tie_tracks()

    def side_lambda(time: Any, lat: Any, lon: Any, ssh: Any, interp: Any) -> float:
        # VL (side a, positive marker) resolves FINER: lower λx.
        return 120.0 if float(np.mean(ssh - interp)) > 0 else 150.0

    v = primary_verdict(
        _rec(1, 0.880001, 120.0, lane="VL"),
        _rec(2, 0.880000, 150.0, lane="lane0"),
        proto,
        _loader(tracks),
        lambda_x_fn=side_lambda,
        now_utc=_NOW,
    )
    assert v["positive"] is True and v["branch"] == "beats-lambda-at-flat-mu"


def test_primary_verdict_within_band_wording_pin(tmp_path: Path) -> None:
    proto = _small_proto(tmp_path)
    tracks = _tie_tracks()
    v = primary_verdict(
        _rec(1, 0.880001, 140.0, lane="VL"),
        _rec(2, 0.880000, 140.0, lane="lane0"),
        proto,
        _loader(tracks),
        lambda_x_fn=lambda *a: 140.0,
        now_utc=_NOW,
    )
    assert v["positive"] is False and v["branch"] == "within-band"
    assert "improvements within band" in v["wording"]
    assert "worse" not in v["wording"].lower()


def test_assert_band_predates_refuses_naive_timestamps(tmp_path: Path) -> None:
    # A tz-naive record timestamp makes the clock ambiguous -> refuse loudly
    # (bug caught: silent TypeError killing the refusal clock mid-comparison).
    p, sha = _seal(tmp_path, created="2026-07-13T20:00:00+00:00")
    proto = load_protocol(p, expected_sha=sha)
    with pytest.raises(PreRegistrationError, match="timezone"):
        assert_band_predates(proto, [{"created_utc": "2026-07-13T21:00:00"}])
