"""One deg->km analog for the GP/Matérn family, owned by the kernel (hygiene #10)."""

from __future__ import annotations

from sverdrup.application import tiling
from sverdrup.methods import gmrf_grid, kernel
from sverdrup.validation import params


def test_the_gp_family_deg_to_km_analog_has_one_owner() -> None:
    """Every GP/Matérn-family site aliases ``kernel.KM_PER_DEG``.

    Identity, not equality: a re-pasted ``111.195`` is a distinct float
    object, so a copy fails here even while its value still agrees. The
    MIOST/orbit/spectral family (111.32) is a deliberate, separately pinned
    split and is NOT in this set. Bug caught: one site of the GP family
    being re-tuned (a different sphere radius, say) while the kernel that
    turns ``length_scale`` km back into degrees keeps the old value, so
    tiles, halos and the baseline config disagree on what a kilometre is.
    """
    assert kernel.KM_PER_DEG == 111.195
    for module, name in (
        (kernel, "_DEG2KM"),
        (params, "_KM_PER_DEG"),
        (gmrf_grid, "_DEG2KM"),
        (tiling, "_KM_PER_DEG_LAT"),
    ):
        assert getattr(module, name) is kernel.KM_PER_DEG, module.__name__
