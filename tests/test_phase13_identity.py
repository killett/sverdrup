"""Phase-13 identity / nesting suite vs the signed miost5 product (plan Task 3).

The constant restriction of the ONE 7-dim parameterization (all δ = 0,
modes column-absent) must reproduce the signed FIVE-MISSION artifacts —
target = miost5, NEVER ``SHIPPED`` (post-flip that resolves to miost6).

Fast tests close the c-block leak class (query routes consume the η slice
alone) and pin the two pre-existing CRN axes bit-exactly. External tests
(``@pytest.mark.external`` + ``SVERDRUP_PHASE13_EXTERNAL=1``) reconstruct
day 0 of the signed product through the EXPLICIT-ZEROS restriction (m=100,
the signed root) and assert the four routes against the on-disk artifacts.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
import pytest

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ConstantProvider
from sverdrup.methods.miost import Miost, MiostPointDistribution
from sverdrup.methods.miost_basis import (
    R_REF,
    BasisSpec,
    DiagonalQ,
    build_g,
)
from sverdrup.methods.miost_crn import coef_noise, obs_noise
from sverdrup.methods.miost_error_basis import (
    build_b,
    lam_diag,
    mission_hash_ints,
    segment_passes,
)
from sverdrup.methods.miost_rspec import RSpec
from sverdrup.methods.miost_solver import MiostSolver, rhs_from_obs
from sverdrup.methods.miost_windows import Window, WindowPlan

_ZEROS = {"alg": 0.0, "h2g": 0.0, "j2g": 0.0, "j2n": 0.0}
_AUG = RSpec(deltas=_ZEROS, log_lam_bias=-3.5, log_lam_tilt=-4.0)

_ARTIFACTS = Path("data/2021a_ssh_mapping_ose/ours")
_ACCEPTANCE = _ARTIFACTS / "stage_miost_acceptance.nc"
_VAR_MAPS = _ARTIFACTS / "stage_b_var_maps.nc"
_SCOPE = Path("tests/validation/fixtures/stage_a_scope.json")
_EXTERNAL_ENV = "SVERDRUP_PHASE13_EXTERNAL"

_external_optin = pytest.mark.skipif(
    os.environ.get(_EXTERNAL_ENV) != "1",
    reason=(
        "opt-in: two full-obs m=100 member solves at the signed config, "
        f"~tens of minutes; set {_EXTERNAL_ENV}=1"
    ),
)


def _aug_fixture() -> tuple[ObsWindow, GridSpec, ConstantProvider]:
    """A tiny two-mission, two-pass obs set spanning window [0, 60] support."""
    rng = np.random.default_rng(31)
    lon_l, lat_l, t_l, mission_l = [], [], [], []
    for mission, day0 in (("alg", 20.0), ("h2g", 30.0)):
        frac = np.linspace(0.0, 1.0, 12)
        t_l.append(day0 + frac * (40.0 / 86400.0))
        lat_l.append(34.5 + frac * 7.0)
        lon_l.append(297.0 + frac * 2.0 + rng.uniform(0, 3))
        mission_l.append(np.full(12, mission, dtype=object))
    for day_edge in (-10.0, 70.0):
        t_l.append(np.asarray([day_edge]))
        lat_l.append(np.asarray([38.0]))
        lon_l.append(np.asarray([300.0]))
        mission_l.append(np.asarray(["alg"], dtype=object))
    lon = np.concatenate(lon_l)
    obs = ObsWindow.from_arrays(
        lon=lon,
        lat=np.concatenate(lat_l),
        time=np.concatenate(t_l),
        values=rng.standard_normal(lon.size) * 0.1,
        error_model=DiagonalErrorModel(np.full(lon.size, R_REF)),
        mission=np.concatenate(mission_l).astype(str),
    )
    grid = GridSpec.lonlat(np.linspace(296, 304, 7), np.linspace(34, 42, 7))
    params = ConstantProvider(
        {
            "spacing_alpha": 1.5,
            "log10_rho": math.log10(20.0),
            "q_slope": 2.0,
            "l_t_days": 10.0,
        }
    )
    return obs, grid, params


def test_structural_solved_state_holds_field_block_only() -> None:
    # STRUCTURAL query-route form (spec §6.2a): at an augmented config the
    # solved state and the window cache hold EXACTLY n_elem rows.
    # Bug caught: a forgotten [:n_elem] slice — the c-block would ride
    # into every product route (the class the behavioral test then closes).
    obs, grid, params = _aug_fixture()
    m = Miost(plan=WindowPlan(starts=(0.0,)), rspec=_AUG)
    dist = m.solve(obs, grid, params, 30.0)
    assert isinstance(dist, MiostPointDistribution)
    spec = m._spec_from(params, grid)
    n_elem = spec.elements_for_window(0.0).identity.shape[0]
    (eta,) = dist._etas.values()
    assert eta.shape == (n_elem,)
    (cached,) = m._eta_cache.values()
    assert cached.shape == (n_elem,)


def test_behavioral_c_perturbation_never_reaches_products() -> None:
    # BEHAVIORAL query-route form (spec §6.2b), realized as LOUD REFUSAL:
    # after §2 rider 1, no state object ever carries a c-slice — the
    # implementation-shape-robust closure of the leak class is therefore
    # that every product route REJECTS a c-carrying coefficient vector
    # with a shape error instead of consuming it. If a future refactor
    # made any route accept extended vectors (padding, broadcasting, or
    # summing over all rows — the variance-route-sums-all-columns class),
    # the raises-assertions here fail loudly and force review.
    # (A slice-then-compare form is vacuous — both sides would be built
    # from identical field-block bytes; recorded at Task-3 review.)
    spec = BasisSpec(alpha=1.5, l_t_days=10.0, ladder=(320.0, 452.548))
    obs, grid, _ = _aug_fixture()
    coords = obs.coords()
    lon, lat, t = coords[:, 0], coords[:, 1], coords[:, 2]
    y = obs.values()
    els = spec.elements_for_window(0.0)
    n_elem = els.identity.shape[0]
    q = DiagonalQ(rho=20.0, q_slope=2.0).variances_for(els)
    g = build_g(spec, els, lon, lat, t)
    assert obs.mission is not None
    mh = mission_hash_ints(obs.mission)
    pt = segment_passes(lon, lat, t, mh)
    from scipy import sparse  # type: ignore[import-untyped]  # noqa: PLC0415

    g_aug = sparse.hstack([g, build_b(pt)], format="csr")
    q_aug = np.concatenate([q, lam_diag(pt.n_pass, 10.0**-3.5, 10.0**-4.0)])
    r = np.full(y.size, R_REF)
    eta_full, _ = MiostSolver(g_aug, r_diag=r, q_diag=q_aug).solve(
        rhs_from_obs(g_aug, r, y)
    )
    eta_full = np.asarray(eta_full)
    assert eta_full.size > n_elem  # the fixture really is augmented

    wid = Window(0.0).id
    mk = MiostPointDistribution.from_etas
    # sanity: the correctly-sliced state builds and evaluates
    d_ok = mk(grid, 30.0, spec, {wid: eta_full[:n_elem]}, {wid: 0.0})
    assert np.isfinite(np.asarray(d_ok.mean)).all()

    # Γ-path POINT routes: a state carrying the unsliced vector refuses
    # loudly (gamma @ eta shape mismatch) — structural rejection.
    with pytest.raises(ValueError):
        mk(grid, 30.0, spec, {wid: eta_full}, {wid: 0.0})

    # S-path ENSEMBLE variance route (spec §6.2b, the literal behavioral
    # form): time_contract consumes layout-covered rows only, so a
    # c-carrying anomaly matrix — even with the c rows PERTURBED — yields
    # BIT-identical std fields. Bug caught: a variance route deriving its
    # block layout from eta.size (or summing all rows) would mix the
    # perturbed c into the output and differ.
    from sverdrup.distributions.miost_ensemble import std_fields  # noqa: PLC0415

    plan = WindowPlan(starts=(0.0,))
    anoms_sliced = np.tile(eta_full[:n_elem, None], (1, 3))
    anoms_with_c = np.tile(eta_full[:, None], (1, 3))
    anoms_c_perturbed = anoms_with_c.copy()
    anoms_c_perturbed[n_elem:] += 123.456
    ref = std_fields(spec, {wid: 0.0}, {wid: anoms_sliced}, grid, plan, [30.0])
    assert np.isfinite(ref).all()
    for anoms in (anoms_with_c, anoms_c_perturbed):
        got = std_fields(spec, {wid: 0.0}, {wid: anoms}, grid, plan, [30.0])
        assert np.array_equal(got, ref)


def test_crn_obs_axis_draws_pinned_bit_exact() -> None:
    # Recorded-draw regression (spec §6.4, obs axis): values captured at
    # the pre-phase-13 stream (root 777, member 3, literal identity rows).
    # Bug caught: any Task-4 stream/keying refactor (adding the "err"
    # axis) perturbing the EXISTING obs-noise stream — members would
    # silently decohere from every signed ensemble.
    ident = np.ascontiguousarray(
        [
            [297.5, 35.5, 12.25, 1234567.0],
            [300.0, 38.0, 12.25, 1234567.0],
            [303.0, 41.0, 40.75, 7654321.0],
            [298.8, 36.9, 40.75, 7654321.0],
        ]
    )
    r = np.asarray([0.0009, 0.0009, 0.0016, 0.0016])
    got = obs_noise(3, ident, r, 777)
    pinned = [
        -0.0063833024081441396,
        0.0026860406103448955,
        0.008727173527609508,
        -0.018637456813990233,
    ]
    assert got.tolist() == pinned


def test_crn_elem_axis_draws_pinned_bit_exact() -> None:
    # Recorded-draw regression (spec §6.4, elem axis): same capture
    # protocol for the η̃ stream. Same bug class as the obs-axis pin.
    ident = np.ascontiguousarray(
        [
            [0, 0, 0, 1, 2, 5],
            [0, 1, 1, 3, 4, 5],
            [1, 0, 0, 2, 2, 6],
            [1, 2, 1, 0, 1, 7],
        ],
        dtype=np.int64,
    )
    q = np.asarray([0.01, 0.02, 0.04, 0.08])
    got = coef_noise(3, ident, q, 777)
    pinned = [
        0.03210196112350635,
        -0.25571039547769936,
        -0.011233687587108755,
        -0.3238310788336019,
    ]
    assert got.tolist() == pinned


def test_member_path_zeros_restriction_and_structured_kinds() -> None:
    # The nesting identity runs the EXPLICIT-ZEROS restriction on the
    # member path (σ²_m ≡ R_REF bit-exactly) under the scalar-era kind;
    # a structured config (Task-4 sampler) produces the VERSIONED kind.
    # Bug caught: the zeros restriction blocked, or a structured ensemble
    # persisted under the scalar-era provenance tag.
    from sverdrup.distributions.miost_ensemble import KIND, KIND_AUG

    obs, grid, params = _aug_fixture()
    plan = WindowPlan(starts=(0.0,))
    zeros = Miost(plan=plan, members=2, member_root=99, rspec=RSpec(deltas=_ZEROS))
    d0 = zeros.solve(obs, grid, params, 30.0)
    # structured rspec (zeros) -> the versioned tag
    assert d0.underlying.state_kind == KIND_AUG  # type: ignore[union-attr]
    scalar = Miost(plan=plan, members=2, member_root=99)
    d1 = scalar.solve(obs, grid, params, 30.0)
    assert d1.underlying.state_kind == KIND  # type: ignore[union-attr]
    structured = Miost(
        plan=plan,
        members=2,
        member_root=99,
        rspec=RSpec(deltas={**_ZEROS, "alg": 0.1}),
    )
    d2 = structured.solve(obs, grid, params, 30.0)
    assert d2.underlying.state_kind == KIND_AUG  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# External: day-0 four-route identity vs the SIGNED miost5 artifacts
# ---------------------------------------------------------------------------


def _summarize_and_free(dist: object) -> dict[str, object]:
    """Extract the four routes' comparison payload, then free the product.

    Memory discipline (recorded at Task-3 execution): holding two m=100
    products through the joint 100-RHS member batch OOM-killed the run
    twice on this host (cgroup ``oom_kill`` events). Member arrays are
    compared via sha256 (hash equality == byte equality), so each product
    reduces to hashes + two small map arrays before the next solve. The
    joint batch itself is NOT chunked — the blocked PCG iterates every
    column until the LAST converges, so member bytes depend on the batch
    composition and only the full m=100 batch reproduces the signed run.
    """
    import hashlib as _hl

    raw = dist.underlying  # type: ignore[attr-defined]
    grid = raw.grid
    lon2d, lat2d = np.meshgrid(grid.x, grid.y)
    pts = np.column_stack([lon2d.ravel(), lat2d.ravel(), np.zeros(lon2d.size)])
    # CHUNKED Γ-path evaluation: one whole-grid mean_at call materializes a
    # dense (n_pts, n_elem) evaluate ~15-20 GB at production element counts
    # — the OOM that killed every earlier attempt right after PCG
    # completion. 200-point chunks cap the transient at ~300 MB.
    gamma_vals = np.concatenate(
        [raw.mean_at(pts[i : i + 200]) for i in range(0, pts.shape[0], 200)]
    )
    gamma_mean = np.asarray(gamma_vals).reshape(grid.shape)
    out: dict[str, object] = {
        "mean": np.asarray(raw.mean).copy(),
        "gamma_mean": gamma_mean.copy(),
        "var": np.asarray(raw.marginal_variance()).copy(),
        "eta_sha": {
            w: _hl.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
            for w, a in raw._etas_a.items()
        },
        "anoms_sha": {
            w: _hl.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
            for w, a in raw._anoms.items()
        },
    }
    return out


@pytest.fixture(scope="module")
def day0_pair() -> tuple[dict[str, object], dict[str, object], np.ndarray]:
    """Day-0 miost5 reconstruction, scalar rspec vs explicit-zeros rspec.

    Mirrors the Phase-8 external fixture recipe exactly (five-mission
    train subset, halo cut, signed winner params from the acceptance
    artifact's provenance attrs, m=100 at the signed root). Day 0 is
    covered by exactly ONE window, so this reproduces the signed w-18
    member batch without solving the year. Each product is summarized and
    FREED before the next solve (see ``_summarize_and_free``).

    Determinism assumption (recorded): the two solves run FRESH (their
    params_keys differ, so no cache crosstalk) and are compared bit-equal
    — this relies on same-process floating-point determinism of the PCG /
    sparse SpMV stack, the same standing assumption every CRN replay test
    in this suite already makes.

    Leg cache (operational, recorded at Task-3 execution): with
    ``SVERDRUP_PHASE13_EXT_CACHE=<dir>`` each leg's summary is persisted
    and reused, so a run killed by external cgroup memory pressure (three
    ``oom_kill`` events on this host) resumes at the surviving leg. The
    cache holds ONLY the derived summaries; clearing the directory forces
    a full recompute (the gate re-validation path).
    """
    import gc
    import json

    import xarray as xr

    from sverdrup.application.splits import make_splits
    from sverdrup.application.tuning.stage_a import _subset
    from sverdrup.methods.miost import (
        STAGE_B_MEMBERS,
        STAGE_B_ROOT,
        shipped_miost5_scalar_phase8,
    )
    from sverdrup.methods.miost_basis import HALO_DEG
    from sverdrup.validation.input_adapter import load_mapping_obs, load_mdt_grid
    from sverdrup.validation.params import baseline_config
    from sverdrup.validation.run import halo_obs

    cfg = json.loads(_SCOPE.read_text())
    with xr.open_dataset(_ACCEPTANCE) as ds:
        winner = json.loads(str(ds.attrs["winner_params"]))
        t0 = np.asarray(ds.time.values)[0]
    assert t0 == np.datetime64("2017-01-01")

    provider, grid, _ = baseline_config()
    obs = load_mapping_obs([Path(p) for p in cfg["mapping_obs_paths"]], provider)
    obs = halo_obs(obs, grid, HALO_DEG)
    split = make_splits(
        obs,
        by="mission",
        locked_missions=["c2"],
        validation_missions=[str(cfg["validation_mission"])],
    )
    train = _subset(obs, split.train_idx)

    scalar = shipped_miost5_scalar_phase8()  # the SIGNED scalar-era config
    cache_dir = os.environ.get("SVERDRUP_PHASE13_EXT_CACHE")
    if cache_dir:
        # crash-durable member-batch PCG (bit-identical resume; the same
        # oom-pressure record as the leg cache above)
        scalar.member_solve_checkpoint_dir = Path(cache_dir)
    zeros = Miost(
        members=STAGE_B_MEMBERS,
        member_root=STAGE_B_ROOT,
        calibration=scalar._calibration,
        rspec=RSpec(deltas=_ZEROS),
        member_solve_checkpoint_dir=Path(cache_dir) if cache_dir else None,
    )
    cache_dir = os.environ.get("SVERDRUP_PHASE13_EXT_CACHE")

    def _leg(name: str, method: Miost) -> dict[str, object]:
        cache = Path(cache_dir) / f"day0_{name}.npz" if cache_dir else None
        if cache is not None and cache.exists():
            try:
                with np.load(cache, allow_pickle=True) as z:
                    return {
                        "mean": np.asarray(z["mean"]),
                        "gamma_mean": np.asarray(z["gamma_mean"]),
                        "var": np.asarray(z["var"]),
                        "eta_sha": z["eta_sha"].item(),
                        "anoms_sha": z["anoms_sha"].item(),
                    }
            except KeyError:
                cache.unlink()  # older schema: recompute the leg
        d = method.solve(train, grid, ConstantProvider(winner), 0.0)
        out = _summarize_and_free(d)
        del d
        gc.collect()
        if cache is not None:
            np.savez(
                cache,
                mean=np.asarray(out["mean"]),
                gamma_mean=np.asarray(out["gamma_mean"]),
                var=np.asarray(out["var"]),
                eta_sha=np.asarray(out["eta_sha"], dtype=object),
                anoms_sha=np.asarray(out["anoms_sha"], dtype=object),
            )
        return out

    sum_scalar = _leg("scalar", scalar)
    sum_zeros = _leg("zeros", zeros)
    mdt = load_mdt_grid([Path(p) for p in cfg["mdt_paths"]], grid)
    return sum_scalar, sum_zeros, np.asarray(mdt)


@pytest.mark.external
@_external_optin
@pytest.mark.skipif(
    not (_ACCEPTANCE.exists() and _VAR_MAPS.exists() and _SCOPE.exists()),
    reason="signed miost5 artifacts / challenge data absent",
)
def test_external_four_route_identity_vs_signed_miost5(
    day0_pair: tuple[dict[str, object], dict[str, object], np.ndarray],
) -> None:
    """Four routes at the explicit-zeros restriction vs the signed artifacts.

    Routes: (1) S-path grid mean vs ``stage_miost_acceptance.nc`` day 0 —
    BIT asserted, rtol-1e-12 fallback with the failure mode printed;
    (2) Γ-path ``mean_at`` at the grid points vs the SAME signed artifact
    at rtol 1e-12 (the ensemble's S-path and dense Γ-path are different
    summation orders — mathematically equal, NOT bitwise; a bit assertion
    here failed at last-ulp level on the first full run, recorded);
    (3) member route — every member anomaly array bit-equal between the
    scalar-era product and the explicit-zeros restriction; (4) variance
    route — raw member variance vs ``stage_b_var_maps.nc`` day 0 at
    rtol 1e-12 (measured 2.2e-16 on the first full run).

    Member-route artifact anchor (recorded at Task-3 review): no signed
    member-store artifact exists on disk for miost5, so route (3) cannot
    be compared to signed bytes directly. Its anchor chain is: zeros ≡
    scalar members BIT (asserted here) + the signed var maps are a
    deterministic function of those members (route 4, rtol 1e-12) + the
    standing Phase-8 external pin of the scalar product against the same
    artifacts. That is the strongest member-route claim the signed
    artifact set supports.

    Bug caught: ANY behavioral daylight between the scalar era and the
    constant restriction of the new parameterization — the nesting claim
    this phase's inference rests on (spec §6.1).
    """
    import xarray as xr

    sum_s, sum_z, mdt = day0_pair

    # (3) member route: identical CRN + identical solves => byte-equal
    # (sha256 equality over the full anomaly/eta arrays)
    assert sum_s["eta_sha"] == sum_z["eta_sha"]
    assert sum_s["anoms_sha"] == sum_z["anoms_sha"]

    # (1) S-path grid mean vs the signed acceptance map
    with xr.open_dataset(_ACCEPTANCE) as ds:
        signed_mean = np.asarray(ds["ssh"].isel(time=0).values)
    got = np.asarray(sum_z["mean"]) + mdt
    if not np.array_equal(got, signed_mean):
        diff = np.max(np.abs(got - signed_mean))
        print(f"mean map NOT bit-identical (max abs diff {diff:.3e}); rtol fallback")
        np.testing.assert_allclose(got, signed_mean, rtol=1e-12, atol=1e-15)

    # (2) Γ-path points vs the signed artifact, rtol 1e-12 (both configs)
    for s in (sum_z, sum_s):
        np.testing.assert_allclose(
            np.asarray(s["gamma_mean"]) + mdt, signed_mean, rtol=1e-12, atol=1e-15
        )

    # (4) variance route vs the signed var maps (RAW member variance)
    with xr.open_dataset(_VAR_MAPS) as ds:
        signed_var = np.asarray(ds["ssh"].isel(time=0).values)
    np.testing.assert_allclose(
        np.asarray(sum_z["var"]), signed_var, rtol=1e-12, atol=1e-18
    )
