"""Typed uncertainty provenance chain + product provenance (invariant 8; spec 5.3, 5.8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from sverdrup.core.types import UncertaintyCapability


class TransformKind(Enum):
    """The kind of uncertainty transform applied to a native head."""

    INPUT_PERTURBATION = auto()
    DIAGONAL_INFLATION = auto()
    POSTERIOR_RECALIBRATED = auto()
    DERIVED = auto()
    BLEND = auto()


class KnownBias(Enum):
    """A documented systematic bias a transform is known to introduce."""

    NONE = auto()
    UNDER_DISPERSED_IN_VOIDS = auto()
    CONSERVATIVE_HALO_RESIDUAL = auto()
    STRUCTURED_BASIS_ORIENTATION = auto()
    DEGRADED_COHERENCE = auto()


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


def blend_transform(
    k: float, residual_bound: float, *, structured_residual: bool
) -> UncertaintyTransform:
    """Build the BlendTransform recording the blend's conservative residual(s).

    Args:
        k: The halo multiple used (the finite-halo residual shrinks as k grows).
        residual_bound: The recorded conservative bound on the finite-halo residual.
        structured_residual: Whether the member-only ``z_r`` structured driver was used,
            which introduces a distinct basis-orientation residual.

    Returns:
        An ``UncertaintyTransform`` of kind ``BLEND`` with the conservative halo bias and,
        when ``structured_residual`` is set, a distinct structured-coherence marker.
    """
    params: dict[str, object] = {"k": k, "residual_bound": residual_bound}
    if structured_residual:
        params["structured_coherence"] = KnownBias.STRUCTURED_BASIS_ORIENTATION.name
    return UncertaintyTransform(
        kind=TransformKind.BLEND,
        known_bias=KnownBias.CONSERVATIVE_HALO_RESIDUAL,
        params=params,
    )


def degradation_transform() -> UncertaintyTransform:
    """Build the transform recording cross-tile coherence loss for the degradation driver.

    The perturb-ensemble driver forces each tile with independent members, so cross-tile
    coherence is not guaranteed. The blend records this explicitly (``DEGRADED_COHERENCE``)
    rather than presenting an incoherent product as coherent.

    Returns:
        An ``UncertaintyTransform`` of kind ``BLEND`` carrying ``DEGRADED_COHERENCE``.
    """
    return UncertaintyTransform(
        kind=TransformKind.BLEND,
        known_bias=KnownBias.DEGRADED_COHERENCE,
        params={
            "coherence": "per-tile-independent members; cross-tile coherence not guaranteed"
        },
    )
