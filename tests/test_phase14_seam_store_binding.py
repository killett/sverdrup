"""Hygiene: a seam leg resumes ONLY from a member store of its own solve.

``_seam_tile_leg`` adopted ``SEAM_MEMBER_STORE[tile]`` whenever it existed,
whatever m / PCG cap / CRN root produced it, then recorded the CURRENT
arguments as the leg's provenance — a store from an m=4 debugging run would
be scored, and labelled, as an m=100 production leg. The resume read is now
``_load_seam_store``, which refuses a mismatched binding.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tests.helpers import load_script

_mod = load_script("phase14_stage1_run")


def _write(path: Path, *, m: int, binding: dict[str, object] | None) -> None:
    payload = _mod._store_payload(
        {"w0": np.zeros(3)},
        {"w0": np.zeros((3, m))},
        {"w0": 0.0},
        [{"window": "w0", "iterations": 5, "final_rel_residual": 1e-8}],
        12.5,
        "test store",
        binding=binding,
    )
    np.savez(path, **payload)


_BOUND = {"m": 4, "maxiter": 500, "root": "7"}


@pytest.mark.parametrize(("field", "value"), [("m", 5), ("maxiter", 501), ("root", 8)])
def test_a_store_from_another_solve_is_refused(
    tmp_path: Path, field: str, value: int
) -> None:
    """Bug caught: resume adopting a store solved under a different m / PCG
    cap / CRN root and recording the current arguments as its provenance."""
    store = tmp_path / "seam_n_members.npz"
    _write(store, m=4, binding=dict(_BOUND))
    want = {"m": 4, "maxiter": 500, "root": 7}
    want[field] = value
    with pytest.raises(RuntimeError, match=f"differs: {field}"):
        _mod._load_seam_store(store, **want)


def test_a_store_of_this_solve_resumes(tmp_path: Path) -> None:
    """Bug caught: a binding check that refuses the store it should resume."""
    store = tmp_path / "seam_n_members.npz"
    _write(store, m=4, binding=dict(_BOUND))
    etas_a, anoms, starts, pcg_rows, wall, unverified = _mod._load_seam_store(
        store, m=4, maxiter=500, root=7
    )
    assert list(anoms) == ["w0"] and anoms["w0"].shape == (3, 4)
    assert starts == {"w0": 0.0} and wall == 12.5
    assert pcg_rows[0]["iterations"] == 5
    assert unverified == []


def test_a_legacy_store_is_checked_on_m_and_says_what_it_cannot_verify(
    tmp_path: Path,
) -> None:
    """A store written before the binding existed: m is still checkable
    from the anomaly shape (refused when wrong); maxiter and root are not,
    and the loader SAYS so rather than vouching for them."""
    store = tmp_path / "seam_n_members.npz"
    _write(store, m=4, binding=None)
    with pytest.raises(RuntimeError, match="asks m=5"):
        _mod._load_seam_store(store, m=5, maxiter=500, root=7)
    *_, unverified = _mod._load_seam_store(store, m=4, maxiter=500, root=7)
    assert unverified == ["maxiter", "root"]
    with np.load(store) as z:
        assert "binding" not in z.files
    assert json.dumps(unverified)  # recordable as-is
