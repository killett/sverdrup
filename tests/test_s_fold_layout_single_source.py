"""One S-fold layout draw: ``harness.draw_s_layout`` is ``folds.s_fold_layout`` (hygiene #8)."""

from __future__ import annotations

import numpy as np
import pytest

from sverdrup.application.calibration import folds as F
from sverdrup.application.calibration.constants import S_FOLD_SEED_ARGS
from sverdrup.application.calibration.harness import Track, draw_s_layout

_OI_TUPLE = ("oi", "phase9", "s-folds")


def _one_point_per_block_track() -> Track:
    """25 points, one per block centroid, one label: every layout keeps 18/25 on the fit side."""
    lon, lat = (
        np.array(v)
        for v in zip(*(F._block_centroid(b) for b in range(25)), strict=True)
    )
    n = lon.size
    z = np.zeros(n)
    return Track(
        z,
        lon,
        lat,
        z,
        np.ones(n),
        np.full(n, "01"),
        np.zeros(n, dtype=int),
        np.full(n, "a"),
        np.zeros(n, dtype=bool),
    )


def test_phase8_tuple_draws_the_folds_layout_at_salt_zero() -> None:
    """Bug caught: the two copies drifting (sizes, slicing or seed args), so the
    harness's MIOST layout stops reproducing the Phase-8 evidence while the
    folds tests stay green."""
    trk = _one_point_per_block_track()
    assert draw_s_layout(trk, S_FOLD_SEED_ARGS) == (F.s_fold_layout(0), 0, [])


def test_redraws_until_the_partition_holds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bug caught: the salt not threaded into the seed (every redraw identical),
    or the accepted salt / redraw list recorded off by one."""
    verdicts = iter([False, False, True])
    monkeypatch.setattr(F, "layout_respects_partition", lambda *_a: next(verdicts))
    layout, salt, redraws = draw_s_layout(
        _one_point_per_block_track(), S_FOLD_SEED_ARGS
    )
    assert (salt, redraws) == (2, [0, 1])
    assert layout == F.s_fold_layout(2)
    assert layout != F.s_fold_layout(0)


def test_a_different_tuple_is_a_different_seed_lineage() -> None:
    """Bug caught: the tuple dropped from the seed (OI silently reusing MIOST's
    folds), or the harness keeping a private draw that folds cannot reproduce."""
    layout, salt, _ = draw_s_layout(_one_point_per_block_track(), _OI_TUPLE)
    assert salt == 0
    assert layout != F.s_fold_layout(0)
    assert layout == F.s_fold_layout(0, seed_args=_OI_TUPLE)
