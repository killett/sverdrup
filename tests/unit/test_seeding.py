import numpy as np

from regatta.core.seeding import derive_seed


def test_deterministic_and_member_varying():
    # Bug caught: nondeterministic seeding (would break reproducibility, spec 5.9).
    a = derive_seed("oi", "ls=100;ts=10", "tile0@t12", 0)
    b = derive_seed("oi", "ls=100;ts=10", "tile0@t12", 0)
    c = derive_seed("oi", "ls=100;ts=10", "tile0@t12", 1)
    assert a == b
    assert a != c


def test_seed_in_rng_range():
    s = derive_seed("trivial", "", "tile0@t0", 7)
    assert 0 <= s < 2**63
    np.random.default_rng(s)  # must not raise
