"""Compute ladder + Stage-0 spend table (phase-14 0b-2, SPEC §4-G).

Spend gates: every stage plan carries a pre-registered SPEND TABLE (rung,
measured-cost basis, authorized ceiling per task class, storage and egress
columns); an execution-blocking spend outside its tier WAITS for the owner
— executor-set spend never happens (the Phase-10 standing rule, monied).

**Data governance (verbatim):** private-source (JPL-adapter) data never
leaves owner-controlled hosts absent explicit owner authorization;
public-lineage data may use any authorized tier.

**Audit-locality rule (verbatim):** no acceptance instrument may REQUIRE
cloud to re-verify given artifacts — cloud produces artifacts, the box can
always audit them; on public-lineage artifacts, ANY third party at Tier 0
can audit — the reproducibility ethic stated as compute policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

_MEMINFO = Path("/proc/meminfo")

# Tier-1 launch predicate: predicted peak must fit under half of the
# MEASURED MemAvailable (the Phase-8/12 co-tenant headroom convention).
TIER1_HEADROOM_FRACTION = 0.5


class Tier(Enum):
    """The compute rungs (SPEC §4-G).

    0 — mini-PC dev fixtures + CI (every capability keeps a Tier-0
    fixture; the dev-scope discipline survives scaling by construction).
    1 — mini-PC production-tier sequential single-tile runs where sizing
    clears (OOM-priced by checkpoint/resume + retry machinery).
    2 — single cloud node (SkyPilot) — the first spend rung.
    3 — multi-node fan-out (per-tile/per-era fleet; embarrassingly
    parallel outside blend assembly).
    """

    DEV_FIXTURE = 0
    BOX_PRODUCTION = 1
    CLOUD_NODE = 2
    FLEET = 3


@dataclass(frozen=True)
class SpendRow:
    """One pre-registered spend-table row (ceilings are OWNER inputs)."""

    task_class: str
    tier: Tier
    cost_ceiling_usd: float
    storage_gib: float
    egress_gib: float
    basis: str
    max_vcpu: int = 0
    max_ram_gib: float = 0.0
    max_wall_h: float = 0.0
    regions: int = 1


# The STAGE-0 table — the plan-header pre-registered owner defaults,
# verbatim. Exceeding any bound of any row = WAIT for the owner.
STAGE0_SPEND_TABLE: tuple[SpendRow, ...] = (
    SpendRow(
        task_class="tier2_probe",
        tier=Tier.CLOUD_NODE,
        cost_ceiling_usd=25.0,
        storage_gib=0.0,
        egress_gib=0.0,
        # storage/egress ceilings were NOT owner-registered for the probe:
        # 0 ceiling means ANY storage/egress estimate WAITs (monied rule).
        basis=(
            "pre-registered owner default (plan header 2026-07-22); "
            "storage/egress unregistered -> 0 ceiling, any use WAITs"
        ),
        max_vcpu=8,
        max_ram_gib=64.0,
        max_wall_h=6.0,
        regions=1,
    ),
    SpendRow(
        task_class="cmems_downloads",
        tier=Tier.BOX_PRODUCTION,
        cost_ceiling_usd=0.0,
        storage_gib=50.0,
        egress_gib=0.0,
        basis="pre-registered owner default: public-data egress $0",
    ),
    SpendRow(
        task_class="stage0_default",
        tier=Tier.BOX_PRODUCTION,
        cost_ceiling_usd=0.0,
        storage_gib=0.0,
        egress_gib=0.0,
        basis="all other Stage-0 compute: Tier 0/1 only, $0",
    ),
)


@dataclass(frozen=True)
class Wait:
    """The WAIT verdict: the estimate is outside its pre-registered row."""

    task_class: str
    reason: str


@dataclass(frozen=True)
class Authorization:
    """An in-ceiling authorization bound to its spend-table row.

    Construction carries EVERY estimate leg and REFUSES any over-ceiling
    value — even a caller bypassing :func:`authorize` cannot mint
    executor-set spend on any axis.
    """

    row: SpendRow
    est_cost_usd: float
    est_vcpu: int = 0
    est_ram_gib: float = 0.0
    est_wall_h: float = 0.0

    def __post_init__(self) -> None:
        """Refuse construction above ANY of the row's ceilings."""
        over = _over_ceilings(
            self.row,
            self.est_cost_usd,
            self.est_vcpu,
            self.est_ram_gib,
            self.est_wall_h,
        )
        if over:
            raise ValueError(
                f"estimate exceeds the pre-registered ceiling(s) for "
                f"{self.row.task_class!r} ({'; '.join(over)}) — executor-set "
                "spend never happens; this WAITS for the owner"
            )


