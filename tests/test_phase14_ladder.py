"""Compute ladder + spend table tests (phase-14 Task 16, 0b-2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sverdrup.application import ladder
from sverdrup.application.ladder import (
    STAGE0_SPEND_TABLE,
    Authorization,
    Tier,
    Wait,
    authorize,
    tier1_eligible,
)


def test_tiers_zero_through_three() -> None:
    """The four rungs exist with the SPEC §4-G identities."""
    assert [t.value for t in Tier] == [0, 1, 2, 3]


def test_stage0_table_rows() -> None:
    """The pre-registered owner defaults are IN the table verbatim.

    Tier-2 probe: US$25 / 8 vCPU / 64 GiB RAM / 6 h / one region; CMEMS
    storage ≤ 50 GiB egress 0; everything else Tier 0/1 at $0.
    """
    rows = {r.task_class: r for r in STAGE0_SPEND_TABLE}
    probe = rows["tier2_probe"]
    assert probe.tier == Tier.CLOUD_NODE
    assert probe.cost_ceiling_usd == 25.0
    assert probe.max_vcpu == 8
    assert probe.max_ram_gib == 64.0
    assert probe.max_wall_h == 6.0
    assert probe.regions == 1
    cmems = rows["cmems_downloads"]
    assert cmems.storage_gib == 50.0
    assert cmems.egress_gib == 0.0
    default = rows["stage0_default"]
    assert default.cost_ceiling_usd == 0.0
    assert default.tier in (Tier.DEV_FIXTURE, Tier.BOX_PRODUCTION)


def test_authorize_within_ceiling() -> None:
    """An estimate inside every bound authorizes with the row recorded."""
    out = authorize(
        "tier2_probe",
        est_cost_usd=12.0,
        est_vcpu=8,
        est_ram_gib=32.0,
        est_wall_h=4.0,
    )
    assert isinstance(out, Authorization)
    assert out.row.task_class == "tier2_probe"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"est_cost_usd": 26.0},
        {"est_vcpu": 16},
        {"est_ram_gib": 128.0},
        {"est_wall_h": 7.0},
    ],
)
def test_authorize_waits_over_any_bound(kwargs: dict[str, float]) -> None:
    """Exceeding ANY single bound yields Wait — never an Authorization."""
    base: dict[str, float] = {
        "est_cost_usd": 1.0,
        "est_vcpu": 1,
        "est_ram_gib": 1.0,
        "est_wall_h": 1.0,
    }
    base.update(kwargs)
    out = authorize(
        "tier2_probe",
        est_cost_usd=base["est_cost_usd"],
        est_vcpu=int(base["est_vcpu"]),
        est_ram_gib=base["est_ram_gib"],
        est_wall_h=base["est_wall_h"],
    )
    assert isinstance(out, Wait)
    assert "owner" in out.reason.lower()


def test_authorize_unknown_task_class_waits() -> None:
    """A task class with no pre-registered row WAITS (never a default spend)."""
    out = authorize("surprise_gpu_farm", est_cost_usd=0.5)
    assert isinstance(out, Wait)


def test_no_code_path_builds_authorization_over_ceiling() -> None:
    """Authorization construction refuses an over-ceiling estimate on ANY leg.

    Executor-set spend never happens: even a buggy caller bypassing
    ``authorize`` cannot mint an over-ceiling Authorization — cost OR
    resource legs (the under-cost 999-vCPU bypass is the refuted attack).
    """
    row = next(r for r in STAGE0_SPEND_TABLE if r.task_class == "tier2_probe")
    with pytest.raises(ValueError, match="ceiling"):
        Authorization(row=row, est_cost_usd=999.0)
    with pytest.raises(ValueError, match="vcpu"):
        Authorization(row=row, est_cost_usd=1.0, est_vcpu=999)


def test_authorize_exact_ceiling_authorizes() -> None:
    """Estimates AT every ceiling authorize (a >= mutant fails here)."""
    out = authorize(
        "tier2_probe",
        est_cost_usd=25.0,
        est_vcpu=8,
        est_ram_gib=64.0,
        est_wall_h=6.0,
    )
    assert isinstance(out, Authorization)


def test_wait_carries_the_standing_sentence() -> None:
    """The owner-facing sentence is the recorded rule, verbatim."""
    out = authorize("tier2_probe", est_cost_usd=26.0)
    assert isinstance(out, Wait)
    assert "executor-set spend never happens" in out.reason


def test_probe_storage_egress_owner_set_ceilings() -> None:
    """Probe storage/egress = the owner-set ceilings (DT-vintage ruling
    item 5, 2026-07-22): ephemeral VM disk 50 GiB, egress 1 GiB — the
    basis string records persistent cloud storage stays 0."""
    row = next(r for r in STAGE0_SPEND_TABLE if r.task_class == "tier2_probe")
    assert row.storage_gib == 50.0
    assert row.egress_gib == 1.0
    assert "persistent storage 0" in row.basis


def test_tier1_eligible_reads_meminfo_at_call_time(tmp_path: Path) -> None:
    """MemAvailable is measured AT CALL TIME from /proc/meminfo (fork-g 4).

    Two calls against two fake meminfo files flip the verdict — a cached
    or constant-headroom implementation cannot.
    """
    lots = tmp_path / "meminfo_big"
    lots.write_text("MemTotal: 65000000 kB\nMemAvailable: 32000000 kB\n")
    little = tmp_path / "meminfo_small"
    little.write_text("MemTotal: 65000000 kB\nMemAvailable: 1000000 kB\n")
    assert tier1_eligible(predicted_peak_mib=2000.0, meminfo=lots) is True
    assert tier1_eligible(predicted_peak_mib=2000.0, meminfo=little) is False


def test_governance_lines_in_docstring() -> None:
    """The data-governance + audit-locality sentences ride in the module."""
    doc = " ".join((ladder.__doc__ or "").split())
    assert (
        "private-source (JPL-adapter) data never leaves owner-controlled "
        "hosts absent explicit owner authorization" in doc
    )
    assert "ANY third party at Tier 0 can audit" in doc
