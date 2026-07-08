"""Capability-derived bars + capability-routed scorer (folds 1 + B; fail-loud POINT)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sverdrup.application.tuning import scorer as scorer_mod
from sverdrup.application.tuning.objective import bars_for
from sverdrup.application.tuning.scorer import ValidationTrackScorer, _assemble_scores
from sverdrup.core.types import UncertaintyCapability as UC


def test_bars_for_point_omits_coverage() -> None:
    bars = bars_for(UC.POINT)
    assert [b.metric for b in bars] == ["mu_score"]


def test_bars_for_marginal_and_up_include_coverage() -> None:
    for cap in (UC.MARGINAL_VARIANCE, UC.COVARIANCE, UC.SAMPLES):
        metrics = [b.metric for b in bars_for(cap)]
        assert "coverage_1sigma" in metrics and "mu_score" in metrics


def test_assemble_scores_var_optional() -> None:
    """var_interp=None -> no coverage key; mu present (and lambda_x above the bar)."""
    n = 64
    rng = np.random.default_rng(0)
    ssh = rng.standard_normal(n)
    s = _assemble_scores(
        ssh_a=ssh,
        mean_interp=ssh + 1e-6 * rng.standard_normal(n),
        var_interp=None,
        time_a=np.arange(n),
        lat_a=np.full(n, 38.0),
        lon_a=np.linspace(295, 305, n),
        mu_bar=1.1,  # keep lambda_x (fragile on synthetic data) out of this test
    )
    assert "coverage_1sigma" not in s and "mu_score" in s


def _scorer(tmp_path: Path) -> ValidationTrackScorer:
    return ValidationTrackScorer(
        train_obs=None,  # type: ignore[arg-type]  # runners are monkeypatched
        grid=None,  # type: ignore[arg-type]
        output_days=[0.0],
        temporal_half_window_days=425.0,
        val_track_path=tmp_path / "track.nc",
        lon_min=295.0,
        lon_max=305.0,
        lat_min=33.0,
        lat_max=43.0,
        time_min="2017-01-01",
        time_max="2017-12-31",
    )


class _PointStub:
    native_capability = UC.POINT


class _SamplesStub:
    native_capability = UC.SAMPLES


def test_scorer_routes_point_mean_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """POINT -> run_challenge_map (mean-only, var path None); >=MARGINAL -> run_mean_var_maps."""
    from sverdrup.methods.registry import METHODS

    calls: list[str] = []
    monkeypatch.setitem(METHODS, "pointstub", _PointStub)
    monkeypatch.setitem(METHODS, "samplesstub", _SamplesStub)
    monkeypatch.setattr(
        scorer_mod,
        "run_challenge_map",
        lambda *a, **k: calls.append("mean-only"),
    )
    monkeypatch.setattr(
        scorer_mod,
        "run_mean_var_maps",
        lambda *a, **k: calls.append("mean+var"),
    )
    s = _scorer(tmp_path)
    _, var_p = s._produce_maps("pointstub", {}, tmp_path)
    assert calls == ["mean-only"] and var_p is None
    _, var_p2 = s._produce_maps("samplesstub", {}, tmp_path)
    assert calls == ["mean-only", "mean+var"] and var_p2 is not None


def test_run_mean_var_maps_on_point_method_fails_loud() -> None:
    """Forcing the variance path onto a POINT method raises CapabilityNotAvailableError."""
    from sverdrup.core.distribution import CapabilityNotAvailableError
    from sverdrup.core.grid import GridSpec
    from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
    from sverdrup.core.parameters import ConstantProvider
    from sverdrup.validation.run import run_mean_var_maps

    rng = np.random.default_rng(5)
    n = 60
    t = np.concatenate([[-30.0, 100.0], rng.uniform(-30, 100, n - 2)])
    obs = ObsWindow.from_arrays(
        lon=rng.uniform(296, 304, n),
        lat=rng.uniform(34, 42, n),
        time=t,
        values=rng.standard_normal(n) * 0.1,
        error_model=DiagonalErrorModel(np.full(n, 0.03**2)),
    )
    grid = GridSpec.lonlat(np.linspace(296.0, 304.0, 5), np.linspace(34.0, 42.0, 5))
    params = ConstantProvider(
        {"spacing_alpha": 1.5, "log10_rho": 1.3, "q_slope": 2.0, "l_t_days": 10.0}
    )
    import tempfile

    # The permanent SEARCH entry is the POINT-configured miost (the
    # registered "miost" is the SHIPPED SAMPLES product post-flip).
    with tempfile.TemporaryDirectory() as td:
        with pytest.raises(CapabilityNotAvailableError, match="POINT"):
            run_mean_var_maps(
                "miost-point",
                obs,
                params,
                grid,
                425.0,
                [30.0],
                Path(td) / "m.nc",
                Path(td) / "v.nc",
            )
