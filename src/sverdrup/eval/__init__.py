"""Evaluator family exports (Phase-11 Task 5).

``ALL_EVALUATORS`` is the canonical factory tuple over EVERY registered
evaluator — the integrity test (declared⇒consumed, constraint 3) iterates it,
and Task 6's ``default_registry()`` builds FROM it (minus the recorded
exclusions). Add a new evaluator here or it ships without integrity coverage.
"""

from __future__ import annotations

from collections.abc import Callable

from sverdrup.core.evaluation import Evaluator
from sverdrup.eval.accuracy import Accuracy
from sverdrup.eval.calibration import Calibration
from sverdrup.eval.fidelity import SpectralFidelity
from sverdrup.eval.groundtrack import GroundTrack
from sverdrup.eval.insitu import InSituGauges
from sverdrup.eval.resolution import EffectiveResolution
from sverdrup.eval.skill import NormalizedSkillScore

ALL_EVALUATORS: tuple[Callable[[], Evaluator], ...] = (
    Accuracy,
    Calibration,
    NormalizedSkillScore,
    GroundTrack,
    InSituGauges,
    SpectralFidelity,
    EffectiveResolution,
)

__all__ = ["ALL_EVALUATORS"]
