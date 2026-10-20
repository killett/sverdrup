"""One pass-splitting decision, one constant (hygiene P2 #11)."""

from __future__ import annotations

from sverdrup.application import orbit_geometry
from sverdrup.application.calibration import harness
from sverdrup.application.tuning import lane_compare
from sverdrup.methods import miost_error_basis


def test_every_pass_splitter_reads_the_harness_gap() -> None:
    """Every along-track pass splitter uses the harness's gap, not a copy.

    Each site's own comment says it "mirrors harness._PASS_GAP_SEC"; a mirror
    is a second definition that drifts silently. Identity, not equality, is
    the check: a re-pasted ``60.0`` literal is a distinct float object, so a
    copy fails here even while its value still agrees. Bug caught: a site
    re-defining the gap (the state before P2 #11 — three literals).
    """
    assert harness.PASS_GAP_SEC == 60.0  # along-track cadence ~1.08 s
    for module, name in (
        (orbit_geometry, "_GAP_SEC"),
        (lane_compare, "PASS_GAP_SEC"),
        (miost_error_basis, "PASS_GAP_SEC"),
    ):
        assert getattr(module, name) is harness.PASS_GAP_SEC, module.__name__
