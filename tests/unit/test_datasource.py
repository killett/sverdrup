import numpy as np

from sverdrup.adapters.odc.fixtures import FixtureSource


def test_window_yields_lazy_obswindow():
    src = FixtureSource("tests/fixtures/natl60_tiny.nc")
    w = src.window(lon_range=(-65, -55), lat_range=(33, 43), time_range=(0, 5))
    assert len(w) > 0
    assert hasattr(w._values, "compute")  # lazy (invariant 2)


def test_truth_present_for_osse_absent_for_ose():
    osse = FixtureSource(
        "tests/fixtures/natl60_tiny.nc", ref_path="tests/fixtures/natl60_ref_tiny.nc"
    )
    from sverdrup.core.grid import GridSpec

    grid = GridSpec.lonlat(np.linspace(-64, -56, 5), np.linspace(34, 42, 5))
    truth = osse.truth(time_days=2.0, grid=grid)
    assert truth is not None
    assert truth.shape == (5, 5)
    ose = FixtureSource("tests/fixtures/ose_tiny.nc")
    assert ose.truth(time_days=2.0, grid=grid) is None
