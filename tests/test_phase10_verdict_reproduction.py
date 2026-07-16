"""Gate (ii): the Phase-10 PRIMARY verdict reproduced from persisted records.

Loads ``phase10.oi.lanes.verdict`` from the standing evidence store,
reconstructs :class:`BandValues` from its PERSISTED fields (never
recomputes — bands-as-data), and replays the seam-backed adjudication.
The branch AND the pinned wording must reproduce string-equal.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sverdrup.application.tuning.lane_compare import (
    BandValues,
    _lambda_usable,
    adjudicate_primary,
    load_protocol,
    primary_wording,
)

_RESULTS = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
_PROTOCOL = Path("data/2021a_ssh_mapping_ose/ours/phase10_band_artifact.json")


@pytest.mark.skipif(
    not (_RESULTS.exists() and _PROTOCOL.exists()),
    reason="Phase-10 evidence / sealed protocol absent (data/ours/ untracked)",
)
def test_phase10_primary_verdict_reproduced_from_persisted_records() -> None:
    """Bug caught: ANY drift in the seam-backed adjudication semantics vs the
    recorded Phase-10 decision — branch and wording must replay byte-equal
    from the persisted band values."""
    verdict = json.loads(_RESULTS.read_text())["phase10"]["oi"]["lanes"]["verdict"]
    primary = verdict["primary"]

    bv = BandValues(
        delta_mu=float(primary["delta_mu"]),
        delta_lambda_x=float(primary["delta_lambda_x"]),
        band_mu=float(primary["band_mu"]),
        band_lambda_x=float(primary["band_lambda_x"]),
        lambda_informative=bool(primary["lambda_informative"]),
        n_segments=int(primary["n_segments"]),
        n_lambda_used=int(primary["n_lambda_used"]),
        protocol_sha=str(primary["protocol_sha"]),
    )
    protocol = load_protocol(_PROTOCOL, expected_sha=primary["protocol_sha"])
    usable, _note = _lambda_usable(bv, protocol)

    branch, positive = adjudicate_primary(bv, usable)
    assert branch == "within-band"
    assert positive is False
    assert branch == primary["branch"]  # string-equal to the record
    wording = primary_wording(str(primary["a_lane"]), positive, branch)
    assert wording == "improvements within band"
    assert wording == primary["wording"]  # string-equal to the record
