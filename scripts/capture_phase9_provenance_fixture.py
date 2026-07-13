"""Capture the Phase-9 provenance-sequence fixture at the PRE-Task-3 commit.

This script is run ONCE before any Task-3 migration edits; it records the
transform sequence of the shipped product so that the PIN-D test can assert
wrapper-built products reproduce the exact same sequence.

PIN D — PROVENANCE SINGLE-APPEND: the raw ensemble stops appending inflation
transforms after Task 3; the wrapper appends once.  This fixture proves the
pre-migration sequence so the post-migration sequence can be asserted equal.

Usage (run from /workspace before touching migration files):

    pixi run python scripts/capture_phase9_provenance_fixture.py

Output:
    tests/fixtures/phase9_provenance_sequence.json

Fixture contents:
    A JSON array where each element is:
        {"kind": <TransformKind.name>, "params_keys": [<sorted param keys>]}
    representing the full transform chain of
    shipped_product.provenance.transforms at the small test-fixture config.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure we import from /workspace/src, not a side worktree.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np


def main() -> None:
    """Capture the provenance-sequence fixture and write to tests/fixtures/."""
    from sverdrup.core.grid import GridSpec
    from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
    from sverdrup.core.parameters import ConstantProvider
    from sverdrup.distributions.calibration import ClipSpec, PolyCalibration
    from sverdrup.methods.miost import (
        PHASE8_CLIP_HI,
        PHASE8_CLIP_LO,
        PHASE8_FIT_ID,
        PHASE8_POLY_COEFFS,
        STAGE_B_ROOT,
        Miost,
    )
    from sverdrup.methods.miost_windows import WindowPlan

    # -----------------------------------------------------------------------
    # Fixture config — identical to test_phase8_identity_regression.py so the
    # PIN-D test runs on the same geometry as the identity gate.
    # -----------------------------------------------------------------------
    _M = 6
    _DAY = 50.0
    _PARAMS = ConstantProvider(
        {"spacing_alpha": 1.5, "log10_rho": 1.3, "q_slope": 2.0, "l_t_days": 10.0}
    )
    _GRID = GridSpec.lonlat(np.linspace(296.0, 304.0, 7), np.linspace(34.0, 42.0, 7))

    def _obs(n: int = 80) -> ObsWindow:
        rng = np.random.default_rng(7)
        t = rng.uniform(-12.0, 117.0, n)
        err = DiagonalErrorModel(np.full(n, 0.01))
        mission = np.asarray(["alg", "s3a", "h2g", "j2n"])[rng.integers(0, 4, n)]
        return ObsWindow.from_arrays(
            rng.uniform(296, 304, n),
            rng.uniform(34, 42, n),
            t,
            rng.standard_normal(n) * 0.1,
            err,
            mission,
        )

    # -----------------------------------------------------------------------
    # Build the shipped product (same calibration as shipped_miost() but
    # with the small fixture's member count so it runs fast).
    # -----------------------------------------------------------------------
    ship = Miost(
        plan=WindowPlan(starts=(0.0, 45.0)),
        members=_M,
        member_root=STAGE_B_ROOT,
        calibration=PolyCalibration(
            coeffs=PHASE8_POLY_COEFFS,
            clip=ClipSpec(lo_log_s=PHASE8_CLIP_LO, hi_log_s=PHASE8_CLIP_HI),
            fit_id=PHASE8_FIT_ID,
        ),
    )
    product = ship.solve(_obs(), _GRID, _PARAMS, _DAY)

    # -----------------------------------------------------------------------
    # Serialise the transform chain.
    # -----------------------------------------------------------------------
    sequence = [
        {"kind": tr.kind.name, "params_keys": sorted(tr.params.keys())}
        for tr in product.provenance.transformations
    ]

    out = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "phase9_provenance_sequence.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sequence, indent=2) + "\n")

    print(f"Written: {out}")
    print(f"Sequence ({len(sequence)} transforms):")
    for item in sequence:
        print(f"  {item}")


if __name__ == "__main__":
    main()
