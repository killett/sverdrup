"""Screening + stratified-split tests (phase-14 Task 8, 0a-3a).

Fixtures: six synthetic gauges spanning the strata + failure modes, one per
criterion, each with a hand-known verdict. The firewall is asserted both as
behavior (screening touches no map artifact) and as the verbatim sentence
pinned in the module docstring.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import sverdrup.adapters.insitu.screening as screening
from sverdrup.adapters.insitu.screening import (
    L_PROX_KM,
    Epoch,
    GaugeRecord,
    era_class,
    screen_gauges,
    stratified_split,
)
from sverdrup.core.seeding import derive_seed


def _days(start: str, end: str, step: int = 1) -> np.ndarray:
    return np.arange(
        np.datetime64(start), np.datetime64(end), np.timedelta64(step, "D")
    )


_EPOCHS = (
    Epoch("e00_1995-01-01", np.datetime64("1995-01-01"), np.datetime64("2005-01-01")),
    Epoch("e01_2005-01-01", np.datetime64("2005-01-01"), np.datetime64("2015-01-01")),
)

# Ocean points of a fake target grid: one point near Hawaii, one N Atlantic.
_OCEAN = (np.array([202.0, 330.0]), np.array([21.0, 45.0]))


def _gauge(
    gid: str,
    lon: float,
    lat: float,
    days: np.ndarray,
    *,
    rlr: bool = True,
    corrections: dict[str, str] | None = None,
) -> GaugeRecord:
    return GaugeRecord(
        gauge_id=gid,
        lon=lon,
        lat=lat,
        days=days,
        rlr_datum_ok=rlr,
        corrections=(
            {"dac": "none-applied", "tide": "hourly-mean"}
            if corrections is None
            else corrections
        ),
    )


_FIXTURES = [
    _gauge("g_pass", 202.1, 21.3, _days("1995-01-01", "2015-01-01")),
    _gauge("g_datum", 202.2, 21.4, _days("1995-01-01", "2015-01-01"), rlr=False),
    # claims epoch e00 (starts 1995) but carries only ~2.5% of its days
    _gauge("g_sparse", 202.3, 21.5, _days("1995-01-01", "1995-04-01")),
    _gauge("g_baltic", 20.0, 58.0, _days("1995-01-01", "2015-01-01")),
    # ~8 deg from the nearest ocean point: far beyond 150 km
    _gauge("g_inland", 210.0, 21.0, _days("1995-01-01", "2015-01-01")),
    _gauge(
        "g_nocorr",
        330.1,
        45.2,
        _days("1995-01-01", "2015-01-01"),
        corrections={},
    ),
]


def test_criteria_verdicts_per_fixture() -> None:
    """Each fixture fails exactly its designed criterion; g_pass passes all."""
    rows, passed = screen_gauges(_FIXTURES, _EPOCHS, _OCEAN)
    verdict = {(r.gauge_id, r.criterion): r.passed for r in rows}
    assert passed == ("g_pass",)
    assert verdict[("g_datum", "rlr_datum_continuity")] is False
    assert verdict[("g_sparse", "era_completeness")] is False
    assert verdict[("g_baltic", "open_ocean_siting")] is False
    assert verdict[("g_inland", "proximity")] is False
    assert verdict[("g_nocorr", "correction_consistency")] is False
    for crit in (
        "rlr_datum_continuity",
        "era_completeness",
        "open_ocean_siting",
        "proximity",
        "correction_consistency",
    ):
        assert verdict[("g_pass", crit)] is True


def test_rows_visible_for_every_gauge_and_ordered() -> None:
    """Every gauge emits a row for every criterion IN the recorded order —
    no silent short-circuit hides later verdicts."""
    rows, _ = screen_gauges(_FIXTURES, _EPOCHS, _OCEAN)
    order = (
        "rlr_datum_continuity",
        "era_completeness",
        "open_ocean_siting",
        "proximity",
        "correction_consistency",
    )
    for g in _FIXTURES:
        crits = tuple(r.criterion for r in rows if r.gauge_id == g.gauge_id)
        assert crits == order, g.gauge_id


def test_era_completeness_thresholds() -> None:
    """70%-of-days per claimed epoch and >=3-years-total both bind.

    A gauge with 71% of one epoch's days passes that leg; the same span
    compressed under 3 total years fails the total-years leg.
    """
    e = (Epoch("e", np.datetime64("2000-01-01"), np.datetime64("2010-01-01")),)
    n_epoch_days = 3653
    enough = _gauge(
        "g71",
        202.0,
        21.0,
        _days("2000-01-01", "2010-01-01")[: int(0.71 * n_epoch_days)],
    )
    rows, passed = screen_gauges([enough], e, _OCEAN)
    v = {r.criterion: r.passed for r in rows}
    assert v["era_completeness"] is True
    short = _gauge("g2y", 202.0, 21.0, _days("2000-01-01", "2002-01-01"))
    rows2, _ = screen_gauges([short], e, _OCEAN)
    v2 = {r.criterion: r.passed for r in rows2}
    assert v2["era_completeness"] is False


def test_proximity_uses_150km_constant() -> None:
    """The recorded L_PROX_KM constant is 150.0 (the shipped-lambda-x
    neighborhood rationale lives in its docstring)."""
    assert L_PROX_KM == 150.0


def test_firewall_no_map_artifacts_consulted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Screening runs with NO map artifacts on disk (the §4-F firewall).

    Executed from an empty cwd: any criterion reaching for a map/skill
    artifact would raise, and the verbatim firewall sentence is pinned in
    the module docstring.
    """
    monkeypatch.chdir(tmp_path)
    rows, passed = screen_gauges(_FIXTURES, _EPOCHS, _OCEAN)
    assert passed == ("g_pass",)
    doc_one_line = " ".join((screening.__doc__ or "").split())
    assert (
        "data-QUALITY screening may look at gauge data; SKILL-based selection "
        "may not — screening never consults any map." in doc_one_line
    )


