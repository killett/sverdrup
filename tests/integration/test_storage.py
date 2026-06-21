import numpy as np

from regatta.adapters.storage_fsspec import FsspecResultSink, read_product
from regatta.application.solve import solve_unit
from regatta.application.uow import UnitOfWork
from regatta.core.grid import GridSpec
from regatta.core.observations import DiagonalErrorModel, ObsWindow
from regatta.core.parameters import ConstantProvider


def _product():
    grid = GridSpec.lonlat(np.linspace(0, 2, 4), np.linspace(40, 42, 4))
    obs = ObsWindow.from_arrays(
        np.array([0.5, 1.5]),
        np.array([40.5, 41.5]),
        np.zeros(2),
        np.array([0.1, -0.2]),
        DiagonalErrorModel(np.full(2, 0.01)),
    )
    params = ConstantProvider(
        {"length_scale": 200.0, "time_scale": 10.0, "variance": 1.0}
    )
    return solve_unit(
        UnitOfWork("tile0", "oi", params, "train", 7, [0.0], obs, grid, None, [])
    )


def test_roundtrip(tmp_path):
    product = _product()
    sink = FsspecResultSink()
    url = f"file://{tmp_path}/prod.zarr"
    sink.write(product, url)
    back = read_product(url)
    assert np.allclose(
        back.per_time[0].base.marginal_variance(),
        product.per_time[0].base.marginal_variance(),
        atol=1e-10,
    )
    assert back.per_time[0].provenance.method == "oi"
    assert back.per_time[0].base.fields.rank == product.per_time[0].base.fields.rank
