import numpy as np

from regatta.methods.solver import DenseCholeskySolver


def test_solve_matches_numpy():
    rng = np.random.default_rng(1)
    a = rng.normal(size=(6, 6))
    spd = a @ a.T + np.eye(6)
    b = rng.normal(size=6)
    s = DenseCholeskySolver()
    s.factor(spd)
    assert np.allclose(s.solve(b), np.linalg.solve(spd, b))


def test_triangular_solve_gives_L_inv():
    rng = np.random.default_rng(2)
    a = rng.normal(size=(5, 5))
    spd = a @ a.T + np.eye(5)
    s = DenseCholeskySolver()
    s.factor(spd)
    b = rng.normal(size=(5, 3))
    v = s.solve_triangular_lower(b)
    assert np.allclose(s.lower @ v, b)