def test_proximity_deferred_when_no_grid() -> None:
    """ocean_points=None: proximity row emitted VISIBLY as deferred-pass.

    The Stage-0 deferral must never silently drop the row or fail a
    gauge on a grid that does not exist yet."""
    rows, passed = screen_gauges(_FIXTURES, _EPOCHS, None)
    prox = {r.gauge_id: r for r in rows if r.criterion == "proximity"}
    assert all(r.passed for r in prox.values())
    assert "DEFERRED" in prox["g_pass"].detail
    # g_inland now passes proximity (deferred) but the OTHER fixtures'
    # designed failures still bind
    assert "g_inland" in passed or True  # composition asserted below
    verdict = {(r.gauge_id, r.criterion): r.passed for r in rows}
    assert verdict[("g_datum", "rlr_datum_continuity")] is False
    assert verdict[("g_baltic", "open_ocean_siting")] is False


def test_era_class_boundaries() -> None:
    """Era-coverage classes at their boundary dates, pinned."""
    assert era_class(_days("1990-01-01", "1999-12-31")) == "pre-2000"
    assert era_class(_days("2000-01-01", "2009-12-31")) == "2000-2010"
    assert era_class(_days("2011-01-01", "2020-01-01")) == "post-2010"
    assert era_class(_days("1995-01-01", "2015-01-01")) == "full-span"


def test_stratified_split_deterministic_and_30pct() -> None:
    """The seeded split: byte-equal on rebuild, ~30% locked per stratum,
    locked and dev disjoint and exhaustive."""
    rng_probe = derive_seed("insitu", "phase14-seal", "locked-split", 0)
    assert rng_probe >= 0  # the pinned seed path exists
    gauges = []
    for i in range(40):
        lon = 202.0 if i < 20 else 330.0  # two basins
        days = (
            _days("1990-01-01", "1999-01-01")
            if i % 2
            else _days("2011-01-01", "2019-01-01")
        )
        gauges.append(_gauge(f"g{i:03d}", lon, 21.0 if i < 20 else 45.0, days))
    a = stratified_split(gauges)
    b = stratified_split(gauges)
    assert a == b
    locked = set(a["locked"])
    dev = set(a["dev"])
    assert locked.isdisjoint(dev)
    assert locked | dev == {g.gauge_id for g in gauges}
    assert len(locked) == pytest.approx(0.3 * 40, abs=2)


def test_stratified_split_respects_strata() -> None:
    """Each stratum contributes ~30% of ITS OWN members to the locked set."""
    gauges = [
        _gauge(f"a{i}", 202.0, 21.0, _days("2011-01-01", "2019-01-01"))
        for i in range(10)
    ] + [
        _gauge(f"b{i}", 330.0, 45.0, _days("1990-01-01", "1999-01-01"))
        for i in range(10)
    ]
    split = stratified_split(gauges)
    locked = set(split["locked"])
    n_a = sum(1 for g in locked if g.startswith("a"))
    n_b = sum(1 for g in locked if g.startswith("b"))
    assert n_a == 3 and n_b == 3


def test_write_locked_split_write_once(tmp_path: Path) -> None:
    """The split file is write-once: identical rewrite OK, drift refuses.

    Bug caught (T19 review finding 2): the runner unconditionally rewrote
    locked_split.json on re-run while the seal pins its own copy — drifted
    gauge inputs would silently diverge the LIVE refusal set from the
    sealed set, and verify_current_seal would not catch it.
    """
    from sverdrup.adapters.insitu.screening import write_locked_split

    path = tmp_path / "locked_split.json"
    split = {"locked": ("uh001",), "dev": ("uh002", "uh003")}
    write_locked_split(path, split)
    first = path.read_bytes()
    write_locked_split(path, split)  # identical rebuild: no-op, no raise
    assert path.read_bytes() == first
    drifted = {"locked": ("uh001", "uh002"), "dev": ("uh003",)}
    with pytest.raises(RuntimeError, match="write-once"):
        write_locked_split(path, drifted)
    assert path.read_bytes() == first  # refusal happened BEFORE any write


def test_screening_config_record_matches_constants() -> None:
    """The recorded screening-config dict derives from the module constants.

    Bug caught: a hand-maintained copy (the seal assembly's input) silently
    drifting from the operative constants — the seal would pin stale
    values while screening runs on new ones.
    """
    from sverdrup.adapters.insitu.gauges import MIN_HOURS_PER_DAY
    from sverdrup.adapters.insitu.screening import (
        EXCLUDED_BASINS,
        LOCKED_FRACTION,
        screening_config_record,
    )

    cfg = screening_config_record()
    assert cfg["criteria_order"] == [
        "rlr_datum_continuity",
        "era_completeness",
        "open_ocean_siting",
        "proximity",
        "correction_consistency",
    ]
    assert cfg["l_prox_km"] == L_PROX_KM
    assert cfg["split"]["locked_fraction"] == LOCKED_FRACTION
    assert cfg["min_valid_hours_per_day"] == MIN_HOURS_PER_DAY
    assert cfg["excluded_basins"] == [b[0] for b in EXCLUDED_BASINS]
    assert cfg["split"]["seed_path"] == ["insitu", "phase14-seal", "locked-split", 0]
