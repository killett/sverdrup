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


def test_assert_band_predates_refuses_naive_timestamps(tmp_path: Path) -> None:
    # A tz-naive record timestamp makes the clock ambiguous -> refuse loudly
    # (bug caught: silent TypeError killing the refusal clock mid-comparison).
    p, sha = _seal(tmp_path, created="2026-07-13T20:00:00+00:00")
    proto = load_protocol(p, expected_sha=sha)
    with pytest.raises(PreRegistrationError, match="timezone"):
        assert_band_predates(proto, [{"created_utc": "2026-07-13T21:00:00"}])
