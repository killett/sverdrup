"""Drive the challenge's own scoring functions (ground truth) on a map + track.

This is a thin wrapper over the vendored ``2021a_SSH_mapping_OSE`` code
(``vendor/2021a_SSH_mapping_OSE``, pinned to the v1.0 leaderboard commit). It
reproduces the exact sequence of ``notebooks/example_eval_baseline.ipynb``:

1. ``src.mod_inout.read_l3_dataset`` — load the withheld Cryosat-2 track.
2. ``src.mod_interp.interp_on_alongtrack`` — interpolate the gridded map onto
   the track (SSH reference = ``sla_unfiltered + mdt - lwe``).
3. ``src.mod_stats.compute_stats`` — area-binned RMSE timeseries -> (mu, sigma).
4. ``src.mod_spectral.compute_spectral_scores`` -> PSD NetCDF.
5. ``src.mod_plot.find_wavelength_05_crossing`` -> lambda_x (effective resolution).

The eval-region box, time window, binning and spectral parameters below are
transcribed verbatim from that notebook; they *are* the published-leaderboard
eval definition, so ``score`` takes only the two file paths.
"""

from __future__ import annotations

import sys
import tempfile
import types
from pathlib import Path
from typing import Any

import matplotlib

_VENDOR = Path(__file__).resolve().parents[3] / "vendor" / "2021a_SSH_mapping_OSE"
_PYINTERP_PATCHED = False

# --- eval definition (notebooks/example_eval_baseline.ipynb, v1.0) ---
_LON_MIN, _LON_MAX = 295.0, 305.0
_LAT_MIN, _LAT_MAX = 33.0, 43.0
_TIME_MIN, _TIME_MAX = "2017-01-01", "2017-12-31"
_BIN_LON_STEP = 1.0
_BIN_LAT_STEP = 1.0
_BIN_TIME_STEP = "1D"
_DELTA_T = 0.9434  # s — Cryosat-2 along-track sampling interval
_VELOCITY = 6.77  # km/s — satellite ground-track speed
_DELTA_X = _VELOCITY * _DELTA_T  # km — along-track spatial sampling
_LENGTH_SCALE = 1000.0  # km — spectral segment length


def _prepare_imports() -> None:
    """Make the vendored challenge package importable in a headless env.

    Puts the submodule root on ``sys.path`` (their modules import each other as
    ``src.mod_*``), forces a non-interactive matplotlib backend, and stubs the
    unused ``hvplot`` import in ``mod_plot`` (it is imported only for
    interactive plots, never by the scoring function we call).
    """
    if str(_VENDOR) not in sys.path:
        sys.path.insert(0, str(_VENDOR))
    matplotlib.use("Agg", force=True)
    if "hvplot" not in sys.modules:
        stub = types.ModuleType("hvplot")
        xr_stub = types.ModuleType("hvplot.xarray")
        stub.xarray = xr_stub  # type: ignore[attr-defined]
        sys.modules["hvplot"] = stub
        sys.modules["hvplot.xarray"] = xr_stub
    _shim_pyinterp_axis()


def _patch(module: Any, name: str, value: Any) -> None:
    """Rebind ``module.name`` to ``value`` (indirection keeps both linters quiet)."""
    setattr(module, name, value)


