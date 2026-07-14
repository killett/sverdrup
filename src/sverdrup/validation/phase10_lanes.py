"""Phase-10 lane definitions: boxes, restrictions, providers, seeds, anchors, bars.

One core parameterization {c0, log_L0, Lt}; lanes are RESTRICTIONS of a
single 6-dim space (spec §2 batch-1 fold 2): lane-0 freezes c1 = c2 = l1 = 0,
V releases (c1, c2), VL-joint releases l1 as well. One provider path, one
solve path; nesting BY CONSTRUCTION. OI parameter names live HERE in
validation/, never in application/tuning/ (method-agnosticism).
"""

from __future__ import annotations

import math

from scipy.stats import qmc  # type: ignore[import-untyped]

from sverdrup.application.calibration.constants import SIGMA_OBS2
from sverdrup.application.tuning.objective import HardBar, bars_for
from sverdrup.core.parameters import LatitudeField, LatitudeVaryingProvider
from sverdrup.core.seeding import derive_seed
from sverdrup.core.types import UncertaintyCapability

# ---------------------------------------------------------------------------
# Boxes (spec §2 principles -> endpoints; rationale recorded beside each).
# ---------------------------------------------------------------------------
BOXES: dict[str, tuple[float, float]] = {
    # brackets 0 <-> variance 1.0 (the signed value); |2*c0| = 3.0 covers the
    # measured OI log-s span 1.93 (phase9_field_oi.json clip [-1.5414, 0.3928]).
    "c0": (-1.5, 1.5),
    "c1": (-1.0, 1.0),
    # max swing |c1| + |c2| <= 2.5 log units over v in [-1, 1] — bounded and
    # recorded vs the artifact span [-1.5414, 0.3928] (lane-A range ± log 1.25).
    "c2": (-1.5, 1.5),
    # brackets L0 = 1.0 deg (the signed lx=ly).
    "log_L0": (math.log(0.5), math.log(2.0)),
    # includes 0 AND both signs; asymmetric toward the Rossby sign (shorter
    # scales poleward = negative l1); swing e^{2*l1} in [0.37, 1.82].
    "l1": (-0.5, 0.3),
    # brackets Lt = 7 d (the signed temporal scale).
    "Lt": (3.0, 14.0),
}

# Fixed dimension order for the SHARED 6-dim Sobol cube (pairing depends on it).
ALL_DIMS: tuple[str, ...] = ("c0", "c1", "c2", "log_L0", "l1", "Lt")

# Released (non-core) coordinates per lane; core {c0, log_L0, Lt} is always
# tuned. Frozen coords are pinned AT 0.0 in trial dicts.
LANES: dict[str, frozenset[str]] = {
    "lane0": frozenset(),
    "V": frozenset({"c1", "c2"}),
    "VL": frozenset({"c1", "c2", "l1"}),
}


def sobol_trials(lane: str, n: int) -> list[dict[str, float]]:
    """Return ``n`` paired Sobol trial dicts for ``lane``.

    The sequence is drawn in the FULL 6-dim unit cube with ONE engine seed
    common to ALL lanes (``derive_seed("oi", "phase10-lanes", "sobol", 0)``);
    each lane MASKS its frozen dims to the restriction value 0.0 — so the
    same trial index has IDENTICAL shared-dim draws across lanes, differing
    only on released coords (spec §4 paired seeds; batch-3 fold 2a).

    Args:
        lane: A key of :data:`LANES`.
        n: Number of trials.

    Returns:
        Trial dicts carrying all six dims (frozen dims exactly 0.0).
    """
    released = LANES[lane]
    seed = derive_seed("oi", "phase10-lanes", "sobol", 0)
    sampler = qmc.Sobol(d=len(ALL_DIMS), scramble=True, seed=seed)
    unit = sampler.random(n)
    trials: list[dict[str, float]] = []
    for row in unit:
        t: dict[str, float] = {}
        for j, dim in enumerate(ALL_DIMS):
            lo, hi = BOXES[dim]
            value = float(lo + row[j] * (hi - lo))
            if dim in ("c1", "c2", "l1") and dim not in released:
                value = 0.0  # restriction bookkeeping: frozen AT zero
            t[dim] = value
        trials.append(t)
    return trials


