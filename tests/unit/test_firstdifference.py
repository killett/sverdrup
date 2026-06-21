import numpy as np
import pytest

from sverdrup.core.grid import GridSpec
from sverdrup.core.provenance import UncertaintyProvenance
from sverdrup.core.types import Linearity, UncertaintyCapability
from sverdrup.derived.area_average import AreaAverage
from sverdrup.derived.firstdifference import FirstDifference
from sverdrup.distributions.gaussian import GaussianPredictiveDistribution
from tests.unit._doubles import ToyExpOperator


def _gauss(n=5):
    grid = GridSpec.lonlat(np.linspace(0, 4, n), np.linspace(40, 44, n))
    prov = UncertaintyProvenance(
        native_capability=UncertaintyCapability.SAMPLES, transformations=[]
    )
    return GaussianPredictiveDistribution(
        grid, np.zeros((n, n)), ToyExpOperator(), prov, time_days=0.0
    )


def test_first_difference_is_linear_and_closes():
    fd = FirstDifference(axis="x")
    assert fd.linearity is Linearity.LINEAR
    out = fd.apply(_gauss())
    assert out.marginal_variance().shape[0] == 5  # still a field distribution


def test_uses_crs_metric_not_index():
    # Bug caught: index-space finite difference (ignores cos(lat) / Earth radius).
    fd = FirstDifference(axis="x")
    out = fd.apply(_gauss())
    # metres-per-degree-lon at lat~42 is ~ cos(42)*111195; a unit index diff must scale by it
    assert out.metric_scale_x[0] == pytest.approx(
        np.cos(np.deg2rad(40)) * 111195.0, rel=0.05
    )


def test_area_average_stub_signature():
    aa = AreaAverage()
    assert aa.linearity is Linearity.LINEAR
    with pytest.raises(NotImplementedError):
        aa.apply(_gauss())
