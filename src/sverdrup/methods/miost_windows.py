"""Temporal WindowPlan + linear blend (spec §4.1; designed at L_t_max=12).

Placement (owner-corrected 2026-07-03): 8 stride windows s_k = -18 + 45k plus a
RIGHT-ALIGNED last window [322, 382] so the span assert is satisfiable inside the
obs data [-31, 395]. Every pairwise overlap >= L_T_MAX (interior 15 d; last pair 35 d).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sverdrup.methods.miost_basis import STRIDE_DAYS, W_DAYS

OBS_START_DAY = -31.0  # 2016-12-01
OBS_END_DAY = 395.0  # 2018-01-31
L_T_MAX = 12.0  # D3 ceiling; placement designed here (fold A)


@dataclass(frozen=True)
class Window:
    """One solve window [start, start+W]."""

    start_day: float

    @property
    def end_day(self) -> float:
        """Window end [days since epoch]."""
        return self.start_day + W_DAYS

    @property
    def id(self) -> str:
        """Stable id derived from placement (cache key component)."""
        return f"w{self.start_day:+08.1f}+{W_DAYS:.0f}"


def _default_starts() -> tuple[float, ...]:
    """k=0..7 stride windows + right-aligned last: 395 - 12 - 60 - 1 = 322."""
    right = OBS_END_DAY - L_T_MAX - W_DAYS - 1.0
    return tuple(-18.0 + STRIDE_DAYS * k for k in range(8)) + (right,)


@dataclass(frozen=True)
class WindowPlan:
    """9 windows covering outputs 0..364 with two-sided support inside the data."""

    starts: tuple[float, ...] = field(default_factory=_default_starts)
    windows: tuple[Window, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Materialize Window objects from the start days."""
        object.__setattr__(self, "windows", tuple(Window(s) for s in self.starts))

    def covering(self, day: float) -> list[Window]:
        """Windows whose span contains ``day`` (1 interior, 2 in overlaps).

        Args:
            day: Output day [days since epoch].

        Returns:
            Covering windows ordered by start day.
        """
        return [w for w in self.windows if w.start_day <= day <= w.end_day]

    def weight(self, w: Window, day: float) -> float:
        """Linear blend weight ∝ boundary distance over the ACTUAL pairwise overlap.

        Args:
            w: One of the covering windows for ``day``.
            day: Output day [days since epoch].

        Returns:
            Blend weight in [0, 1]; unity outside overlaps.
        """
        wins = self.covering(day)
        if len(wins) == 1:
            return 1.0
        left, right = wins  # ordered by start
        overlap = left.end_day - right.start_day  # >= L_T_MAX by construction
        if w.id == left.id:
            return (left.end_day - day) / overlap
        return (day - right.start_day) / overlap
