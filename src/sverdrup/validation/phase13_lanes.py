"""Phase-13 lane definitions: restrictions, paired Sobol, anchors, bars.

One 7-dim parameterization (δ×4 + ρ + Λ×2); lanes are FROZEN RESTRICTIONS
(spec §4): lane-0 = the SIGNED config (quoted — zero re-proving), lane-D
releases {δ×4, ρ} with modes COLUMN-ABSENT, lane-C releases all seven,
modes-only releases {ρ, Λ×2} with δ ≡ 0. Masked δ dims are pinned AT 0.0;
masked ρ at the SIGNED value; masked Λ dims are ``None`` — structural
column absence (spec §2 rider 3), NEVER a Λ = 0 diagonal.

ONE shared Sobol engine (``derive_seed("miost","phase13-lanes","sobol",0)``)
with per-lane dim MASKING of a single 7-dim sequence — the same trial index
carries IDENTICAL shared-dim draws across lanes (pairing survives; NO
per-lane engines). Anchors are evaluated extra points, never Sobol points.
"""

from __future__ import annotations

from scipy.stats import qmc  # type: ignore[import-untyped]

from sverdrup.application.tuning.objective import HardBar, bars_for
from sverdrup.core.seeding import derive_seed
from sverdrup.core.types import UncertaintyCapability
from sverdrup.methods.miost_rspec import RSpec
from sverdrup.validation.phase13_boxes import (
    DELTA_BOX,
    LOG10_LAM_BOX,
    LOG10_RHO_BOX,
    SOBOL_DIMS,
    SOBOL_ENGINE_KEY,
)

# The signed Stage-A winner, verbatim (asserted against the record by test).
SIGNED_PARAMS: dict[str, float] = {
    "spacing_alpha": 1.0656719505786896,
    "log10_rho": -1.5990709075704217,
    "q_slope": 1.4518111273646355,
    "l_t_days": 6.00630128569901,
}

ALL_DIMS: tuple[str, ...] = SOBOL_DIMS  # fixed order; pairing depends on it
_DELTA_DIMS = ALL_DIMS[:4]
_LAM_DIMS = ("log_lam_bias", "log_lam_tilt")

BOXES: dict[str, tuple[float, float]] = {
    "delta_alg": DELTA_BOX,
    "delta_h2g": DELTA_BOX,
    "delta_j2g": DELTA_BOX,
    "delta_j2n": DELTA_BOX,
    "log10_rho": LOG10_RHO_BOX,
    "log_lam_bias": LOG10_LAM_BOX,
    "log_lam_tilt": LOG10_LAM_BOX,
}

# Released dims per lane (frozen dims take the restriction value).
LANES: dict[str, frozenset[str]] = {
    "lane0": frozenset(),
    "D": frozenset({*_DELTA_DIMS, "log10_rho"}),
    "C": frozenset(ALL_DIMS),
    "modes-only": frozenset({"log10_rho", *_LAM_DIMS}),
}

Trial = dict[str, float | None]


def _masked(dim: str, value: float, released: frozenset[str]) -> float | None:
    """Apply the restriction semantics for a masked dim."""
    if dim in released:
        return value
    if dim in _LAM_DIMS:
        return None  # structural COLUMN ABSENCE — never Lambda = 0
    if dim == "log10_rho":
        return SIGNED_PARAMS["log10_rho"]
    return 0.0  # delta contrasts frozen AT zero


def sobol_trials(lane: str, n: int) -> list[Trial]:
    """Return ``n`` paired Sobol trial dicts for ``lane``.

    Args:
        lane: A key of :data:`LANES`.
        n: Number of trials.

    Returns:
        Trial dicts carrying all seven dims (masked dims at their
        restriction values; Λ masked = None).
    """
    released = LANES[lane]
    seed = derive_seed(*SOBOL_ENGINE_KEY)
    sampler = qmc.Sobol(d=len(ALL_DIMS), scramble=True, seed=seed)
    unit = sampler.random(n)
    trials: list[Trial] = []
    for row in unit:
        t: Trial = {}
        for j, dim in enumerate(ALL_DIMS):
            lo, hi = BOXES[dim]
            t[dim] = _masked(dim, float(lo + row[j] * (hi - lo)), released)
        trials.append(t)
    return trials


