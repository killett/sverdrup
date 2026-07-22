"""Sealed instrument configs (phase-14 Task 11, 0a-5).

The config set the Task-19 seal ingests: byte-deterministic serialization,
doc↔code equality on the seam thresholds, and identity with the Task-9
sealed null objects.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from sverdrup.eval.insitu import InSituNullConfig
from sverdrup.validation.phase14_instruments import (
    SEAM_CLEAN_MAX,
    SEAM_ELEVATED_MAX,
    instrument_configs,
    serialize_instrument_configs,
)

_RUBRIC = Path(__file__).resolve().parents[1] / (
    "docs/validation/phase14_seam_rubric.md"
)


def test_doc_code_threshold_equality() -> None:
    """The rubric doc's thresholds equal the constants — comment AND prose.

    Catches the classic drift: someone edits the doc (or the module) and
    the two verdict sources diverge silently. The prose pins keep the
    machine-readable comment from going vacuous against body edits.
    """
    text = _RUBRIC.read_text()
    m = re.search(
        r"<!-- thresholds: clean_max=([\d.]+) elevated_max=([\d.]+) -->", text
    )
    assert m, "rubric doc lost its machine-readable threshold comment"
    assert float(m.group(1)) == SEAM_CLEAN_MAX
    assert float(m.group(2)) == SEAM_ELEVATED_MAX
    # prose verdict cells carry the same numbers
    assert f"**CLEAN:** `R_seam ≤ {SEAM_CLEAN_MAX}`" in text
    assert f"{SEAM_CLEAN_MAX} < R_seam ≤ {SEAM_ELEVATED_MAX}`" in text
    assert f"**STRUCTURAL-STOP:** `R_seam > {SEAM_ELEVATED_MAX}`" in text


def test_config_carries_all_four_instrument_families() -> None:
    """GroundTrack, SpectralFidelity, seam, in-situ nulls — all present."""
    cfg = instrument_configs()
    assert cfg["groundtrack"]["constellation_aware"] is True
    assert cfg["groundtrack"]["geometry_artifact_keyed"] is True
    assert cfg["spectral_fidelity"]["band"] == "tile-extent"
    assert cfg["seam"]["clean_max"] == SEAM_CLEAN_MAX
    assert cfg["seam"]["elevated_max"] == SEAM_ELEVATED_MAX
    nulls = cfg["insitu_nulls"]
    sealed = InSituNullConfig()
    assert nulls["climo_smooth_days"] == sealed.climo_smooth_days
    assert nulls["persist_lag_days"] == sealed.persist_lag_days


def test_serialization_byte_deterministic() -> None:
    """Two serializations are byte-identical (the seal substrate)."""
    a = serialize_instrument_configs()
    b = serialize_instrument_configs()
    assert a == b
    assert isinstance(a, bytes)
    assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest()


def test_serialization_tracks_config_content() -> None:
    """The bytes change when any config number changes (no stale cache)."""
    base = serialize_instrument_configs()
    mutated = dict(instrument_configs())
    mutated["seam"] = dict(mutated["seam"], clean_max=999.0)
    assert serialize_instrument_configs(mutated) != base
