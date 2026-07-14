"""OI dispatch seam: provider-aware Gaussian-degrees kernel factory (Task 3).

Bugs caught: the factory drifting from ``baseline_kernel()`` (any constant,
exponent, or anisotropy change breaks byte-identity); a ``LatitudeField``
silently coerced to float instead of routing the nonstationary branch; the
two kernel-from-params flags both set (ambiguous kernel source); the
``run_mean_var_maps`` factory path diverging from the explicit-kernel path.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import (
    ConstantProvider,
    LatitudeField,
    LatitudeVaryingProvider,
)
from sverdrup.validation.params import baseline_kernel
from sverdrup.validation.run import gaussian_kernel_from_params, run_mean_var_maps


def _pts() -> np.ndarray:
    rng = np.random.default_rng(7)
    lon = 295 + 10 * rng.random(40)
    lat = 33 + 10 * rng.random(40)
    t = 30 * rng.random(40)
    return np.column_stack([lon, lat, t])


def test_scalar_path_bit_identical_to_baseline() -> None:
    # Signed values through the factory == baseline_kernel(), np.array_equal
    # (NOT allclose): the byte-identical baseline gate.
    p = ConstantProvider({"variance": 1.0, "lx_deg": 1.0, "time_scale": 7.0})
    k = gaussian_kernel_from_params(p, None)
    a = _pts()
    b = _pts()[:17]
    assert np.array_equal(k.evaluate(a, b), baseline_kernel().evaluate(a, b))


def test_field_path_routes_nonstationary() -> None:
    # A LatitudeField in ANY resolved slot must route the nonstationary
    # branch (NotImplementedError until Task 4), never coerce to float.
    p = LatitudeVaryingProvider(
        core={"variance": 1.0, "time_scale": 7.0},
        varied={"lx_deg": LatitudeField("exp-linear-mult", (-0.2,))},
    )
    with pytest.raises(NotImplementedError):  # replaced by type check in Task 4
        gaussian_kernel_from_params(p, None)


def test_variance_field_also_routes_nonstationary() -> None:
    # The variance slot must route too — not only the length multiplier.
    p = LatitudeVaryingProvider(
        core={"lx_deg": 1.0, "time_scale": 7.0},
        varied={"variance": LatitudeField("exp-quad", (0.0, 0.3, -0.6))},
    )
    with pytest.raises(NotImplementedError):
        gaussian_kernel_from_params(p, None)


def _tiny_obs(n: int = 90) -> ObsWindow:
    rng = np.random.default_rng(11)
    return ObsWindow.from_arrays(
        300.0 + 1.0 * rng.random(n),
        38.0 + 1.0 * rng.random(n),
        rng.uniform(-2.0, 5.0, n),
        rng.standard_normal(n) * 0.1,
        DiagonalErrorModel(np.full(n, 0.0025)),
        mission=np.asarray(["alg"] * n),
    )


def test_run_mean_var_maps_factory_path_bit_identical(tmp_path: Path) -> None:
    # 3-day dev-scope maps: factory path (flag + provider) vs explicit
    # kernel=baseline_kernel() — mean AND var bit-identical.
    grid = GridSpec.lonlat(np.arange(300.0, 300.61, 0.2), np.arange(38.0, 38.61, 0.2))
    obs = _tiny_obs()
    days = [0.0, 1.0, 2.0]
    p_factory = ConstantProvider({"variance": 1.0, "lx_deg": 1.0, "time_scale": 7.0})
    p_legacy = ConstantProvider(
        {"variance": 1.0, "length_scale": 111.195, "time_scale": 7.0}
    )
    m_a, v_a = (tmp_path / "mean_a.nc", tmp_path / "var_a.nc")
    m_b, v_b = (tmp_path / "mean_b.nc", tmp_path / "var_b.nc")
    run_mean_var_maps(
        "oi", obs, p_legacy, grid, 14.0, days, m_a, v_a, kernel=baseline_kernel()
    )
    run_mean_var_maps(
        "oi",
        obs,
        p_factory,
        grid,
        14.0,
        days,
        m_b,
        v_b,
        oi_gaussian_kernel_from_params=True,
    )
    for path_a, path_b in ((m_a, m_b), (v_a, v_b)):
        with xr.open_dataset(path_a) as da, xr.open_dataset(path_b) as db:
            assert np.array_equal(da["ssh"].values, db["ssh"].values)


def test_both_kernel_flags_rejected(tmp_path: Path) -> None:
    # Ambiguous kernel source: Matérn-from-params AND Gaussian-from-params
    # both requested -> loud ValueError, nothing solved/written.
    grid = GridSpec.lonlat(np.array([300.0, 300.2]), np.array([38.0, 38.2]))
    p = ConstantProvider(
        {"variance": 1.0, "lx_deg": 1.0, "length_scale": 111.195, "time_scale": 7.0}
    )
    with pytest.raises(ValueError, match="kernel"):
        run_mean_var_maps(
            "oi",
            _tiny_obs(10),
            p,
            grid,
            14.0,
            [0.0],
            tmp_path / "m.nc",
            tmp_path / "v.nc",
            oi_kernel_from_params=True,
            oi_gaussian_kernel_from_params=True,
        )
    assert not (tmp_path / "m.nc").exists()
