"""PCG checkpoint/resume tests (phase-13 operational hardening).

The external identity runs were OOM-killed ~hourly by cgroup pressure
(three recorded ``oom_kill`` events); a 45-minute joint member batch that
cannot be chunked (per-column iterates depend on the batch's slowest
column) needs mid-solve durability instead. PCG state is exactly
``(x, r, z, p, rz, iters, it)``; persisting and restoring it bit-exactly
must reproduce the uninterrupted solve BIT-FOR-BIT — anything less would
change signed-product reconstructions.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sverdrup.methods.miost_basis import BasisSpec, DiagonalQ, build_g
from sverdrup.methods.miost_solver import MiostSolver, rhs_from_obs

SPEC = BasisSpec(alpha=1.5, l_t_days=10.0, ladder=(320.0, 452.548))
RNG = np.random.default_rng(11)


def _small_system() -> tuple[MiostSolver, np.ndarray]:
    els = SPEC.elements_for_window(0.0)
    n = 50
    lon = RNG.uniform(296, 304, n)
    lat = RNG.uniform(34, 42, n)
    t = RNG.uniform(10, 50, n)
    y = RNG.standard_normal(n) * 0.1
    r = np.full(n, 0.01)
    q = DiagonalQ(rho=20.0, q_slope=2.0).variances_for(els)
    g = build_g(SPEC, els, lon, lat, t)
    solver = MiostSolver(g, r_diag=r, q_diag=q, pcg_rtol=1e-10, pcg_maxiter=2000)
    b = np.column_stack([rhs_from_obs(g, r, y), rhs_from_obs(g, r, y * 0.5)])
    return solver, b


def test_checkpointing_does_not_perturb_the_solve(tmp_path: Path) -> None:
    # Bug caught: any checkpoint bookkeeping (extra copies, dtype round
    # trips) leaking into the iteration arithmetic — the solve with
    # checkpointing enabled must be BIT-identical to the plain solve.
    solver, b = _small_system()
    x_plain, rep_plain = solver.solve(b)
    x_ck, rep_ck = solver.solve(b, checkpoint=tmp_path / "ck.npz", checkpoint_every=7)
    assert np.array_equal(x_plain, x_ck)
    assert np.array_equal(rep_plain.iterations, rep_ck.iterations)
    assert np.array_equal(rep_plain.final_rel_residual, rep_ck.final_rel_residual)


def test_resume_reproduces_uninterrupted_solve_bit_for_bit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Bug caught: incomplete state capture (rz or the iteration counter
    # missing) — a resumed solve would take a different Krylov path and
    # differ at ~rtol level, silently breaking signed-product identity.
    solver, b = _small_system()
    x_plain, rep_plain = solver.solve(b)

    ck = tmp_path / "ck.npz"

    class _Abort(RuntimeError):
        pass

    # interrupt the first run right after a checkpoint write
    from typing import Any

    orig_savez = np.savez
    calls = {"n": 0}

    def _savez_then_abort(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        orig_savez(*args, **kwargs)
        calls["n"] += 1
        if calls["n"] == 3:  # let a few checkpoints land, then die mid-solve
            raise _Abort

    with monkeypatch.context() as mp:
        mp.setattr(np, "savez", _savez_then_abort)
        with pytest.raises(_Abort):
            solver.solve(b, checkpoint=ck, checkpoint_every=5)
    assert ck.exists()

    # resume from the surviving checkpoint: must finish bit-identical
    x_res, rep_res = solver.solve(b, checkpoint=ck, checkpoint_every=5)
    assert np.array_equal(x_plain, x_res)
    assert np.array_equal(rep_plain.iterations, rep_res.iterations)
    assert np.array_equal(rep_plain.final_rel_residual, rep_res.final_rel_residual)
    # the checkpoint file is cleaned up after a completed solve
    assert not ck.exists()


def test_checkpoint_of_mismatched_system_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Bug caught: a stale checkpoint from a DIFFERENT system (other rhs or
    # geometry) silently resumed — the solve would converge to the wrong
    # solution while reporting convergence.
    solver, b = _small_system()
    ck = tmp_path / "ck.npz"

    class _Abort(RuntimeError):
        pass

    from typing import Any

    orig = np.savez
    calls = {"n": 0}

    def _abort_soon(*args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        orig(*args, **kwargs)
        calls["n"] += 1
        if calls["n"] == 1:
            raise _Abort

    with monkeypatch.context() as mp:
        mp.setattr(np, "savez", _abort_soon)
        with pytest.raises(_Abort):
            solver.solve(b, checkpoint=ck, checkpoint_every=5)

    with pytest.raises(ValueError, match="checkpoint"):
        solver.solve(b * 2.0, checkpoint=ck, checkpoint_every=5)
