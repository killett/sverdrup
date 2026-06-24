"""Blend fidelity marker + provenance transform with two distinct residual kinds."""

from __future__ import annotations

from sverdrup.core.provenance import (
    KnownBias,
    TransformKind,
    UncertaintyTransform,
    blend_transform,
)
from sverdrup.core.types import CovFidelity


def test_blended_fidelity_is_distinct_marker():
    # Behavior: BLENDED is its own fidelity, never equal to LOW_RANK.
    # Bug caught: reusing LOW_RANK lets a blended product claim constituent fidelity.
    assert CovFidelity.BLENDED not in (
        CovFidelity.EXACT,
        CovFidelity.LOW_RANK,
        CovFidelity.SAMPLE,
    )


def test_two_residual_kinds_are_distinct():
    # Behavior: halo residual and basis-orientation residual are separate biases.
    # Bug caught: collapsing them hides a faint sample seam's true cause.
    # (set-of-two avoids mypy narrowing two enum literals to an always-true `is not`)
    distinct = {
        KnownBias.CONSERVATIVE_HALO_RESIDUAL,
        KnownBias.STRUCTURED_BASIS_ORIENTATION,
    }
    assert len(distinct) == 2


def test_blend_transform_records_conservative_bias_and_k():
    # Behavior: blend_transform stamps kind=BLEND, conservative halo bias, k & bound.
    # Bug caught: a transform without known_bias claims the blend is unbiased.
    t = blend_transform(k=3.0, residual_bound=0.05, structured_residual=True)
    assert isinstance(t, UncertaintyTransform)
    assert t.kind is TransformKind.BLEND
    assert t.known_bias is KnownBias.CONSERVATIVE_HALO_RESIDUAL
    assert t.params["k"] == 3.0
    assert t.params["residual_bound"] == 0.05
    # the structured residual is recorded as a DISTINCT marker, not folded into the halo one
    assert (
        t.params["structured_coherence"] == KnownBias.STRUCTURED_BASIS_ORIENTATION.name
    )


def test_blend_transform_without_structured_omits_marker():
    # Behavior: when the spatial-sqrt driver is used, no structured-orientation marker.
    # Bug caught: always stamping the structured marker misattributes a bias that
    # the non-member-only driver does not introduce.
    t = blend_transform(k=3.0, residual_bound=0.05, structured_residual=False)
    assert "structured_coherence" not in t.params
