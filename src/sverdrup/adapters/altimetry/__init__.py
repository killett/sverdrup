"""Along-track altimetry source adapters (phase-14 dual-source input layer)."""

from sverdrup.adapters.altimetry.contract import (
    AlongTrackSource,
    BBox,
    SourceDescriptor,
    apply_superobs,
)

__all__ = [
    "AlongTrackSource",
    "BBox",
    "SourceDescriptor",
    "apply_superobs",
]
