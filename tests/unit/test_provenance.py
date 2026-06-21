from regatta.core.provenance import (
    KnownBias,
    TransformKind,
    UncertaintyProvenance,
    UncertaintyTransform,
)
from regatta.core.types import UncertaintyCapability


def test_native_provenance_not_synthesized():
    prov = UncertaintyProvenance(
        native_capability=UncertaintyCapability.SAMPLES, transformations=[]
    )
    assert prov.is_synthesized is False


def test_perturb_transform_marks_synthesized_with_bias():
    # Bug caught: presenting synthesized uncertainty as native (invariant 8).
    prov = UncertaintyProvenance(
        native_capability=UncertaintyCapability.POINT,
        transformations=[
            UncertaintyTransform(
                kind=TransformKind.INPUT_PERTURBATION,
                known_bias=KnownBias.UNDER_DISPERSED_IN_VOIDS,
                params={"m": 50},
            )
        ],
    )
    assert prov.is_synthesized is True
    assert prov.transformations[0].known_bias is KnownBias.UNDER_DISPERSED_IN_VOIDS
