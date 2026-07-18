"""Phase-12 scope config: declared mission roles for the six-mission product.

val_track_path is REQUIRED and must be null: this product has no validation
track (j3 assimilated). Missing key = schema error; null = the declared
production state (spec §2, kernel=None precedent).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REQUIRED_KEYS = frozenset(
    {
        "mapping_obs_paths",
        "val_track_path",
        "validation_mission",
        "no_validation_reason",
        "c2_track_path",
        "mdt_paths",
        "time_min",
        "time_max",
        "smoke_days",
        "mean_map_out",
        "var_map_out",
        "member_store_out",
        "window_id",
    }
)
MIOST6_MISSIONS = frozenset({"alg", "h2g", "j2g", "j2n", "j3", "s3a"})
NO_VALIDATION_REFUSAL = (
    "REFUSED: this product has no validation track "
    "(no_validation_reason='j3-assimilated') — j3 is assimilated; no quantity "
    "can be refit without a leak"
)


class Phase12ConfigError(ValueError):
    """Schema violation in the phase12 scope cfg."""


@dataclass(frozen=True)
class Phase12Scope:
    """Validated six-mission scope (roles declared, validation declared absent)."""

    mapping_obs_paths: tuple[Path, ...]
    c2_track_path: Path
    mdt_paths: tuple[Path, ...]
    time_min: str
    time_max: str
    smoke_days: tuple[float, ...]
    mean_map_out: Path
    var_map_out: Path
    member_store_out: Path
    window_id: str
    no_validation_reason: str


def load_phase12_scope(path: Path | str) -> Phase12Scope:
    """Load + schema-validate; missing keys and non-null validation roles refuse.

    Args:
        path: The phase12 scope JSON path.

    Returns:
        The validated :class:`Phase12Scope`.

    Raises:
        Phase12ConfigError: On missing required keys, a non-null validation
            role, a wrong ``no_validation_reason``, or a mission set that is
            not exactly the six assimilated missions.
        ValueError: From ``_mission_code`` on a c2 or unknown mapping path
            (the withheld-leak guard).
    """
    from sverdrup.validation.input_adapter import _mission_code

    raw = json.loads(Path(path).read_text())
    missing = sorted(REQUIRED_KEYS - set(raw))
    if missing:
        raise Phase12ConfigError(f"phase12 scope missing required keys: {missing}")
    if raw["val_track_path"] is not None or raw["validation_mission"] is not None:
        raise Phase12ConfigError(NO_VALIDATION_REFUSAL)
    if raw["no_validation_reason"] != "j3-assimilated":
        raise Phase12ConfigError(
            "no_validation_reason must be 'j3-assimilated' (the declared state)"
        )
    paths = [Path(p) for p in raw["mapping_obs_paths"]]
    codes = {_mission_code(p) for p in paths}  # raises on c2/unknown
    if codes != MIOST6_MISSIONS:
        raise Phase12ConfigError(
            f"mapping missions {sorted(codes)} != {sorted(MIOST6_MISSIONS)}"
        )
    return Phase12Scope(
        mapping_obs_paths=tuple(paths),
        c2_track_path=Path(raw["c2_track_path"]),
        mdt_paths=tuple(Path(p) for p in raw["mdt_paths"]),
        time_min=raw["time_min"],
        time_max=raw["time_max"],
        smoke_days=tuple(float(d) for d in raw["smoke_days"]),
        mean_map_out=Path(raw["mean_map_out"]),
        var_map_out=Path(raw["var_map_out"]),
        member_store_out=Path(raw["member_store_out"]),
        window_id=str(raw["window_id"]),
        no_validation_reason=raw["no_validation_reason"],
    )


def require_validation_track(scope: Phase12Scope) -> None:
    """Every validation-flavored entry point refuses here with the declared reason.

    Args:
        scope: The validated phase12 scope (unused beyond its declared state —
            this product NEVER has a validation track).

    Raises:
        Phase12ConfigError: Always, with the pinned ``NO_VALIDATION_REFUSAL``.
    """
    raise Phase12ConfigError(NO_VALIDATION_REFUSAL)
