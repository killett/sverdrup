"""The phase-13 R parameterization (spec §4): per-mission σ² + mode priors.

One responsibility: RSpec — the structured observation-error specification.
σ²_m = R_REF · exp(δ_m) with the gauge fixed by mean(δ) = 0 over the five
fit missions: the engine sweeps δ_{alg, h2g, j2g, j2n} and δ_s3a is DERIVED
as −Σ of the four (balance mission — never an input). Mode priors are the
shared {Λ_bias, Λ_tilt} pair in log10 m²; both set = modes active, both
None = modes structurally COLUMN-ABSENT (spec §2 rider 3 — never Λ = 0).

Cache lineage (spec §2 rider 5 / §11): ``key()`` returns the params_key
fragment. The scalar configuration returns "" so scalar-era keys are
byte-identical (cached scalar solves stay valid); any structured config
gets a NEW fragment carrying the structure kind, all five δ (including the
derived s3a), both Λ, the basis id and the segmentation version.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from sverdrup.eval.phase11_constants import DERIVATION_VERSION
from sverdrup.methods.miost_basis import R_REF
from sverdrup.methods.miost_error_basis import PASS_GAP_SEC, mission_hash_ints

SWEPT_MISSIONS = ("alg", "h2g", "j2g", "j2n")
BALANCE_MISSION = "s3a"
FIT_MISSIONS = (*SWEPT_MISSIONS, BALANCE_MISSION)

# Basis id (spec §11): {P0, P1} per pass in s-units, geometry-artifact
# segmentation (version + gap rule pinned into the key).
_BASIS_ID = "P0P1-s"
_SEG_VERSION = f"v{DERIVATION_VERSION}g{PASS_GAP_SEC:g}"


@dataclass(frozen=True)
class RSpec:
    """Structured observation-error spec: δ contrasts + shared mode priors.

    Attributes:
        deltas: EXACTLY the four swept missions' log-variance contrasts
            (``{}`` = the scalar configuration). ``s3a`` is never a key.
        log_lam_bias: log10 bias-mode prior variance [m²], or None.
        log_lam_tilt: log10 tilt-mode prior variance [m²], or None.
            Both set = modes active; both None = modes column-absent.
    """

    deltas: dict[str, float] = field(default_factory=dict)
    log_lam_bias: float | None = None
    log_lam_tilt: float | None = None

    def __post_init__(self) -> None:
        """Validate the contrast chart and the mode-pair completeness.

        Raises:
            ValueError: If ``s3a`` appears as an input, the swept keys are
                not exactly the four, or only one Λ is set.
        """
        if self.deltas:
            if BALANCE_MISSION in self.deltas:
                raise ValueError(
                    "delta_s3a is DERIVED (= -sum of the four swept contrasts) "
                    "— s3a must never be an input (spec §4 contrast chart)"
                )
            if set(self.deltas) != set(SWEPT_MISSIONS):
                missing = sorted(set(SWEPT_MISSIONS) - set(self.deltas))
                extra = sorted(set(self.deltas) - set(SWEPT_MISSIONS))
                raise ValueError(
                    f"deltas must carry exactly {SWEPT_MISSIONS}; "
                    f"missing {missing}, unexpected {extra}"
                )
        if (self.log_lam_bias is None) != (self.log_lam_tilt is None):
            raise ValueError(
                "log_lam_bias and log_lam_tilt must be both set (modes "
                "active) or both None (modes column-absent) — a half-set "
                "mode block is neither"
            )

    @property
    def modes_active(self) -> bool:
        """True when the {bias, tilt} mode columns are present."""
        return self.log_lam_bias is not None

    @property
    def is_scalar(self) -> bool:
        """True for the scalar-era configuration (empty deltas, no modes)."""
        return not self.deltas and not self.modes_active

    @property
    def delta_s3a(self) -> float:
        """The DERIVED balance contrast: −Σ of the four swept δ."""
        return -sum(self.deltas.values()) if self.deltas else 0.0

    @property
    def all_deltas(self) -> dict[str, float]:
        """All five δ (including the derived s3a), fit-mission order."""
        base = {m: self.deltas.get(m, 0.0) for m in SWEPT_MISSIONS}
        return {**base, BALANCE_MISSION: self.delta_s3a}

    @property
    def lam_bias(self) -> float:
        """Bias-mode prior variance Λ_bias [m²] (modes must be active)."""
        if self.log_lam_bias is None:
            raise ValueError("modes are column-absent: no lam_bias exists")
        return float(10.0**self.log_lam_bias)

    @property
    def lam_tilt(self) -> float:
        """Tilt-mode prior variance Λ_tilt [m²] (modes must be active)."""
        if self.log_lam_tilt is None:
            raise ValueError("modes are column-absent: no lam_tilt exists")
        return float(10.0**self.log_lam_tilt)

    @property
    def structure_kind(self) -> str:
        """Provenance kind: scalar | per-mission | per-mission+modes (§11)."""
        if self.modes_active:
            return "per-mission+modes"
        return "per-mission" if self.deltas else "scalar"

    def sigma2_for(self, mission_hash: np.ndarray) -> np.ndarray:
        """Per-obs error variances by MISSION IDENTITY (never positional).

        σ²_m = R_REF · exp(δ_m), looked up through the blake2b-4 mission
        hashes (the ``_obs_identity`` convention). exp(0) == 1.0 exactly,
        so the scalar/zero configuration returns R_REF bit-equal.

        Args:
            mission_hash: (n,) int64 mission hashes (``mission_hash_ints``).

        Returns:
            (n,) float64 per-obs variances.

        Raises:
            ValueError: On any hash outside the five fit missions (the
                j3/c2 leak class refuses instead of defaulting).
        """
        table = dict(
            zip(
                mission_hash_ints(np.asarray(FIT_MISSIONS)).tolist(),
                [R_REF * np.exp(d) for d in self.all_deltas.values()],
                strict=True,
            )
        )
        mh = np.asarray(mission_hash, dtype=np.int64)
        out = np.empty(mh.size, dtype=float)
        for i, h in enumerate(mh.tolist()):
            if h not in table:
                raise ValueError(
                    f"unknown mission hash {h} — not one of the five fit "
                    f"missions {FIT_MISSIONS}; refusing a silent R_REF default"
                )
            out[i] = table[h]
        return out

    def key(self) -> str:
        """The params_key fragment (seam f); "" for the scalar config.

        Returns:
            "" when scalar (byte-identical scalar-era keys — cache
            lineage), else a fragment carrying kind, all five δ, both Λ,
            basis id and segmentation version (spec §11).
        """
        if self.is_scalar:
            return ""
        d = ",".join(f"{m}={v!r}" for m, v in self.all_deltas.items())
        return (
            f";rspec=kind={self.structure_kind};deltas={d};"
            f"lam=({self.log_lam_bias!r},{self.log_lam_tilt!r});"
            f"basis={_BASIS_ID};seg={_SEG_VERSION}"
        )
