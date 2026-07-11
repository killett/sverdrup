"""Capture the Phase-8 factory byte-compat snapshot at the PRE-Task-3 commit.

This script is run ONCE, against a side git worktree checked out at commit
3f88ccb (the last commit before the Task-3 eval-time √s seam, where the shipped
factory applied ``inflation_s`` via the old ``ens.rescaled(self.inflation_s)``
anomaly path).  It records, through the FACTORY (``shipped_miost()``), a small
set of derived σ / mean / covariance probes on a compact fixture config so that
the current (post-seam) factory path can be asserted byte-compatible against it
at rtol 1e-12 (plan Task 4, acceptance criterion 4).

Why a worktree and not an in-tree checkout: the user's standing rule forbids
``git checkout <sha>`` inside the working tree (it has silently restored deleted
files).  We add a detached worktree with ``git worktree add``, import sverdrup
from *that* tree via sys.path, capture, and remove the worktree.

The pre-seam worktree shares this repo's pixi environment (only the source tree
differs), so we run under ``pixi run python`` from /workspace and prepend the
worktree's ``src`` to sys.path so ``import sverdrup`` resolves to the 3f88ccb
sources — NOT the current working tree.

Usage (documented; re-run only if the fixture must be regenerated):

    WT=.../scratchpad/pre-seam
    git worktree add "$WT" 3f88ccb
    pixi run python tests/fixtures/capture_phase8_factory_bytecompat.py "$WT"
    git worktree remove "$WT"

Fixture contents (tests/fixtures/phase8_factory_bytecompat.npz):
    probe_pts   (P, 3)  probe points (lon, lat, day)
    mean        (P,)    mean_at(probe_pts)
    std         (P,)    per-probe marginal std = sqrt(diag(cov(pts, pts)))
    cov_block   (P, P)  one covariance block covariance(probe_pts, probe_pts)
    grid_lon    (nx,)   fixture grid lon (for reference / regen)
    grid_lat    (ny,)   fixture grid lat
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


def _load_presem_sverdrup(worktree: Path) -> None:
    """Prepend the pre-seam worktree's src to sys.path (import from 3f88ccb)."""
    src = worktree / "src"
    if not src.is_dir():
        raise SystemExit(f"worktree src not found: {src}")
    sys.path.insert(0, str(src))


def main(worktree: Path, out: Path) -> None:
    """Capture the byte-compat snapshot through the pre-seam factory."""
    _load_presem_sverdrup(worktree)

    # Confirm we really imported from the worktree, not the current tree.
    import sverdrup as _sv
    from sverdrup.core.grid import GridSpec
    from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
    from sverdrup.core.parameters import ConstantProvider
    from sverdrup.methods.miost import STAGE_B_INFLATION_S, Miost
    from sverdrup.methods.miost_windows import WindowPlan

    assert str(worktree) in _sv.__file__, (
        f"sverdrup imported from {_sv.__file__}, not the pre-seam worktree"
    )

    # Small fixture config: a compact 5×5 grid, a modest obs set, the two-window
    # plan, and a small member count — the byte-compat concern is the s*-scaling
    # path (identical arithmetic regardless of m), so a small m keeps the fixture
    # tiny while exercising the exact factory path (members>0, inflation_s=s*).
    day = 50.0
    root = 12345
    m = 24
    params = ConstantProvider(
        {"spacing_alpha": 1.5, "log10_rho": 1.3, "q_slope": 2.0, "l_t_days": 10.0}
    )
    grid = GridSpec.lonlat(np.linspace(296.0, 304.0, 5), np.linspace(34.0, 42.0, 5))

    rng = np.random.default_rng(7)
    n = 80
    t = rng.uniform(-12.0, 117.0, n)
    err = DiagonalErrorModel(np.full(n, 0.01))
    mission = np.asarray(["alg", "s3a", "h2g", "j2n"])[rng.integers(0, 4, n)]
    obs = ObsWindow.from_arrays(
        rng.uniform(296, 304, n),
        rng.uniform(34, 42, n),
        t,
        rng.standard_normal(n) * 0.1,
        err,
        mission,
    )

    # THROUGH THE FACTORY-equivalent config: shipped_miost() bakes in
    # members=100 / STAGE_B_ROOT; we mirror its ensemble+inflation_s wiring on
    # the compact config here so the current test can reconstruct it identically.
    method = Miost(
        plan=WindowPlan(starts=(0.0, 45.0)),
        members=m,
        member_root=root,
        inflation_s=STAGE_B_INFLATION_S,
    )
    dist = method.solve(obs, grid, params, day)

    # Fixed probe points inside the box (lon, lat, day).
    probe_pts = np.array(
        [
            [298.0, 36.0, day],
            [301.0, 40.0, day],
            [300.0, 38.0, day],
            [297.0, 41.0, day],
            [303.0, 35.0, day],
        ]
    )
    mean = np.asarray(dist.mean_at(probe_pts))
    cov_block = np.asarray(dist.covariance(probe_pts, probe_pts))
    std = np.sqrt(np.diag(cov_block))

    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        out,
        probe_pts=probe_pts,
        mean=mean,
        std=std,
        cov_block=cov_block,
        grid_lon=grid.x,
        grid_lat=grid.y,
        m=m,
        day=day,
        root=root,
        inflation_s=STAGE_B_INFLATION_S,
    )
    # Round-trip verification: the npz loads and the arrays are finite.
    with np.load(out) as z:
        assert z["mean"].shape == (probe_pts.shape[0],)
        assert z["cov_block"].shape == (probe_pts.shape[0], probe_pts.shape[0])
        assert np.all(np.isfinite(z["std"]))
    print(f"captured {out} from {_sv.__file__}")
    print(f"  probe std: {std}")


if __name__ == "__main__":
    wt = Path(sys.argv[1]).resolve()
    dest = Path(__file__).resolve().parent / "phase8_factory_bytecompat.npz"
    main(wt, dest)
