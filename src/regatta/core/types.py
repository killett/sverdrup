"""Shared enums and type aliases for the regatta framework spine."""

from __future__ import annotations

from enum import Enum, auto

import numpy as np

Field = np.ndarray
Points = np.ndarray
Seed = int
ScalarOrField = float | np.ndarray


class UncertaintyCapability(Enum):
    """Native uncertainty a method can emit, poorest to richest."""

    POINT = auto()
    MARGINAL_VARIANCE = auto()
    COVARIANCE = auto()
    SAMPLES = auto()


class CovFidelity(Enum):
    """Fidelity of a covariance representation; selects/annotates derived routing."""

    EXACT = auto()
    LOW_RANK = auto()
    SAMPLE = auto()


class Linearity(Enum):
    """Functional linearity; LINEAR uses the covariance path, NONLINEAR the sample path."""

    LINEAR = auto()
    NONLINEAR = auto()
