"""Tile-scale sizing tests (phase-14 Task 15, 0b-1).

The retained-store term BY NAME (the Phase-12 miss), box-identity of the
domain defaults, and the basis-domain hook's identity guarantee.
"""

from __future__ import annotations

from sverdrup.methods.miost_basis import LADDER, BasisSpec
from sverdrup.methods.miost_sizing import (
    D_X_KM,
    D_Y_KM,
    n_coefficients,
    peak_model,
    size_tile,
)

_ALPHA, _NDIR, _LAM = 1.0656719505786896, 8, 80.0


def test_retained_store_term_named_and_scales_with_m() -> None:
    """retained_member_store_mib = n_grid*n_windows*m*8 B — and it SCALES.

    The Phase-12 accumulator miss: doubling m must double the retained
    term and grow the peak; a model that forgets the store again fails.
    """

    def sized(m: int) -> dict[str, float]:
        return size_tile(
            d_x_km=1500.0,
            d_y_km=1600.0,
            n_grid_nodes=9216,
            window_days=60.0,
            n_windows=9,
            m_members=m,
            n_obs=40000,
            alpha=_ALPHA,
            n_dir=_NDIR,
            lam_min=_LAM,
        )

    s1 = sized(1)
    s100 = sized(100)
    assert s1["retained_member_store_mib"] == 9216 * 9 * 1 * 8 / 2**20
    assert s100["retained_member_store_mib"] == 100 * s1["retained_member_store_mib"]
    assert s100["peak_model_mib"] > s1["peak_model_mib"]


def test_box_dims_reproduce_box_peak_model() -> None:
    """size_tile at the box dims == the standing box peak_model (identity)."""
    tile = size_tile(
        d_x_km=D_X_KM,
        d_y_km=D_Y_KM,
        n_grid_nodes=0,
        window_days=60.0,
        n_windows=1,
        m_members=1,
        n_obs=11041,
        alpha=_ALPHA,
        n_dir=_NDIR,
        lam_min=_LAM,
    )
    box_peak = peak_model(_ALPHA, _NDIR, 60.0, _LAM, 11041, m=1)
    # retained term is 0 at n_grid_nodes=0, so totals must coincide
    assert tile["peak_model_mib"] == box_peak.total / 2**20
    assert tile["n_coef"] == float(
        n_coefficients(_ALPHA, _NDIR, 60.0, _LAM, margin=True)
    )


def test_wall_estimate_scales_with_obs() -> None:
    """wall_est ∝ nnz: doubling n_obs doubles the estimate (recorded basis)."""

    def sized(n_obs: int) -> dict[str, float]:
        return size_tile(
            d_x_km=1500.0,
            d_y_km=1600.0,
            n_grid_nodes=0,
            window_days=60.0,
            n_windows=1,
            m_members=1,
            n_obs=n_obs,
            alpha=_ALPHA,
            n_dir=_NDIR,
            lam_min=_LAM,
        )

    a = sized(11041)
    b = sized(22082)
    assert abs(b["wall_est_s"] / a["wall_est_s"] - 2.0) < 1e-6  # int-round slack
    assert abs(a["wall_est_s"] - 253.4) < 1.0  # the box basis reproduces itself


def test_default_basis_domain_identity() -> None:
    """A default-domain BasisSpec enumerates byte-identically to the signed
    construction: key() carries NO domain suffix and the element count at
    a fixed window is unchanged; a tile-domain spec differs in both."""
    default = BasisSpec(alpha=_ALPHA, l_t_days=6.00630128569901)
    assert ";dom=" not in default.key()
    tile = BasisSpec(
        alpha=_ALPHA,
        l_t_days=6.00630128569901,
        x0_km=-300.0,
        y0_km=-300.0,
        d_x_km=1500.0,
        d_y_km=1600.0,
    )
    assert ";dom=" in tile.key()
    els_d = default.elements_for_window(14.0, 60.0)
    els_t = tile.elements_for_window(14.0, 60.0)
    assert els_t.identity.shape[0] > els_d.identity.shape[0]
    assert len(LADDER) == 8  # the D1 ladder is untouched by the extension
