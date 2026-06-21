import numpy as np

from sverdrup.core.product import EvalPointPredictions, PerTimeProduct, Product


def test_eval_points_shapes():
    ep = EvalPointPredictions(
        locations=np.zeros((3, 3)), mean=np.zeros(3), variance=np.ones(3), samples=None
    )
    assert ep.locations.shape == (3, 3)
    assert ep.variance.shape == (3,)


def test_product_orders_times():
    # Bug caught: losing the per-time series ordering (deliverable is a series of grids).
    p0 = PerTimeProduct(
        time_days=2.0, base=object(), derived={}, eval_points=None, provenance=None
    )
    p1 = PerTimeProduct(
        time_days=0.0, base=object(), derived={}, eval_points=None, provenance=None
    )
    product = Product(per_time=[p0, p1], run_manifest={"mode": "OSSE"})
    assert product.times() == [0.0, 2.0]
