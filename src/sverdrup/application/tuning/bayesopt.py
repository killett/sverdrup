"""Bayesian-optimization SearchStrategy (optuna TPE), added once the simple loop is green."""

from __future__ import annotations

import optuna

from sverdrup.application.tuning.trial import TrialHistory
from sverdrup.core.parameters import ParameterSpace

optuna.logging.set_verbosity(optuna.logging.WARNING)


class BayesianOptimization:
    """Seeded TPE search over a method's ``parameter_space``; minimizes the primary score.

    Drop-in ``SearchStrategy``: the loop, objective, and acceptance are unchanged.
    The surrogate is warm-started each call from the recorded feasible primary
    scores, so the proposals improve as ``history`` accumulates.
    """

    def __init__(self, seed: int, n: int = 8, primary: str = "lambda_x") -> None:
        """Store the seed, batch size ``n``, and the primary score to minimize."""
        self.seed, self.n, self.primary = seed, n, primary

    def propose(
        self, space: ParameterSpace, history: TrialHistory
    ) -> list[dict[str, float]]:
        """Return ``n`` in-bounds parameter dicts from a seeded TPE study.

        Args:
            space: The parameter space whose ``bounds`` define the search box.
            history: Prior trials; feasible-scored records warm-start the surrogate.

        Returns:
            ``n`` parameter dicts over exactly ``space.bounds`` keys, each in-bounds.
        """
        distributions: dict[str, optuna.distributions.BaseDistribution] = {
            k: optuna.distributions.FloatDistribution(lo, hi)
            for k, (lo, hi) in space.bounds.items()
        }
        study = optuna.create_study(
            direction="minimize",
            sampler=optuna.samplers.TPESampler(seed=self.seed),
        )
        # Warm-start the surrogate with the recorded feasible primary scores.
        for rec in history.feasible_scored():
            scores = rec.scores or {}
            if self.primary in scores:
                study.add_trial(
                    optuna.trial.create_trial(
                        params=rec.trial.params,
                        distributions=distributions,
                        value=scores[self.primary],
                    )
                )
        out: list[dict[str, float]] = []
        for _ in range(self.n):
            t = study.ask(distributions)
            out.append({k: float(t.params[k]) for k in space.bounds})
            study.tell(
                t, 0.0
            )  # placeholder; real value supplied by the loop next round
        return out