def _over_ceilings(
    row: SpendRow,
    est_cost_usd: float,
    est_vcpu: int,
    est_ram_gib: float,
    est_wall_h: float,
) -> list[str]:
    """The list of estimate legs exceeding their row ceilings (empty = ok)."""
    over = []
    if est_cost_usd > row.cost_ceiling_usd:
        over.append(f"cost {est_cost_usd} > {row.cost_ceiling_usd} USD")
    if row.max_vcpu and est_vcpu > row.max_vcpu:
        over.append(f"vcpu {est_vcpu} > {row.max_vcpu}")
    if row.max_ram_gib and est_ram_gib > row.max_ram_gib:
        over.append(f"ram {est_ram_gib} > {row.max_ram_gib} GiB")
    if row.max_wall_h and est_wall_h > row.max_wall_h:
        over.append(f"wall {est_wall_h} > {row.max_wall_h} h")
    return over


def authorize(
    task_class: str,
    est_cost_usd: float,
    est_vcpu: int = 0,
    est_ram_gib: float = 0.0,
    est_wall_h: float = 0.0,
) -> Authorization | Wait:
    """Authorize an estimate against the Stage-0 spend table, or WAIT.

    Args:
        task_class: The spend-table row key.
        est_cost_usd: Estimated total cost.
        est_vcpu: Estimated VM vCPU count (cloud rows).
        est_ram_gib: Estimated VM RAM (cloud rows).
        est_wall_h: Estimated wall time (cloud rows).

    Returns:
        An :class:`Authorization` when EVERY bound covers the estimate;
        otherwise a :class:`Wait` carrying the owner-facing sentence. An
        unknown task class always WAITS — there is no default spend row.
    """
    row = next((r for r in STAGE0_SPEND_TABLE if r.task_class == task_class), None)
    if row is None:
        return Wait(
            task_class=task_class,
            reason=(
                f"no pre-registered spend row for {task_class!r}: the owner "
                "must register one before any spend (executor-set spend "
                "never happens)"
            ),
        )
    over = _over_ceilings(row, est_cost_usd, est_vcpu, est_ram_gib, est_wall_h)
    if over:
        return Wait(
            task_class=task_class,
            reason=(
                f"estimate exceeds the pre-registered {task_class!r} row "
                f"({'; '.join(over)}): the task WAITS for the owner — "
                "executor-set spend never happens"
            ),
        )
    return Authorization(
        row=row,
        est_cost_usd=est_cost_usd,
        est_vcpu=est_vcpu,
        est_ram_gib=est_ram_gib,
        est_wall_h=est_wall_h,
    )


def tier1_eligible(predicted_peak_mib: float, meminfo: Path = _MEMINFO) -> bool:
    """Tier-1 launch predicate on MEASURED available RAM (fork-g pin 4).

    Reads ``MemAvailable`` from ``/proc/meminfo`` AT CALL TIME — the
    co-tenant box's headroom is a measurement, not a constant (the Phase-8
    predicate re-grounding lesson).

    Args:
        predicted_peak_mib: The sizing model's predicted peak RSS.
        meminfo: The meminfo file (a fake in tests).

    Returns:
        True iff the predicted peak fits under
        ``TIER1_HEADROOM_FRACTION × MemAvailable``.
    """
    for line in meminfo.read_text().splitlines():
        if line.startswith("MemAvailable:"):
            avail_mib = float(line.split()[1]) / 1024.0  # kB -> MiB
            return predicted_peak_mib <= TIER1_HEADROOM_FRACTION * avail_mib
    raise RuntimeError(f"MemAvailable not found in {meminfo}")
