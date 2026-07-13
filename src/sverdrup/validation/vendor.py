"""Vendored-submodule path/plumbing setup for the 2021a SSH-mapping OSE challenge.

This module contains *only* environment-preparation logic — no data loading,
no scoring, no c2 capability.  It exists so both
``sverdrup.validation.their_eval`` and the calibration harness can share the
same idempotent setup call without either importing the other.

``prepare_vendored_imports()`` does three things:

1. Adds the vendored submodule root to ``sys.path`` so the challenge's internal
   ``src.mod_*`` modules resolve correctly.
2. Forces the ``Agg`` (non-interactive) matplotlib backend.
3. Stubs the unused ``hvplot`` import in ``mod_plot`` and applies
   ``_shim_pyinterp_axis()`` to bridge 2021-era pyinterp API onto modern
   pyinterp.

None of these steps load data or invoke any scoring function.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import matplotlib

_VENDOR = Path(__file__).resolve().parents[3] / "vendor" / "2021a_SSH_mapping_OSE"
_PYINTERP_PATCHED = False


def prepare_vendored_imports() -> None:
    """Make the vendored challenge package importable in a headless env.

    Puts the submodule root on ``sys.path`` (their modules import each other as
    ``src.mod_*``), forces a non-interactive matplotlib backend, and stubs the
    unused ``hvplot`` import in ``mod_plot`` (it is imported only for
    interactive plots, never by the scoring function we call).

    No data loading, no scoring — path/plumbing only.  Safe to call multiple
    times (idempotent).
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
    is API-incompatible in several places.  Each shim below is a faithful, exact
    translation (kwarg rename / type coercion / restored accessor), never a
    change to scoring logic — validated by the DUACS row reproducing the
    published 0.88/0.07/152 (see ``tests/validation/test_their_eval_spike.py``):

    * ``Axis(is_circle=True)`` -> ``Axis(period=360.0)`` (their only ``is_circle``
      sites are degrees-longitude axes), and coerce DataArray values to float64.
    * ``TemporalAxis`` — coerce DataArray -> datetime64 ndarray and restore
      ``safe_cast`` (modern ``trivariate`` takes datetime64 directly).
    * ``Grid3D`` — materialize the (dask/float32) ssh array to a float64 ndarray.
    * ``Binning2D`` — restore the ``variable(name)`` accessor over the modern
      per-statistic methods.  Idempotent.
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
