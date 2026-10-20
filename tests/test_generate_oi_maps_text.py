"""Hygiene P2-#18: the obs-set note stamped into the OI-map audit counts right.

``generate_oi_maps`` printed AND stamped into the audit record "signed
artifact used all 5 mapping missions including j3" — while its own comment
lists six (alg, h2g, j2g, j2n, j3, s3a). Recorded artifacts stand as-is;
the script is fixed for future runs.
"""

from __future__ import annotations

from pathlib import Path

from tests.helpers import load_script

# The signed artifact's obs set, as the script's own comment lists it.
_SIGNED_OBS_SET = {"alg", "h2g", "j2g", "j2n", "j3", "s3a"}


def test_the_stamped_obs_set_note_counts_every_mapping_mission() -> None:
    """Bug caught: a hard-coded "5" (the TRAIN-only count) describing the
    all-mission set — six with j3."""
    mod = load_script("generate_oi_maps")
    assert f"all {len(_SIGNED_OBS_SET)} mapping missions" in mod.OBS_SET_NOTE
    source = (
        Path(__file__).resolve().parents[1] / "scripts" / "generate_oi_maps.py"
    ).read_text()
    assert "all-5-missions" not in source
    assert "all 5 mapping missions" not in source