def lane0_trial() -> Trial:
    """The signed configuration as a trial dict (the quoted lane-0 point)."""
    return {dim: _masked(dim, 0.0, frozenset()) for dim in ALL_DIMS}


def rspec_for_trial(trial: Trial) -> RSpec:
    """Build the RSpec for one trial dict (the method-config glue).

    Args:
        trial: A seven-dim trial dict (:func:`sobol_trials` shape).

    Returns:
        The RSpec: δ from the four contrast dims (s3a derived inside);
        modes active iff BOTH Λ dims carry values.
    """
    deltas = {
        m: float(trial[f"delta_{m}"] or 0.0) for m in ("alg", "h2g", "j2g", "j2n")
    }
    lb, lt = trial["log_lam_bias"], trial["log_lam_tilt"]
    return RSpec(
        deltas=deltas,
        log_lam_bias=None if lb is None else float(lb),
        log_lam_tilt=None if lt is None else float(lt),
    )


def params_for_trial(trial: Trial) -> dict[str, float]:
    """Solver params for one trial: signed {α, q_slope, L_t} + the trial's ρ.

    Args:
        trial: A seven-dim trial dict.

    Returns:
        The four-dim solver params (spec §4: α/q_slope/L_t FROZEN at the
        signed record; ρ reopened).
    """
    rho = trial["log10_rho"]
    return {
        "spacing_alpha": SIGNED_PARAMS["spacing_alpha"],
        "log10_rho": SIGNED_PARAMS["log10_rho"] if rho is None else float(rho),
        "q_slope": SIGNED_PARAMS["q_slope"],
        "l_t_days": SIGNED_PARAMS["l_t_days"],
    }


def anchors_for(lane: str, winners: dict[str, Trial]) -> list[Trial]:
    """Return the pre-registered anchor trials to evaluate inside ``lane``.

    Spec §4 anchor embedding: lane-0's config sits inside lane-D's box
    (trivial restriction point) and enters lane-C evaluated at the Λ
    BOX-FLOOR (log Λ = −∞ is outside any box); lane-D's winner enters
    lane-C the same way, as an EVALUATED point after lane-D selection.
    Sources are copied, never mutated.

    Args:
        lane: The lane about to run.
        winners: Winner trial dicts keyed by lane name (missing = not run).

    Returns:
        Anchor trial dicts (possibly empty).
    """
    floor = LOG10_LAM_BOX[0]
    anchors: list[Trial] = []
    if lane == "D":
        anchors.append(lane0_trial())
    if lane == "C":
        a = lane0_trial()
        a["log_lam_bias"] = floor
        a["log_lam_tilt"] = floor
        anchors.append(a)
        if "D" in winners:
            d = dict(winners["D"])
            d["log_lam_bias"] = floor
            d["log_lam_tilt"] = floor
            anchors.append(d)
    return anchors


def lane_bars() -> tuple[HardBar, ...]:
    """Return the lane hard bars: POINT-capability (µ floor only).

    Lane trials are POINT solves (members are generated at tuned winners
    only, spec 6.1) — no variance maps exist per trial, so no coverage bar.
    """
    return bars_for(UncertaintyCapability.POINT)


def trial_admissible(
    scores: dict[str, float], bars: tuple[HardBar, ...] | None = None
) -> bool:
    """Return True iff every lane hard bar passes for ``scores``.

    Args:
        scores: The trial's score vector.
        bars: Override bars (default :func:`lane_bars`).
    """
    return all(b.passes(scores) for b in (bars if bars is not None else lane_bars()))
