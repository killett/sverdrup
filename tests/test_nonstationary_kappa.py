"""Nonstationary kappa: provider-driven latitude-varying range -> spatially-varying Q (Task 11)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import pytest

pytest.importorskip("sksparse")  # noqa: E402

from sverdrup.core.grid import GridSpec  # noqa: E402
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow  # noqa: E402
from sverdrup.core.types import ScalarOrField  # noqa: E402
from sverdrup.methods.gmrf import MaternGMRF  # noqa: E402


@dataclass(frozen=True)
class LatVaryingRange:
    """Resolve ``range`` as an equator->pole cos(lat) field; other params constant."""

    equator_km: float
    pole_km: float
    constants: dict[str, float]

    def resolve(self, name: str, grid: GridSpec) -> ScalarOrField:
        if name == "range":
            _, lat = grid._lonlat_nodes()
            c = np.cos(np.deg2rad(lat))
            return np.asarray(self.pole_km + (self.equator_km - self.pole_km) * c)
        return self.constants[name]

    def params_key(self) -> str:
        return f"latrange(eq={self.equator_km},pole={self.pole_km})"


def _grid():
    return GridSpec.lonlat(np.linspace(-10.0, 10.0, 11), np.linspace(0.0, 60.0, 13))


def _obs():
    return ObsWindow.from_arrays(
        np.array([0.0]),
        np.array([30.0]),
        np.array([2.0]),
        np.array([1.0]),
        DiagonalErrorModel(np.array([1e-3])),
    )


def test_nonstationary_kappa_varies_precision_by_latitude():
    # Behavior: a latitude-varying range field makes Q's coefficients latitude-dependent.
    # Bug caught: collapsing the field to a scalar (ignoring nonstationary kappa).
    prov = LatVaryingRange(
        800.0, 100.0, {"variance": 0.05, "temporal_taper_scale": 10.0}
    )
    dist = MaternGMRF().solve(_obs(), _grid(), prov, 2.0)
    q = cast(Any, dist.cov_op).q_post
    ny, nx = _grid().shape
    diag = q.diagonal()
    low_row = diag[0:nx].mean()  # near equator (range 800 -> small kappa)
    high_row = diag[(ny - 1) * nx :].mean()  # near 60N (range 100 -> larger kappa)
    assert not np.isclose(low_row, high_row, rtol=0.05)


def test_nonstationary_kappa_mapping_recorded():
    # Behavior: the kappa<->range mapping + field marker are recorded in provenance params.
    # Bug caught: a nonstationary run that silently drops the provenance of its varying kappa.
    prov = LatVaryingRange(
        800.0, 100.0, {"variance": 0.05, "temporal_taper_scale": 10.0}
    )
    dist = MaternGMRF().solve(_obs(), _grid(), prov, 2.0)
    params = dist.provenance.transformations[0].params
    assert "kappa_range_mapping" in params
    assert "field" in str(params["range"])


def test_stationary_scalar_range_still_works():
    # Behavior: a scalar range provider keeps the stationary path intact (Task 6 unchanged).
    from sverdrup.core.parameters import ConstantProvider

    p = ConstantProvider(
        {"range": 300.0, "variance": 0.05, "temporal_taper_scale": 10.0}
    )
    dist = MaternGMRF().solve(_obs(), _grid(), p, 2.0)
    assert np.isfinite(dist.marginal_variance()).all()
    assert dist.provenance.transformations[0].params["range"] == 300.0
