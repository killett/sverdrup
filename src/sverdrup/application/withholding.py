"""Pluggable blocked/grouped withholding strategies (design section 8; invariant 12)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol, runtime_checkable

import numpy as np

from sverdrup.core.observations import ObsWindow


class Assignment(Enum):
    """Per-observation split label."""

    TRAIN = auto()
    VALIDATION = auto()
    BUFFER_DISCARD = auto()
    TEST = auto()


@dataclass(frozen=True)
class SplitAssignment:
    """Per-observation assignment array + a stable id.

    Attributes:
        assignment: ``(n,)`` array of ``Assignment`` members (dtype object).
        id: A stable identifier of the strategy + parameters.
    """

    assignment: np.ndarray
    id: str


@runtime_checkable
class WithholdingStrategy(Protocol):
    """Assigns each observation to TRAIN / VALIDATION / BUFFER_DISCARD / TEST."""

    def split(self, obs: ObsWindow) -> SplitAssignment:
        """Return the per-observation assignment for ``obs``."""
        ...


@dataclass(frozen=True)
class LeaveOneMissionOut:
    """Withhold one or more whole missions for validation; the rest train.

    Attributes:
        validation_missions: Mission labels held out entirely for validation.
    """

    validation_missions: list[str]

    def split(self, obs: ObsWindow) -> SplitAssignment:
        """Assign each obs TRAIN unless its mission is withheld -> VALIDATION.

        Args:
            obs: The observation window (must carry per-obs mission labels).

        Returns:
            The per-observation ``SplitAssignment``.

        Raises:
            ValueError: If ``obs`` has no mission labels.
        """
        if obs.mission is None:
            raise ValueError("LeaveOneMissionOut requires per-obs mission labels.")
        mask = np.isin(obs.mission, self.validation_missions)
        a = np.empty(len(obs), dtype=object)
        a[mask] = Assignment.VALIDATION
        a[~mask] = Assignment.TRAIN
        return SplitAssignment(a, id=f"loo:{sorted(self.validation_missions)}")


@dataclass(frozen=True)
class PerMissionTemporalFraction:
    """Per mission: first ``train`` -> TRAIN, next ``buffer`` -> BUFFER_DISCARD, rest -> VALIDATION.

    Attributes:
        train: Leading temporal fraction assigned to TRAIN.
        buffer: Middle fraction discarded to sever train/validation autocorrelation.
        validation: Trailing fraction assigned to VALIDATION.
    """

    train: float
    buffer: float
    validation: float

    def split(self, obs: ObsWindow) -> SplitAssignment:
        """Temporally split each mission's record with an autocorrelation-severing buffer.

        Args:
            obs: The observation window (must carry per-obs mission labels).

        Returns:
            The per-observation ``SplitAssignment`` with a disjoint buffer-discard band.

        Raises:
            ValueError: If ``obs`` has no mission labels.
        """
        if obs.mission is None:
            raise ValueError(
                "PerMissionTemporalFraction requires per-obs mission labels."
            )
        t = obs.coords()[:, 2]
        a = np.empty(len(obs), dtype=object)
        for mission in np.unique(obs.mission):
            idx = np.where(obs.mission == mission)[0]
            order = idx[np.argsort(t[idx])]
            n = len(order)
            n_tr = int(n * self.train)
            n_bf = int(n * self.buffer)
            a[order[:n_tr]] = Assignment.TRAIN
            a[order[n_tr : n_tr + n_bf]] = Assignment.BUFFER_DISCARD
            a[order[n_tr + n_bf :]] = Assignment.VALIDATION
        return SplitAssignment(
            a, id=f"pmtf:{self.train}/{self.buffer}/{self.validation}"
        )
