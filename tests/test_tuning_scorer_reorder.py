"""mu_score-before-λx reorder: λx is computed only for trials that clear the µ bar.

λx is the expensive, fragile metric (it raises UnresolvedScaleError on a degenerate
map). A trial below the BASELINE µ bar is inadmissible regardless of λx (the objective
filters on µ before ranking on λx), so the scorer skips λx for it — avoiding wasted
work AND keeping a 'GMRF maps but under-resolves' trial legible (it reports its real
mu_score instead of vanishing into a feasible-but-unscorable UnresolvedScaleError).
"""

from __future__ import annotations

import numpy as np

from sverdrup.application.tuning.scorer import _assemble_scores


class _SpyLambdaX:
    """Records calls; stands in for the expensive effective_resolution_lambda_x."""

    def __init__(self, value: float) -> None:
        self.value, self.calls = value, 0

    def __call__(self, *args: object, **kwargs: object) -> float:
        self.calls += 1
        return self.value


def _arrays(predicted: list[float]) -> dict[str, np.ndarray]:
    """Synthetic along-track arrays; observed=[1,2,3,4], var=1 (so σ=1)."""
    return dict(
        ssh_a=np.array([1.0, 2.0, 3.0, 4.0]),
        mean_interp=np.array(predicted),
        var_interp=np.ones(4),
        time_a=np.arange(4.0),
        lat_a=np.zeros(4),
        lon_a=np.arange(4.0),
    )


def test_sub_bar_mu_skips_lambda_x() -> None:
    # predicted=zeros -> rms_resid==rms_signal -> mu_score=0.0 (< 0.85 bar).
    spy = _SpyLambdaX(142.0)
    scores = _assemble_scores(
        **_arrays([0.0, 0.0, 0.0, 0.0]), mu_bar=0.85, lambda_x_fn=spy
    )
    assert scores["mu_score"] == 0.0
    assert "lambda_x" not in scores  # skipped: inadmissible regardless of λx
    assert spy.calls == 0  # the expensive/fragile metric was never touched
    # coverage: |truth-0|<=1 only for truth=1 -> 1/4.
    assert scores["coverage_1sigma"] == 0.25


def test_above_bar_mu_computes_lambda_x() -> None:
    # predicted==observed -> mu_score=1.0 (>= 0.85 bar) -> λx is needed for ranking.
    spy = _SpyLambdaX(142.0)
    scores = _assemble_scores(
        **_arrays([1.0, 2.0, 3.0, 4.0]), mu_bar=0.85, lambda_x_fn=spy
    )
    assert scores["mu_score"] == 1.0
    assert scores["lambda_x"] == 142.0
    assert spy.calls == 1
    assert scores["coverage_1sigma"] == 1.0  # exact match -> all within 1σ


def test_at_bar_is_inclusive() -> None:
    # mu_score == mu_bar must compute λx: the objective admits with ">=", so a strict
    # ">" here would drop a trial sitting exactly on the BASELINE floor.
    spy = _SpyLambdaX(99.0)
    scores = _assemble_scores(
        **_arrays([1.0, 2.0, 3.0, 4.0]), mu_bar=1.0, lambda_x_fn=spy
    )
    assert scores["mu_score"] == 1.0
    assert scores["lambda_x"] == 99.0
    assert spy.calls == 1
