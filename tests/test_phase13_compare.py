"""Tests for the phase-13 comparison read (plan Task 9).

Each test names the bug it catches; expected values hand-derived from the
sealed protocol semantics, never from the implementation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from sverdrup.application.tuning.lane_compare import (
    BandProtocol,
    BandValues,
    PreRegistrationError,
)
from tests.helpers import load_script

_SEAL = "2026-07-19T16:03:06+00:00"
_POST = "2026-07-20T01:00:00+00:00"
_PRE = "2026-07-19T12:00:00+00:00"


def _protocol() -> BandProtocol:
    return BandProtocol(
        created_utc=_SEAL,
        resample_seed=1,
        block_unit="contiguous day/pass segments",
        n_resamples=8,
        n_lambda_resamples=4,
        machinery="test",
        lambda_informative_rule="band_lambda_x <= 25 km",
        single_execution_rule="one seeded computation per consulted pair",
        protocol_sha="deadbeef",
    )


def _winner(lane: str, mu: float, lx: float, created: str = _POST) -> dict[str, Any]:
    return {
        "lane": lane,
        "index": 1,
        "created_utc": created,
        "scores": {"mu_score": mu, "lambda_x": lx},
        "residuals_npz": f"unused_{lane}.npz",
        "admissible": True,
    }


def _lane0() -> dict[str, Any]:
    return {
        "lane": "lane0",
        "scores": {"mu_score": 0.8642, "lambda_x": 178.0},
        "residuals_npz": "unused_lane0.npz",
    }


def _bv(
    dmu: float,
    dlx: float,
    band_mu: float = 0.001,
    band_lx: float = 5.0,
) -> BandValues:
    # n_lambda_used=4 of 4 sealed and band_lx<=25: the lambda tie-break is
    # USABLE unless a test narrows it deliberately.
    return BandValues(
        delta_mu=dmu,
        delta_lambda_x=dlx,
        band_mu=band_mu,
        band_lambda_x=band_lx,
        lambda_informative=band_lx <= 25.0,
        n_segments=8,
        n_lambda_used=4,
        protocol_sha="deadbeef",
    )


def _track_tagger(rec: dict[str, Any]) -> dict[str, Any]:
    """Test loader: tags the 'track' with its lane so bands_fn can dispatch."""
    return {"lane": rec["lane"]}


def _bands_table(
    table: dict[tuple[str, str], BandValues],
) -> Any:
    def bands_fn(
        ta: dict[str, Any], tb: dict[str, Any], *a: Any, **k: Any
    ) -> BandValues:
        return table[(ta["lane"], tb["lane"])]

    return bands_fn


def _winners(
    c_mu: float = 0.8656, d_mu: float = 0.8655, m_mu: float = 0.8657
) -> dict[str, dict[str, Any]]:
    return {
        "D": _winner("D", d_mu, 174.5),
        "C": _winner("C", c_mu, 174.2),
        "modes-only": _winner("modes-only", m_mu, 174.2),
    }


def test_refusal_clock_first_and_refuses_pre_seal_winner() -> None:
    # Refusal clock FIRST (plan AC 1): a winner record whose created_utc
    # does not postdate the seal refuses BEFORE any track is loaded or any
    # seeded band is computed.
    # Bug caught: clock evaluated after (or during) the band computation —
    # a post-hoc protocol proves nothing, and a seeded execution would be
    # spent before the refusal (unrecoverable under the single-execution
    # rule).
    compare = load_script("phase13_compare")
    winners = _winners()
    winners["C"] = _winner("C", 0.8656, 174.2, created=_PRE)

    def exploding_loader(rec: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("track loaded before the refusal clock ran")

    with pytest.raises(PreRegistrationError, match="postdate"):
        compare.assemble_verdict(
            winners,
            _lane0(),
            _protocol(),
            load_track=exploding_loader,
            bands_fn=_bands_table({}),
        )


def test_lane0_integrity_refuses_sha_mismatch(tmp_path: Path) -> None:
    # lane-0 is the CO-SEALED reference (no post-seal record to clock):
    # its integrity check recomputes sha256 of the residuals npz bytes and
    # refuses on mismatch with the sealed residuals_sha256.
    # Bug caught: silently computing the claim-bearing verdict against a
    # clobbered/regenerated lane-0 array (the Stage-B evidence-clobber
    # failure class, hygiene P0-2).
    compare = load_script("phase13_compare")
    npz = tmp_path / "lane0.npz"
    np.savez(npz, time=np.arange(3.0))
    artifact = {
        "lane0_reference": {
            "residuals_npz": str(npz),
            "residuals_sha256": "0" * 64,  # deliberately wrong
            "mu_score": 0.8642,
        }
    }
    with pytest.raises(SystemExit, match="sha"):
        compare.lane0_record(artifact)


def test_lane0_record_carries_sealed_reference(tmp_path: Path) -> None:
    # On a sha MATCH the lane-0 side is built verbatim from the sealed
    # reference block (npz path + mu).
    # Bug caught: hand-typed lane-0 numbers drifting from the sealed
    # artifact (the five-file-MDT 4e-6 class of silent divergence).
    compare = load_script("phase13_compare")
    npz = tmp_path / "lane0.npz"
    np.savez(npz, time=np.arange(3.0))
    sha = hashlib.sha256(npz.read_bytes()).hexdigest()
    artifact = {
        "lane0_reference": {
            "residuals_npz": str(npz),
            "residuals_sha256": sha,
            "mu_score": 0.8642,
        }
    }
    rec = compare.lane0_record(artifact)
    assert rec["lane"] == "lane0"
    assert rec["residuals_npz"] == str(npz)
    assert rec["scores"]["mu_score"] == 0.8642


def test_wording_pin_positive_mu() -> None:
    # Pinned wording (plan AC 2): a positive primary reads
    # "C beats lane-0 beyond the measured band (beats-mu)" string-equal.
    # Bug caught: wording drift (breaks the gate-ii style replay from
    # persisted fields) or the wrong lane label in the claim.
    compare = load_script("phase13_compare")
    table = {
        ("C", "lane0"): _bv(dmu=+0.005, dlx=-3.8),  # beyond 0.001 band
        ("D", "lane0"): _bv(dmu=+0.0002, dlx=-3.5),
        ("modes-only", "lane0"): _bv(dmu=+0.0003, dlx=-3.8),
        ("C", "D"): _bv(dmu=+0.0001, dlx=-0.3),
    }
    v = compare.assemble_verdict(
        _winners(),
        _lane0(),
        _protocol(),
        load_track=_track_tagger,
        bands_fn=_bands_table(table),
    )
    assert v["primary"]["positive"] is True
    assert v["primary"]["branch"] == "beats-mu"
    assert v["primary"]["wording"] == (
        "C beats lane-0 beyond the measured band (beats-mu)"
    )


def test_wording_pin_negative_within_band() -> None:
    # Pinned wording: a non-positive primary reads EXACTLY
    # "improvements within band" — never "worse".
    # Bug caught: the negative path acquiring pejorative or novel wording
    # (the §7 pre-registered negative wording is part of the seal).
    compare = load_script("phase13_compare")
    table = {
        ("C", "lane0"): _bv(dmu=+0.0005, dlx=-1.0),  # inside 0.001 band
        ("D", "lane0"): _bv(dmu=+0.0004, dlx=-1.0),
        ("modes-only", "lane0"): _bv(dmu=+0.0004, dlx=-1.0),
        ("C", "D"): _bv(dmu=+0.0001, dlx=-0.1),
    }
    v = compare.assemble_verdict(
        _winners(),
        _lane0(),
        _protocol(),
        load_track=_track_tagger,
        bands_fn=_bands_table(table),
    )
    assert v["primary"]["positive"] is False
    assert v["primary"]["wording"] == "improvements within band"
    assert v["branch_recorded"].startswith("NEGATIVE")
    assert "Task 10" in v["branch_recorded"]
    assert v["winner_lane_rule"]["chain_lane"] is None


def test_winner_lane_rule_tie_gives_the_simpler_lane_d() -> None:
    # Winner-lane rule (spec §10 owner pin, plan AC 3): PRIMARY positive
    # but C-vs-D within band -> lane-D takes the acceptance chain.
    # Bug caught: the chain defaulting to the claim lane C on an
    # indistinguishable pair — the exact outcome the owner pin forbids
    # (unbought machinery costs conditioning forever).
    compare = load_script("phase13_compare")
    table = {
        ("C", "lane0"): _bv(dmu=+0.005, dlx=-3.8),
        ("D", "lane0"): _bv(dmu=+0.004, dlx=-3.5),
        ("modes-only", "lane0"): _bv(dmu=+0.004, dlx=-3.8),
        ("C", "D"): _bv(dmu=+0.0001, dlx=-0.3),  # within band
    }
    v = compare.assemble_verdict(
        _winners(),
        _lane0(),
        _protocol(),
        load_track=_track_tagger,
        bands_fn=_bands_table(table),
    )
    assert v["primary"]["positive"] is True
    assert v["winner_lane_rule"]["chain_lane"] == "D"
    assert v["branch_recorded"].startswith("WINNER")
    assert "lane D" in v["branch_recorded"]
    assert "Tasks 11-14" in v["branch_recorded"]


def test_winner_lane_rule_c_clear_keeps_c() -> None:
    # C beats D beyond band -> lane-C keeps the chain.
    # Bug caught: the rule unconditionally handing D the chain (reading
    # "simpler lane on tie" as "simpler lane always").
    compare = load_script("phase13_compare")
    table = {
        ("C", "lane0"): _bv(dmu=+0.005, dlx=-3.8),
        ("D", "lane0"): _bv(dmu=+0.001, dlx=-1.0),
        ("modes-only", "lane0"): _bv(dmu=+0.001, dlx=-1.0),
        ("C", "D"): _bv(dmu=+0.004, dlx=-0.3),  # beyond 0.001 band
    }
    v = compare.assemble_verdict(
        _winners(),
        _lane0(),
        _protocol(),
        load_track=_track_tagger,
        bands_fn=_bands_table(table),
    )
    assert v["winner_lane_rule"]["chain_lane"] == "C"
    assert "lane C" in v["branch_recorded"]


def test_winner_lane_pair_row_carries_no_lane0_wording() -> None:
    # The pinned primary_wording strings hardcode "beats lane-0"; the
    # C-vs-D bookkeeping pair is NOT a lane-0 comparison, so its row must
    # carry no wording (branch + roles carry the semantics).
    # Bug caught: the write-once record stating "C beats lane-0 beyond the
    # measured band" for a pair whose side b is lane D (spec-review
    # finding, dual review 2026-07-20).
    compare = load_script("phase13_compare")
    table = {
        ("C", "lane0"): _bv(dmu=+0.005, dlx=-3.8),
        ("D", "lane0"): _bv(dmu=+0.001, dlx=-1.0),
        ("modes-only", "lane0"): _bv(dmu=+0.001, dlx=-1.0),
        ("C", "D"): _bv(dmu=+0.004, dlx=-0.3),  # C beats D beyond band
    }
    v = compare.assemble_verdict(
        _winners(),
        _lane0(),
        _protocol(),
        load_track=_track_tagger,
        bands_fn=_bands_table(table),
    )
    assert v["winner_lane_rule"]["pair"]["wording"] is None
    assert v["primary"]["wording"] is not None


def test_secondary_rows_designated_never_claim_bearing() -> None:
    # The sealed designations: D-vs-0 and modes-only-vs-0 rows carry the
    # never-claim-bearing designation verbatim; modes-only NEVER ships.
    # Bug caught: a secondary row silently promoted to claim-bearing in
    # the pack (the designation strings are part of the sealed artifact).
    compare = load_script("phase13_compare")
    table = {
        ("C", "lane0"): _bv(dmu=+0.0005, dlx=-1.0),
        ("D", "lane0"): _bv(dmu=+0.0004, dlx=-1.0),
        ("modes-only", "lane0"): _bv(dmu=+0.0004, dlx=-1.0),
        ("C", "D"): _bv(dmu=+0.0001, dlx=-0.1),
    }
    v = compare.assemble_verdict(
        _winners(),
        _lane0(),
        _protocol(),
        load_track=_track_tagger,
        bands_fn=_bands_table(table),
    )
    assert "never claim-bearing" in v["secondary_d_vs_lane0"]["role"]
    assert "never claim-bearing" in v["secondary_modes_only_vs_lane0"]["role"]
    assert "PRIMARY" in v["primary"]["role"]


def test_main_end_to_end_writes_verdict_on_synthetic_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Full main() happy path against a synthetic evidence store + sealed
    # artifact + real compute_bands on a tiny synthetic track: the verdict
    # block lands at phase13.miost.lanes.verdict and round-trips json.
    # Bug caught: a serialization or key error AFTER the seeded band
    # computations (adversarial-review blind spot (a)) — the write-once
    # ceremony would abort with 100% of the execution spent and nothing
    # recorded.
    compare = load_script("phase13_compare")
    rng = np.random.default_rng(7)
    n = 48
    time = np.datetime64("2021-01-01") + (
        np.arange(n) * np.timedelta64(90, "m")
    ).astype("timedelta64[ns]")
    ssh = rng.normal(size=n)
    lat = np.linspace(35.0, 41.0, n)
    lon = np.linspace(295.0, 305.0, n)

    def _npz(name: str, shift: float) -> str:
        p = tmp_path / name
        np.savez(p, time=time, lat=lat, lon=lon, ssh=ssh, mean_interp=ssh * 0.5 + shift)
        return str(p)

    lane0_npz = _npz("lane0.npz", 0.0)
    artifact = {
        "created_utc": _SEAL,
        "resample_seed": 3,
        "block_unit": "contiguous day/pass segments",
        "n_resamples": 8,
        "n_lambda_resamples": 4,
        "machinery": "test",
        "lambda_informative_rule": "band_lambda_x <= 25 km",
        "single_execution_rule": "one seeded computation per consulted pair",
        "lane0_reference": {
            "residuals_npz": lane0_npz,
            "residuals_sha256": hashlib.sha256(
                Path(lane0_npz).read_bytes()
            ).hexdigest(),
            "mu_score": 0.8642,
        },
    }
    art_path = tmp_path / "artifact.json"
    art_path.write_text(json.dumps(artifact))
    art_sha = hashlib.sha256(art_path.read_bytes()).hexdigest()

    winners = {
        lane: {
            **_winner(lane, 0.86, 174.0),
            "residuals_npz": _npz(f"{lane}.npz", 0.01 * (i + 1)),
        }
        for i, lane in enumerate(("D", "C", "modes-only"))
    }
    results = tmp_path / "results.json"
    results.write_text(
        json.dumps(
            {
                "phase13": {
                    "band_protocol": {"path": str(art_path), "sha256": art_sha},
                    "miost": {"lanes": {k: {"winner": w} for k, w in winners.items()}},
                }
            }
        )
    )
    monkeypatch.setattr(compare, "_RESULTS", results)
    compare.main()
    verdict = json.loads(results.read_text())["phase13"]["miost"]["lanes"]["verdict"]
    assert verdict["protocol_sha"] == art_sha
    assert verdict["branch_recorded"].startswith(("WINNER", "NEGATIVE"))
    assert verdict["primary"]["a_lane"] == "C"
    assert verdict["lane0_integrity"]["match"] is True


def test_single_execution_guard_refuses_a_second_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Single-execution rule + pre-registered misfire protocol (owner,
    # 2026-07-20): an existing verdict refuses the run — a corrected read
    # happens only through owner adjudication under a dated defect key,
    # never a silent re-execution.
    # Bug caught: main() silently overwriting the claim-bearing read.
    compare = load_script("phase13_compare")
    results = tmp_path / "results.json"
    results.write_text(
        json.dumps({"phase13": {"miost": {"lanes": {"verdict": {"branch": "x"}}}}})
    )
    monkeypatch.setattr(compare, "_RESULTS", results)
    with pytest.raises(SystemExit, match="defect key"):
        compare.main()
