"""Typed uncertainty provenance chain + product provenance (invariant 8; spec 5.3, 5.8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from regatta.core.types import UncertaintyCapability


class TransformKind(Enum):
    """The kind of uncertainty transform applied to a native head."""

    INPUT_PERTURBATION = auto()
    DIAGONAL_INFLATION = auto()
    POSTERIOR_RECALIBRATED = auto()
    DERIVED = auto()


class KnownBias(Enum):
    """A documented systematic bias a transform is known to introduce."""

    NONE = auto()
    UNDER_DISPERSED_IN_VOIDS = auto()


@dataclass(frozen=True)
class UncertaintyTransform:
    """One step in the uncertainty-synthesis chain, with its known bias."""

    kind: TransformKind
    known_bias: KnownBias = KnownBias.NONE
    params: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class UncertaintyProvenance:
    """The native uncertainty head plus the ordered chain of transforms applied."""

    native_capability: UncertaintyCapability
    transformations: list[UncertaintyTransform]

    @property
    def is_synthesized(self) -> bool:
        """True iff any transform was applied (uncertainty is not native)."""
        return len(self.transformations) > 0


@dataclass(frozen=True)
class ProductProvenance:
    """Full provenance for one produced field: method, params, seed, split, lineage."""

    method: str
    params_key: str
    seed: int
    split_id: str
    code_version: str
    input_manifest: dict[str, object]
    uncertainty: UncertaintyProvenance
