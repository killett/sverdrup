"""Three-way blocked/grouped withholding (spec 5.7). No random point holdout."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sverdrup.core.observations import ObsWindow


@dataclass(frozen=True)
class Split:
    """A train / validation / locked-test partition of observation indices."""

    train_idx: np.ndarray
    validation_idx: np.ndarray
    locked_test_idx: np.ndarray
    id: str


def make_splits(
    obs: ObsWindow,
    *,
    by: str = "mission",
    locked_missions: list[str] | None = None,
    validation_missions: list[str] | None = None,
    block_days: float = 7.0,
    block_deg: float = 2.0,
) -> Split:
    """Partition observations into train/validation/locked-test by group or block.

    Args:
        obs: The observation window.
        by: ``"mission"`` (group by mission) or ``"block"`` (contiguous space-time blocks).
        locked_missions: Missions held out as the locked test set (mission mode).
        validation_missions: Missions held out for validation (mission mode).
        block_days: Temporal block size in days (block mode).
        block_deg: Spatial block size in degrees longitude (block mode).

    Returns:
        A disjoint, total ``Split``.

    Raises:
        ValueError: If ``by`` is ``"random_point"`` or otherwise unsupported, or if
            mission mode is requested without per-obs mission labels.
    """
    if by == "random_point":
        raise ValueError(
            "Random point holdout leaks through spatial autocorrelation (spec 5.7)."
        )
    n = len(obs)
    idx = np.arange(n)
    if by == "mission":
        if obs.mission is None:
            raise ValueError("mission holdout requires per-obs mission labels.")
        locked = np.isin(obs.mission, locked_missions or [])
        val = np.isin(obs.mission, validation_missions or [])
        train = ~(locked | val)
        return Split(
            idx[train], idx[val], idx[locked], id=f"mission:lock={locked_missions}"
        )
    if by == "block":
        coords = obs.coords()
        block = np.floor(coords[:, 0] / block_deg).astype(int) * 1000 + np.floor(
            coords[:, 2] / block_days
        ).astype(int)
        uniq = np.unique(block)
        rng = np.random.default_rng(0)
        rng.shuffle(uniq)
        n_lock = max(1, len(uniq) // 5)
        n_val = max(1, len(uniq) // 5)
        lock_b, val_b = set(uniq[:n_lock]), set(uniq[n_lock : n_lock + n_val])
        locked = np.array([b in lock_b for b in block])
        val = np.array([b in val_b for b in block])
        train = ~(locked | val)
        return Split(idx[train], idx[val], idx[locked], id="block")
    raise ValueError(f"unknown split strategy {by!r}")