def provider_for_trial(trial: dict[str, float]) -> LatitudeVaryingProvider:
    """Build the provider for one trial dict (the kernel-factory glue).

    Contract with ``gaussian_kernel_from_params`` (Task-4): the multiplier
    rides ``lx_mult`` (NEVER a field under ``lx_deg``), and is OMITTED at
    l1 == 0 so all-zero released coords route the STATIONARY class; the
    variance stays a scalar ``exp(c0)`` when c1 == c2 == 0.

    Args:
        trial: A six-dim trial dict (:func:`sobol_trials` shape).

    Returns:
        The provider resolving ``variance``, ``lx_deg``, ``time_scale``
        (and ``lx_mult`` when l1 is released and nonzero).
    """
    core: dict[str, float] = {
        "lx_deg": math.exp(trial["log_L0"]),
        "time_scale": trial["Lt"],
    }
    varied: dict[str, LatitudeField] = {}
    if trial["c1"] == 0.0 and trial["c2"] == 0.0:
        core["variance"] = math.exp(trial["c0"])
    else:
        varied["variance"] = LatitudeField(
            "exp-quad", (trial["c0"], trial["c1"], trial["c2"])
        )
    if trial["l1"] != 0.0:
        varied["lx_mult"] = LatitudeField("exp-linear-mult", (trial["l1"],))
    return LatitudeVaryingProvider(core=core, varied=varied)


def anchors_for(
    lane: str, winners: dict[str, dict[str, float]]
) -> list[dict[str, float]]:
    """Return the pre-registered anchor trials to evaluate inside ``lane``.

    Spec §4: the lane-0 winner is evaluated inside V and VL (released coords
    at 0 — already true of a lane-0 trial dict); the V winner inside VL with
    l1 = 0. Nested lanes therefore tie-or-win by construction on the
    selection read. Sources are copied, never mutated.

    Args:
        lane: The lane about to run.
        winners: Winner trial dicts keyed by lane name (missing = not run).

    Returns:
        Anchor trial dicts (possibly empty).
    """
    anchors: list[dict[str, float]] = []
    if lane in ("V", "VL") and "lane0" in winners:
        anchors.append(dict(winners["lane0"]))
    if lane == "VL" and "V" in winners:
        v_anchor = dict(winners["V"])
        v_anchor["l1"] = 0.0
        anchors.append(v_anchor)
    return anchors


def lane_bars() -> tuple[HardBar, ...]:
    """Return the lane hard bars: capability-derived for SAMPLES (spec §4).

    µ ≥ 0.85 floor + coverage bar. Coverage convention (batch-2 fold 2): raw
    posterior variance + SIGMA_OBS2 floor — ONE convention with the
    acceptance bar at s ≡ 1 (see :func:`lane_coverage_extra_var`).
    """
    return bars_for(UncertaintyCapability.SAMPLES)


def lane_coverage_extra_var() -> float:
    """Return the variance added to raw posterior var before coverage.

    RECORDED EXPECTATION (spec §4, pre-registered so bar-binding clusters
    are not misread at execution): ŝ_OI = 0.6621 → baseline raw coverage
    ≈ 0.78, at the coverage band's TOP edge — the bar is LIVE for this
    product; variance-increasing trials tripping it is the design working,
    not a defect. Inadmissible trials are recorded, never selected.
    """
    return float(SIGMA_OBS2)


def lane_names() -> tuple[str, ...]:
    """Return the committed lane names in execution order."""
    return ("lane0", "V", "VL")


def trial_admissible(
    scores: dict[str, float], bars: tuple[HardBar, ...] | None = None
) -> bool:
    """Return True iff every lane hard bar passes for ``scores``.

    Args:
        scores: The trial's score vector.
        bars: Override bars (default :func:`lane_bars`).
    """
    return all(b.passes(scores) for b in (bars if bars is not None else lane_bars()))
