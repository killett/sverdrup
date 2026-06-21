import numpy as np

from regatta.methods.kernel import Matern32SpaceTime


def _pts(rows):
    return np.array(rows, float)


def test_diagonal_is_variance_and_symmetric():
    k = Matern32SpaceTime(variance=0.7, length_scale=100.0, time_scale=10.0)
    pts = _pts([[0, 0, 0], [1, 1, 1]])
    m = k.evaluate(pts, pts)
    assert np.allclose(np.diag(m), 0.7)
    assert np.allclose(m, m.T)


def test_separation_decreases_covariance():
    # Bug caught: spatial-only kernel that ignores the time column.
    k = Matern32SpaceTime(variance=1.0, length_scale=100.0, time_scale=5.0)
    a = _pts([[0.0, 0.0, 0.0]])
    near = _pts([[0.0, 0.0, 1.0]])
    far_t = _pts([[0.0, 0.0, 30.0]])
    assert k.evaluate(a, far_t)[0, 0] < k.evaluate(a, near)[0, 0]


def test_psd():
    k = Matern32SpaceTime(variance=1.0, length_scale=100.0, time_scale=10.0)
    rng = np.random.default_rng(0)
    pts = rng.normal(size=(8, 3)) * np.array([50, 50, 5])
    m = k.evaluate(pts, pts) + 1e-8 * np.eye(8)
    assert np.all(np.linalg.eigvalsh(m) > 0)
