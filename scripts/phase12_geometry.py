"""Phase-12 six-mission orbit-geometry derivation (plan Task 4; spec §4).

The ONE geometry derivation of the phase: j3's FIRST classification happens
here. The Phase-11 RATIO_GAP rider is live — ``classify_orbit`` refusing on
a ratio inside the measured gap TABLES an owner decision and this driver
exits nonzero without writing anything further; Tasks 5/6 must not proceed.

Zero c2: ``build_geometry_artifact`` refuses the id ``"c2"``; the withheld
file is never opened. The five-mission ``phase11_orbit_geometry.json`` is
never touched (new out-path).

The artifact sha belongs under ``phase12.miost6.geometry`` — recorded at the
Task-5 evidence module's first write; until then the printed sha + the
artifact file itself are the durable outputs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sverdrup.application.orbit_geometry import build_geometry_artifact

_OURS = Path("data/2021a_ssh_mapping_ose/ours")
_OBS_DIR = Path("data/2021a_ssh_mapping_ose/dc_obs")
_GEOMETRY = _OURS / "phase12_orbit_geometry_miost6.json"
_MISSIONS = ["alg", "h2g", "j2g", "j2n", "j3", "s3a"]
_PHI0 = 38.1


def main() -> int:
    """Derive the six-mission artifact; print sha + j3 family rows.

    Returns:
        0 on success; 2 when the gap rider tables j3 (owner decision).
    """
    try:
        sha = build_geometry_artifact(_OBS_DIR, _MISSIONS, _PHI0, _GEOMETRY)
    except ValueError as exc:
        if "RATIO_GAP" in str(exc):
            print(f"STOP: j3 classification TABLED for owner — {exc}")
            return 2
        raise
    print(f"[phase12] geometry artifact sha256 {sha} at {_GEOMETRY}")
    art = json.loads(_GEOMETRY.read_text())
    print(f"[phase12] missions: {sorted(art['missions'])}")
    for family, rec in sorted(art["missions"]["j3"].items()):
        print(
            f"[phase12] j3/{family}: orbit_class={rec['orbit_class']} "
            f"classifier_ratio={rec['classifier_ratio']} "
            f"d_perp_km={rec['d_perp_km']} n_clusters={rec['n_clusters']} "
            f"cluster_size_median={rec['cluster_size_median']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