def _shim_pyinterp_axis() -> None:
    """Bridge the challenge's 2021 pyinterp calls onto modern pyinterp (2026).

    The pinned challenge code targets a 2021-era pyinterp; the current pyinterp
    is API-incompatible in several places. Each shim below is a faithful, exact
    translation (kwarg rename / type coercion / restored accessor), never a
    change to scoring logic — validated by the DUACS row reproducing the
    published 0.88/0.07/152 (see ``tests/validation/test_their_eval_spike.py``):

    * ``Axis(is_circle=True)`` -> ``Axis(period=360.0)`` (their only ``is_circle``
      sites are degrees-longitude axes), and coerce DataArray values to float64.
    * ``TemporalAxis`` — coerce DataArray -> datetime64 ndarray and restore
      ``safe_cast`` (modern ``trivariate`` takes datetime64 directly).
    * ``Grid3D`` — materialize the (dask/float32) ssh array to a float64 ndarray.
    * ``Binning2D`` — restore the ``variable(name)`` accessor over the modern
      per-statistic methods. Idempotent.
    """
    global _PYINTERP_PATCHED
    if _PYINTERP_PATCHED:
        return
    import numpy as np
    import pyinterp

    real_axis = pyinterp.Axis

    def axis(*args: Any, is_circle: bool | None = None, **kwargs: Any) -> Any:
        if is_circle is not None and "period" not in kwargs:
            kwargs["period"] = 360.0 if is_circle else None
        if args:
            args = (np.asarray(args[0], dtype="float64"), *args[1:])
        return real_axis(*args, **kwargs)

    _patch(pyinterp, "Axis", axis)

    real_taxis = pyinterp.TemporalAxis

    class _CompatTemporalAxis(real_taxis):  # type: ignore[valid-type,misc]
        """TemporalAxis with the 2021-era ``safe_cast`` restored."""

        def safe_cast(self, values: Any) -> Any:
            return np.asarray(values).astype(self.dtype)

    def temporal_axis(*args: Any, **kwargs: Any) -> Any:
        if args:
            args = (np.asarray(args[0]), *args[1:])
        return _CompatTemporalAxis(*args, **kwargs)

    _patch(pyinterp, "TemporalAxis", temporal_axis)

    real_grid3d = pyinterp.Grid3D

    def grid3d(*args: Any, **kwargs: Any) -> Any:
        if args:
            *axes, values = args
            args = (*axes, np.asarray(values, dtype="float64"))
        return real_grid3d(*args, **kwargs)

    _patch(pyinterp, "Grid3D", grid3d)

    real_binning = pyinterp.Binning2D

    class _BinningProxy:
        """Forwarding proxy adding the 2021-era ``variable(name)`` accessor.

        Binning2D is a nanobind type (not Python-subclassable) but is only ever
        used through Python-level methods here, so a proxy that forwards
        everything to the real binning and adds ``variable`` suffices.
        """

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._b = real_binning(*args, **kwargs)

        def variable(self, name: str) -> Any:
            return getattr(self._b, name)()

        def __getattr__(self, name: str) -> Any:
            return getattr(self._b, name)

    _patch(pyinterp, "Binning2D", _BinningProxy)
    _PYINTERP_PATCHED = True


def score(map_path: Path, track_path: Path) -> tuple[float, float, float]:
    """Score a gridded SSH map against the withheld track using THEIR code.

    Args:
        map_path: Path to a gridded map NetCDF in the challenge L4 schema
            (coords ``lon``/``lat``/``time``, variable ``ssh``).
        track_path: Path to the withheld Cryosat-2 along-track L3 NetCDF.

    Returns:
        ``(mu_rmse, sigma_rmse, lambda_x_km)`` as computed by the challenge's
        own RMSE-based and spectral scoring functions.
    """
    _prepare_imports()
    from src.mod_inout import read_l3_dataset
    from src.mod_interp import interp_on_alongtrack
    from src.mod_plot import find_wavelength_05_crossing
    from src.mod_spectral import compute_spectral_scores
    from src.mod_stats import compute_stats

    ds_alongtrack = read_l3_dataset(
        str(track_path),
        lon_min=_LON_MIN,
        lon_max=_LON_MAX,
        lat_min=_LAT_MIN,
        lat_max=_LAT_MAX,
        time_min=_TIME_MIN,
        time_max=_TIME_MAX,
    )
    time_a, lat_a, lon_a, ssh_a, ssh_map_interp = interp_on_alongtrack(
        str(map_path),
        ds_alongtrack,
        lon_min=_LON_MIN,
        lon_max=_LON_MAX,
        lat_min=_LAT_MIN,
        lat_max=_LAT_MAX,
        time_min=_TIME_MIN,
        time_max=_TIME_MAX,
        is_circle=False,
    )

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        mu, sigma = compute_stats(
            time_a,
            lat_a,
            lon_a,
            ssh_a,
            ssh_map_interp,
            _BIN_LON_STEP,
            _BIN_LAT_STEP,
            _BIN_TIME_STEP,
            str(tmp / "stat.nc"),
            str(tmp / "stat_timeseries.nc"),
        )
        psd_file = tmp / "psd.nc"
        compute_spectral_scores(
            time_a,
            lat_a,
            lon_a,
            ssh_a,
            ssh_map_interp,
            _LENGTH_SCALE,
            _DELTA_X,
            _DELTA_T,
            str(psd_file),
        )
        lambda_x = float(find_wavelength_05_crossing(str(psd_file)))

    return float(mu), float(sigma), lambda_x
