"""Along-track source contract (phase-14 workstream 0c, fork-a pins).

Pins carried in code, per SPEC §4-A of
``docs/superpowers/specs/2026-07-21-phase14-scaling-program-design.md``:

- **Content-addressed descriptor with per-file shas ALWAYS** (fork-a pin 3):
  ``SourceDescriptor.content_manifest`` is the only provenance mechanism —
  no processing-tag or version-string alternative exists in the type.
- **Loading NEVER mutates values** (fork-a pin 4): any transform (super-obs
  later) is a separate parameterized loader-layer step recorded in
  provenance. The hook is :func:`apply_superobs`, a documented no-op until
  its consumer lands.
- **Version migration = a NEW ``source_id``, never a mutation** (fork-a
  pin 5).

Time convention (contract-wide): :meth:`AlongTrackSource.load` takes
absolute ``numpy.datetime64`` bounds, half-open ``[t0, t1)``; the returned
``ObsWindow`` carries float days since the SOURCE's declared
:meth:`AlongTrackSource.time_epoch` (dc2021a declares 2017-01-01, so the
gate-2 byte-identity against the legacy input path is representable).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

from sverdrup.core.observations import ObsWindow


@dataclass(frozen=True)
class BBox:
    """Geographic bounding box in degrees; bounds inclusive on all sides.

    The inclusive-both-ends convention matches ``halo_obs`` (the standing
    obs-framing helper) so tile obs selection composes without off-by-one
    seams.
    """

    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float

    def contains(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """Vectorized inclusive membership mask.

        Args:
            lon: Longitudes [degrees], same convention as the source.
            lat: Latitudes [degrees].

        Returns:
            Boolean mask of points inside (inclusive) this box.
        """
        return np.asarray(
            (lon >= self.lon_min)
            & (lon <= self.lon_max)
            & (lat >= self.lat_min)
            & (lat <= self.lat_max)
        )


@dataclass(frozen=True)
class SourceDescriptor:
    """Uniform content-addressed identity of an along-track source.

    ``content_manifest`` is a sorted tuple of ``(relpath, sha256)`` pairs —
    per-file shas ALWAYS (fork-a pin 3; there is deliberately no alternative
    representation in this type). Construction normalizes ordering so two
    descriptors over the same content are equal regardless of input order.
    """

    source_id: str
    dataset_version: str
    content_manifest: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        """Normalize the manifest to canonical sorted-tuple form."""
        canonical = tuple(sorted((str(p), str(h)) for p, h in self.content_manifest))
        object.__setattr__(self, "content_manifest", canonical)

    def manifest_sha(self) -> str:
        """sha256 over the canonical JSON serialization of this descriptor.

        Returns:
            64-char lowercase hex digest; changes when the source id, the
            dataset version, or any file's bytes (via its sha) change.
        """
        payload = json.dumps(
            {
                "source_id": self.source_id,
                "dataset_version": self.dataset_version,
                "content_manifest": [list(e) for e in self.content_manifest],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()


@runtime_checkable
class AlongTrackSource(Protocol):
    """The dual-source loader contract every altimetry adapter implements.

    Adapter census (owner pin 2, plan review 2026-07-22): synthetic +
    CMEMS-MY + dc2021a + JPL-code — every one a REAL adapter through this
    contract, never a test-only bypass.
    """

    def missions(self) -> tuple[str, ...]:
        """Mission codes this source can serve, stable order."""
        ...

    def time_epoch(self) -> np.datetime64:
        """The absolute epoch the returned ObsWindow times count days from."""
        ...

    def load(
        self,
        bbox: BBox,
        t0: np.datetime64,
        t1: np.datetime64,
        missions: Sequence[str] | None = None,
    ) -> ObsWindow:
        """Load obs in ``bbox`` and ``[t0, t1)``, mission-tagged.

        Loading is a pure restriction of the source's canonical obs stream:
        deterministic, order-preserving, and value-preserving (fork-a
        pin 4 — no transform happens here). An unknown mission code raises
        ``ValueError`` (never a silent empty result).
        """
        ...

    def descriptor(self) -> SourceDescriptor:
        """The content-addressed identity of the data this source serves."""
        ...


def apply_superobs(obs: ObsWindow, cfg: object | None = None) -> ObsWindow:
    """Super-observation hook — a documented no-op until its consumer lands.

    Loader-layer transforms are SEPARATE from loading (fork-a pin 4): when a
    super-obs config arrives (a later stage), this step runs after ``load``
    with its cfg serialized into provenance. Until then it returns ``obs``
    unchanged when ``cfg is None`` and refuses loudly otherwise — a silent
    ignore would fake a transform that never ran.

    Args:
        obs: The loaded observation window.
        cfg: Super-obs configuration; None until the consumer stage lands.

    Returns:
        ``obs`` unchanged (cfg is None).

    Raises:
        NotImplementedError: If ``cfg`` is not None — the transform does not
            exist yet; landing it requires the provenance serialization too.
    """
    if cfg is not None:
        raise NotImplementedError(
            "super-obs transform is not implemented yet; it lands with its "
            "consumer stage, cfg serialized into provenance (fork-a pin 4)"
        )
    return obs
