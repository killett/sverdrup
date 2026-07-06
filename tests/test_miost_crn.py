"""Identity-keyed CRN perturbations (Stage B, spec 6.2).

The load-bearing property: perturbations are pure functions of
(seed root, member, identity) — never of window membership, enumeration
order, or array position. Overlapping windows then perturb shared
obs/elements IDENTICALLY, which is what keeps member fields coherent
across window seams without any cross-window communication.
"""

from __future__ import annotations

import numpy as np

from sverdrup.core.seeding import derive_seed
from sverdrup.methods.miost_basis import BasisSpec
from sverdrup.methods.miost_crn import coef_noise, obs_noise

ROOT = derive_seed("miost", "pk-test", "stageB-crn", 0)
SPEC = BasisSpec(alpha=1.5, l_t_days=10.0)
# Overlapping production windows: [0, 60] and [45, 105] share the 15-day
# blend zone, so their element sets share global temporal slots.
ELS_A = SPEC.elements_for_window(0.0)
ELS_B = SPEC.elements_for_window(45.0)


def test_cross_window_element_identity() -> None:
    """Shared element (same identity row) in two windows -> IDENTICAL noise.

    Catches: keying by window-local column index or enumeration order —
    the exact bug that would silently decorrelate members across the blend
    zone and inflate seam dispersion (what Task 18 measures).
    """
    qa = np.ones(len(ELS_A.identity))
    qb = np.ones(len(ELS_B.identity))
    za = coef_noise(member=3, identity=ELS_A.identity, q_var=qa, root=ROOT)
    zb = coef_noise(member=3, identity=ELS_B.identity, q_var=qb, root=ROOT)
    shared_a = {tuple(r): i for i, r in enumerate(map(tuple, ELS_A.identity))}
    n_shared = 0
    for j, r in enumerate(map(tuple, ELS_B.identity)):
        if r in shared_a:
            assert za[shared_a[r]] == zb[j]
            n_shared += 1
    # The overlap must actually be exercised — an empty intersection would
    # vacuously pass (windows share the 15-day blend zone by construction).
    assert n_shared > 100


def test_obs_noise_subset_invariant() -> None:
    """Obs noise depends on the obs identity row, not its array position.

    Catches: position-based keying — per-window obs SUBSETTING would then
    change a shared observation's perturbation between windows.
    """
    rng = np.random.default_rng(0)
    ids = np.column_stack(
        [
            rng.uniform(295, 305, 500),
            rng.uniform(33, 43, 500),
            rng.uniform(0, 60, 500),
            rng.integers(0, 6, 500).astype(np.float64),
        ]
    )
    r = np.full(500, 0.25)
    full = obs_noise(member=1, identity=ids, r_var=r, root=ROOT)
    sel = np.arange(0, 500, 7)  # arbitrary subset, order preserved
    sub = obs_noise(member=1, identity=ids[sel], r_var=r[sel], root=ROOT)
    np.testing.assert_array_equal(full[sel], sub)


def test_member_index_decorrelates() -> None:
    """Different member -> statistically independent stream (|corr| < 0.05).

    Catches: member index missing from the key — all members would collapse
    onto one realization and the ensemble variance would be ~0.
    """
    q = np.ones(len(ELS_A.identity))
    z0 = coef_noise(0, ELS_A.identity, q, ROOT)
    z1 = coef_noise(1, ELS_A.identity, q, ROOT)
    assert not np.array_equal(z0, z1)
    assert abs(np.corrcoef(z0, z1)[0, 1]) < 0.05


def test_obs_and_coef_streams_distinct() -> None:
    """Same (root, member) but different axis -> different stream.

    Catches: shared stream between eps' and eta~ — would correlate obs and
    coefficient perturbations, biasing the perturbed-obs posterior sample.
    """
    ids = np.arange(400, dtype=np.int64).reshape(100, 4)
    a = obs_noise(2, ids.astype(np.float64), np.ones(100), ROOT)
    b = coef_noise(2, ids, np.ones(100), ROOT)
    assert not np.allclose(a, b)


def test_moments_match_r() -> None:
    """1e5 draws: mean ~ 0, var ~ R within 2% (var=0.25 -> tol 0.005).

    Catches: missing sqrt(R) scaling (var would be 1.0 or 0.0625), biased
    uint64->uniform mapping, or a wrong inverse-normal transform.
    """
    rng = np.random.default_rng(1)
    ids = np.column_stack(
        [
            rng.uniform(295, 305, 100_000),
            rng.uniform(33, 43, 100_000),
            rng.uniform(0, 365, 100_000),
            rng.integers(0, 6, 100_000).astype(np.float64),
        ]
    )
    z = obs_noise(0, ids, np.full(100_000, 0.25), root=ROOT)
    assert abs(float(z.mean())) < 0.01
    assert abs(float(z.var()) - 0.25) < 0.005


def test_deterministic_across_calls() -> None:
    """Same inputs -> bit-identical output (reproducibility contract).

    Catches: any hidden nondeterministic salt (time, PYTHONHASHSEED-style
    hashing) — would break member reproducibility across sessions.
    """
    q = np.ones(50)
    ids = ELS_A.identity[:50]
    np.testing.assert_array_equal(
        coef_noise(5, ids, q, ROOT), coef_noise(5, ids, q, ROOT)
    )


def test_root_changes_stream() -> None:
    """Different seed root -> different realization.

    Catches: root ignored in the key — distinct experiments would share
    noise, defeating derive_seed's unit-of-work isolation.
    """
    other = derive_seed("miost", "pk-test", "stageB-crn", 1)
    q = np.ones(200)
    ids = ELS_A.identity[:200]
    assert not np.array_equal(coef_noise(0, ids, q, ROOT), coef_noise(0, ids, q, other))
