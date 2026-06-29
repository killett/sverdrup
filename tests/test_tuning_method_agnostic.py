"""The tuner bakes in no method-specific parameter shape (test 3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sverdrup.application.tuning.feasibility import CoherenceFeasibility, TileGeometry
from sverdrup.application.tuning.loop import tune
from sverdrup.application.tuning.objective import ConstrainedObjective
from sverdrup.application.tuning.strategy import SobolSearch
from sverdrup.core.method import Method
from sverdrup.core.types import UncertaintyCapability as UC
from sverdrup.methods.gmrf import MaternGMRF
from sverdrup.methods.oi import OptimalInterpolation


def test_no_oi_param_names_in_tuning_package() -> None:
    # Bug it catches: OI's length_scale/time_scale hard-coded into the search/objective.
    root = Path("src/sverdrup/application/tuning")
    blob = "\n".join(p.read_text() for p in root.glob("*.py"))
    assert "length_scale" not in blob
    assert "time_scale" not in blob


class _FakeScorer:
    def score(
        self,
        method_name: str,
        params: dict[str, float],
        split: object,
        seed: int,
        window: object,
    ) -> dict[str, float]:
        return {"lambda_x": 150.0, "mu_score": 0.86, "coverage_1sigma": 0.68}


@pytest.mark.parametrize("method", [OptimalInterpolation(), MaternGMRF()])
def test_same_loop_drives_both_methods(method: Method) -> None:
    name = "oi" if isinstance(method, OptimalInterpolation) else "gmrf"
    res = tune(
        method_name=name,
        space=method.parameter_space(),
        strategy=SobolSearch(seed=1, n=4),
        predicate=CoherenceFeasibility(),
        objective=ConstrainedObjective(),
        scorer=_FakeScorer(),
        split=type("S", (), {"id": "s"})(),
        seed=1,
        window=type("W", (), {"id": "w"})(),
        tile_geometry=TileGeometry(1e9, 1.0, "single"),
        required_capabilities=frozenset({UC.POINT}),
        rounds=1,
    )
    assert res.winner is not None
