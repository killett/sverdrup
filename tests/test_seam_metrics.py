"""Stage-1 seam metric tests (phase-14, sealed rubric).

Pins ``sverdrup.validation.seam_metrics`` against the PRE-REGISTERED
rubric ``docs/validation/phase14_seam_rubric.md``: interior reference
dispersion ``D_int``, co-located seam delta, ratio ``R``, verdict cells,
the residual validity guard (the rubric's Rule-0 floor-probe
attributability check belongs to the consumer, T4), and NaN (land)
handling. All
expected values are hand-computed, never derived from the implementation.
"""

from __future__ import annotations

import math
from typing import Any, TypedDict

import numpy as np
import pytest

from sverdrup.validation import seam_metrics
from sverdrup.validation.seam_metrics import (
    SeamRead,
    interior_increment_rms,
    seam_delta,
    seam_read,
    seam_verdict,
)


def _arange_4x4() -> np.ndarray:
    """A 4x4 arange field: axis-0 steps are all 4.0, axis-1 steps all 1.0."""
    return np.arange(16, dtype=np.float64).reshape(4, 4)


# ---------------------------------------------------------------------------
# interior_increment_rms — D_int building block
# ---------------------------------------------------------------------------


def test_interior_increment_rms_axis0_hand_value() -> None:
    """Axis-0 one-grid-step increment RMS of a 4x4 arange is exactly 4.0.

    Bug caught: differencing along the wrong axis (would return 1.0) or a
    wrong normalization (mean instead of root-mean-square of increments).
    """
    assert interior_increment_rms(_arange_4x4(), axis=0) == pytest.approx(
        4.0, rel=1e-12
    )


def test_interior_increment_rms_axis1_hand_value() -> None:
    """Axis-1 one-grid-step increment RMS of a 4x4 arange is exactly 1.0.

    Bug caught: axis argument ignored or transposed (would return 4.0).
    """
    assert interior_increment_rms(_arange_4x4(), axis=1) == pytest.approx(
        1.0, rel=1e-12
    )


def test_interior_increment_rms_excludes_nan_nodes() -> None:
    """A NaN (land) node drops its increments from the pool; RMS stays 4.0.

    On the 4x4 arange with field[0, 0] = NaN, the single axis-0 increment
    touching that node is excluded; every surviving increment is 4.0.

    Bug caught: naive ``np.diff`` + mean propagating NaN through the pool
    (the whole RMS would come back NaN).
    """
    field = _arange_4x4()
    field[0, 0] = np.nan
    assert interior_increment_rms(field, axis=0) == pytest.approx(4.0, rel=1e-12)


def test_interior_increment_rms_all_nan_refuses() -> None:
    """An all-NaN interior refuses (ValueError) instead of returning NaN.

    Bug caught: silently emitting ``nan`` as a reference dispersion, which
    would poison the seam ratio downstream instead of failing loudly.
    """
    field = np.full((4, 4), np.nan)
    with pytest.raises(ValueError, match="all-NaN"):
        interior_increment_rms(field, axis=0)


# ---------------------------------------------------------------------------
# seam_delta — co-located RMS difference on the 2·overlap strip
# ---------------------------------------------------------------------------


def test_seam_delta_hand_value_two_cm_on_three_nodes() -> None:
    """Two constant fields differing by 2 cm on a 3-node seam give 0.02.

    Bug caught: a sign-dependent reduction (plain mean of signed
    differences could cancel) or a wrong node-count normalization.
    """
    a = np.full(3, 1.00)
    b = np.full(3, 1.02)
    assert seam_delta(a, b) == pytest.approx(0.02, rel=1e-12)


def test_seam_delta_is_rms_not_mean_abs() -> None:
    """Mixed-magnitude differences reduce as RMS: sqrt(2e-4), not 4e-2/3.

    diffs = (-0.01, 0.01, -0.02) -> RMS = sqrt((1+1+4)*1e-4/3) = sqrt(2e-4).

    Bug caught: implementing mean absolute difference (0.01333...) or plain
    mean (-0.00667) instead of root-mean-square.
    """
    a = np.zeros(3)
    b = np.array([0.01, -0.01, 0.02])
    assert seam_delta(a, b) == pytest.approx(math.sqrt(2e-4), rel=1e-12)


def test_seam_delta_excludes_nan_nodes() -> None:
    """A NaN node on either field is excluded from the co-located pool.

    With one NaN node the two surviving diffs are both 0.02 -> RMS 0.02.

    Bug caught: NaN propagation turning the whole seam delta into NaN.
    """
    a = np.array([1.00, 1.00, np.nan])
    b = np.full(3, 1.02)
    assert seam_delta(a, b) == pytest.approx(0.02, rel=1e-12)


def test_seam_delta_all_nan_refuses() -> None:
    """An all-NaN seam refuses (ValueError matching "all-NaN").

    Bug caught: returning NaN (or 0.0) for a seam with no ocean nodes,
    which would silently produce a CLEAN verdict on no data.
    """
    a = np.full(3, np.nan)
    b = np.full(3, 1.02)
    with pytest.raises(ValueError, match="all-NaN"):
        seam_delta(a, b)


def test_seam_delta_shape_mismatch_refuses() -> None:
    """Fields of different shapes refuse instead of broadcasting.

    Bug caught: silent numpy broadcasting (e.g. (3,) vs (3,1)) computing a
    plausible-looking RMS over a 3x3 outer-difference grid.
    """
    with pytest.raises(ValueError, match="shape"):
        seam_delta(np.zeros(3), np.zeros(2))


# ---------------------------------------------------------------------------
# seam_verdict — pre-registered cells, thresholds read at call time
# ---------------------------------------------------------------------------


def test_seam_verdict_sealed_boundary_semantics() -> None:
    """Exact cell boundaries: R <= 1.0 CLEAN, <= 2.5 ELEVATED, else STOP.

    Pins both boundary points and their immediate float successors under
    the sealed config (clean_max=1.0, elevated_max=2.5).

    Bug caught: strict ``<`` instead of ``<=`` at either boundary (1.0
    would wrongly read ELEVATED; 2.5 would wrongly read STRUCTURAL_STOP).
    """
    assert seam_verdict(0.0) == "CLEAN"
    assert seam_verdict(1.0) == "CLEAN"
    assert seam_verdict(float(np.nextafter(1.0, 2.0))) == "ELEVATED"
    assert seam_verdict(2.5) == "ELEVATED"
    assert seam_verdict(float(np.nextafter(2.5, 3.0))) == "STRUCTURAL_STOP"


def test_seam_verdict_reads_config_at_call_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Thresholds come from ``instrument_configs()`` at CALL time.

    A sentinel config (clean_max=0.3, elevated_max=0.5) monkeypatched in
    AFTER import must change the verdict: 0.4 -> ELEVATED, 0.6 ->
    STRUCTURAL_STOP (both would be CLEAN under the sealed 1.0/2.5).

    Bug caught: caching the thresholds at import time (module-level
    constants), which would silently ignore the sealed-config source of
    truth and keep reporting CLEAN here.
    """

    def sentinel_configs() -> dict[str, Any]:
        return {"seam": {"clean_max": 0.3, "elevated_max": 0.5}}

    monkeypatch.setattr(seam_metrics, "instrument_configs", sentinel_configs)
    assert seam_verdict(0.4) == "ELEVATED"
    assert seam_verdict(0.6) == "STRUCTURAL_STOP"


def test_seam_verdict_non_finite_refuses() -> None:
    """A non-finite ratio refuses (ValueError) instead of classifying.

    NaN fails every ``<=`` comparison, so a naive implementation would
    silently return STRUCTURAL_STOP for NaN and CLEAN would be impossible
    to distinguish from a poisoned pipeline.

    Bug caught: NaN or inf flowing through the comparisons into a verdict.
    """
    with pytest.raises(ValueError, match="finite"):
        seam_verdict(float("nan"))


# ---------------------------------------------------------------------------
# seam_read — residual validity guard + assembled reading
# ---------------------------------------------------------------------------


def _valid_read_kwargs() -> dict[str, float]:
    """Solve-quality kwargs for a pair of converged PCG solves."""
    return {
        "final_rel_residual_a": 1e-9,
        "rtol_a": 1e-7,
        "final_rel_residual_b": 1e-9,
        "rtol_b": 1e-7,
    }


class _SigmaKwargs(TypedDict):
    """The four member-std (σ-route) inputs of a ``seam_read`` call."""

    sigma_seam_a: np.ndarray
    sigma_seam_b: np.ndarray
    sigma_interior_a: np.ndarray
    sigma_interior_b: np.ndarray


def _sigma_read_kwargs() -> _SigmaKwargs:
    """Valid member-std (σ-route) inputs for a ``seam_read`` call.

    Hand values, distinct from every mean-side fixture: σ seams differ by
    a constant 0.2 on 3 nodes (RMS(sigma_delta) = 0.2); σ interiors are
    2x the 4x4 arange (axis-1 increments all 2.0 -> D_int_sigma = 2.0),
    so R_seam_sigma = 0.1 -> CLEAN under the sealed thresholds.
    """
    return {
        "sigma_seam_a": np.zeros(3),
        "sigma_seam_b": np.full(3, 0.2),
        "sigma_interior_a": 2.0 * _arange_4x4(),
        "sigma_interior_b": 2.0 * _arange_4x4(),
    }


def test_seam_read_hand_values_clean() -> None:
    """Full reading on hand-computable inputs: delta 0.5, D_int 1.0, R 0.5.

    Interiors are 4x4 aranges (axis-1 increments all 1.0 -> pooled D_int
    exactly 1.0); seams are 0.0 vs 0.5 on 3 nodes (RMS delta 0.5). So
    R = 0.5/1.0 = 0.5 -> CLEAN under the sealed thresholds.

    Bug caught: an inverted ratio (D_int/delta = 2.0 would flip the
    verdict to ELEVATED) or delta/D_int wired to the wrong operands.
    """
    reading = seam_read(
        np.zeros(3),
        np.full(3, 0.5),
        _arange_4x4(),
        _arange_4x4(),
        axis=1,
        **_sigma_read_kwargs(),
        **_valid_read_kwargs(),
    )
    assert isinstance(reading, SeamRead)
    assert reading.rms_delta == pytest.approx(0.5, rel=1e-12)
    assert reading.d_int == pytest.approx(1.0, rel=1e-12)
    assert reading.r_seam == pytest.approx(0.5, rel=1e-12)
    assert reading.verdict == "CLEAN"


def test_seam_read_pools_both_interiors() -> None:
    """D_int pools increments from BOTH tiles, then takes one RMS.

    Interior A has axis-1 increments all 1.0 (12 of them), interior B
    (7 x arange) all 7.0 (12 of them): pooled RMS =
    sqrt((12*1 + 12*49)/24) = 5.0 exactly. Averaging the two per-tile RMS
    values would give 4.0 instead.

    Bug caught: computing D_int per tile and averaging, rather than the
    rubric's pooled-interior RMS.
    """
    reading = seam_read(
        np.zeros(3),
        np.full(3, 0.5),
        _arange_4x4(),
        7.0 * _arange_4x4(),
        axis=1,
        **_sigma_read_kwargs(),
        **_valid_read_kwargs(),
    )
    assert reading.d_int == pytest.approx(5.0, rel=1e-12)
    assert reading.r_seam == pytest.approx(0.1, rel=1e-12)


@pytest.mark.parametrize("bad_solve", ["a", "b"])
def test_seam_read_refuses_unconverged_solve(bad_solve: str) -> None:
    """Residual guard: residual above rtol on EITHER solve refuses (ValueError).

    An invalid solve never produces a verdict — the reading must raise
    before any metric arithmetic.

    Bug caught: a missing gate, or a one-sided gate that only checks
    solve A (the ``b`` parametrization would then pass silently).
    """
    kwargs = _valid_read_kwargs()
    kwargs[f"final_rel_residual_{bad_solve}"] = 1e-5  # > rtol of 1e-7
    with pytest.raises(ValueError, match="(?i)residual"):
        seam_read(
            np.zeros(3),
            np.full(3, 0.5),
            _arange_4x4(),
            _arange_4x4(),
            axis=1,
            **_sigma_read_kwargs(),
            **kwargs,
        )


@pytest.mark.parametrize("bad_solve", ["a", "b"])
def test_seam_read_refuses_nan_residual(bad_solve: str) -> None:
    """A NaN final residual (crashed/aborted solve) refuses, never verdicts.

    NaN fails every ``>`` comparison, so a gate written as
    ``if residual > rtol`` silently passes a solve that never reported a
    valid residual at all.

    Bug caught: exactly that NaN-comparison hole — a crashed solve
    reporting NaN residual slipping through the validity gate into a
    verdict.
    """
    kwargs = _valid_read_kwargs()
    kwargs[f"final_rel_residual_{bad_solve}"] = float("nan")
    with pytest.raises(ValueError, match="(?i)residual"):
        seam_read(
            np.zeros(3),
            np.full(3, 0.5),
            _arange_4x4(),
            _arange_4x4(),
            axis=1,
            **_sigma_read_kwargs(),
            **kwargs,
        )


def test_seam_read_all_nan_interiors_refuse() -> None:
    """seam_read's own pooled-interior all-NaN refusal (ValueError).

    Both interiors all-NaN leave an empty pooled increment set; the
    reading must refuse rather than divide by an empty-pool D_int.

    Bug caught: a refactor dropping seam_read's pooled-size check (the
    ratio would become NaN/undefined instead of a clear refusal).
    """
    with pytest.raises(ValueError, match="all-NaN"):
        seam_read(
            np.zeros(3),
            np.full(3, 0.5),
            np.full((4, 4), np.nan),
            np.full((4, 4), np.nan),
            axis=1,
            **_sigma_read_kwargs(),
            **_valid_read_kwargs(),
        )


def test_seam_read_residual_exactly_at_rtol_is_valid() -> None:
    """A solve whose final residual EQUALS its rtol converged; no refusal.

    PCG stops when the residual drops to <= rtol, so equality is a valid
    converged solve.

    Bug caught: a ``>=`` gate refusing solves that converged exactly at
    tolerance.
    """
    kwargs = _valid_read_kwargs()
    kwargs["final_rel_residual_a"] = kwargs["rtol_a"]
    reading = seam_read(
        np.zeros(3),
        np.full(3, 0.5),
        _arange_4x4(),
        _arange_4x4(),
        axis=1,
        **_sigma_read_kwargs(),
        **kwargs,
    )
    assert reading.verdict == "CLEAN"


# ---------------------------------------------------------------------------
# seam_read σ route — member-std maps, per-field-kind verdicts (T10)
# ---------------------------------------------------------------------------


def test_seam_read_mean_only_construction_refuses() -> None:
    """A SeamRead built with only the mean-route fields refuses (TypeError).

    The σ fields are required dataclass fields with no defaults, so a read
    missing one route cannot be constructed at all.

    Bug caught: adding the σ fields with defaults (None/NaN), which would
    let a mean-only read silently pass downstream as a complete
    per-field-kind reading.
    """
    with pytest.raises(TypeError):
        SeamRead(  # type: ignore[call-arg]
            rms_delta=0.5,
            d_int=1.0,
            r_seam=0.5,
            verdict="CLEAN",
        )


def test_seam_read_sigma_inputs_required_no_defaults() -> None:
    """Calling seam_read without the σ-side inputs refuses (TypeError).

    The σ inputs are required keyword-only parameters; one call must
    produce BOTH routes or none.

    Bug caught: σ parameters given defaults — in particular a mean-field
    fallback, which would fabricate a σ verdict from mean maps whenever a
    caller forgets the member-std inputs.
    """
    with pytest.raises(TypeError):
        seam_read(  # type: ignore[call-arg]
            np.zeros(3),
            np.full(3, 0.5),
            _arange_4x4(),
            _arange_4x4(),
            axis=1,
            final_rel_residual_a=1e-9,
            rtol_a=1e-7,
            final_rel_residual_b=1e-9,
            rtol_b=1e-7,
        )


def test_seam_read_sigma_hand_values_distinct_from_mean() -> None:
    """σ route hand values, distinct from the mean route's on the same call.

    Mean route: seams 0.0 vs 0.5 on 3 nodes, interiors 4x4 aranges ->
    RMS(delta) 0.5, D_int 1.0, R 0.5. σ route: σ seams 0.0 vs 0.09 ->
    RMS(sigma_delta) 0.09; σ interiors 3x arange (axis-1 increments all
    3.0) -> D_int_sigma 3.0; R_seam_sigma = 0.03. Every σ value differs
    from its mean counterpart.

    Bug caught: a route swap — r_seam_sigma computed from the mean fields
    would read 0.5 (not 0.03), and r_seam computed from the σ fields would
    read 0.03 (not 0.5).
    """
    reading = seam_read(
        np.zeros(3),
        np.full(3, 0.5),
        _arange_4x4(),
        _arange_4x4(),
        axis=1,
        sigma_seam_a=np.zeros(3),
        sigma_seam_b=np.full(3, 0.09),
        sigma_interior_a=3.0 * _arange_4x4(),
        sigma_interior_b=3.0 * _arange_4x4(),
        **_valid_read_kwargs(),
    )
    assert reading.rms_delta == pytest.approx(0.5, rel=1e-12)
    assert reading.d_int == pytest.approx(1.0, rel=1e-12)
    assert reading.r_seam == pytest.approx(0.5, rel=1e-12)
    assert reading.rms_sigma_delta == pytest.approx(0.09, rel=1e-12)
    assert reading.d_int_sigma == pytest.approx(3.0, rel=1e-12)
    assert reading.r_seam_sigma == pytest.approx(0.03, rel=1e-12)
    assert reading.verdict == "CLEAN"
    assert reading.verdict_sigma == "CLEAN"


def test_seam_read_verdicts_independent_per_field_kind() -> None:
    """Verdict cells apply independently per field kind on one read.

    Mean route R = 0.5 -> CLEAN; σ route with σ seams 0.0 vs 3.0 and σ
    interiors plain aranges gives R_seam_sigma = 3.0 -> STRUCTURAL_STOP
    under the sealed thresholds (clean_max=1.0, elevated_max=2.5).

    Bug caught: a single combined verdict — verdict_sigma copied from the
    mean cell (would read CLEAN) or the mean verdict driven by the σ ratio
    (would read STRUCTURAL_STOP).
    """
    reading = seam_read(
        np.zeros(3),
        np.full(3, 0.5),
        _arange_4x4(),
        _arange_4x4(),
        axis=1,
        sigma_seam_a=np.zeros(3),
        sigma_seam_b=np.full(3, 3.0),
        sigma_interior_a=_arange_4x4(),
        sigma_interior_b=_arange_4x4(),
        **_valid_read_kwargs(),
    )
    assert reading.verdict == "CLEAN"
    assert reading.verdict_sigma == "STRUCTURAL_STOP"


def test_seam_read_sentinel_config_flips_both_verdict_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both verdict routes read ``instrument_configs()`` at CALL time.

    Sentinel thresholds (clean_max=0.3, elevated_max=0.5) monkeypatched in
    AFTER import: mean R = 0.4 -> ELEVATED and σ R = 0.6 ->
    STRUCTURAL_STOP (BOTH would be CLEAN under the sealed 1.0/2.5).

    Bug caught: the σ route caching thresholds at import time, or the
    call-time config read applied to only one field kind (the other
    verdict would stay CLEAN here).
    """

    def sentinel_configs() -> dict[str, Any]:
        return {"seam": {"clean_max": 0.3, "elevated_max": 0.5}}

    monkeypatch.setattr(seam_metrics, "instrument_configs", sentinel_configs)
    reading = seam_read(
        np.zeros(3),
        np.full(3, 0.4),
        _arange_4x4(),
        _arange_4x4(),
        axis=1,
        sigma_seam_a=np.zeros(3),
        sigma_seam_b=np.full(3, 0.6),
        sigma_interior_a=_arange_4x4(),
        sigma_interior_b=_arange_4x4(),
        **_valid_read_kwargs(),
    )
    assert reading.verdict == "ELEVATED"
    assert reading.verdict_sigma == "STRUCTURAL_STOP"


def test_seam_read_invalid_solve_refuses_before_sigma_arithmetic() -> None:
    """One invalid solve refuses the WHOLE read, before any σ arithmetic.

    Solve B's residual exceeds rtol AND the σ interiors are all-NaN: the
    refusal must be the residual guard's (matching "residual"), not the σ
    pool's ("all-NaN"), proving no σ-only metric is ever computed from a
    bad solve.

    Bug caught: the σ route computed ahead of (or despite) the residual
    guard — the error would match "all-NaN" instead, and a rearrangement
    could leak a σ verdict from an unconverged solve.
    """
    kwargs = _valid_read_kwargs()
    kwargs["final_rel_residual_b"] = 1e-5  # > rtol of 1e-7
    with pytest.raises(ValueError, match="(?i)residual"):
        seam_read(
            np.zeros(3),
            np.full(3, 0.5),
            _arange_4x4(),
            _arange_4x4(),
            axis=1,
            sigma_seam_a=np.zeros(3),
            sigma_seam_b=np.full(3, 0.2),
            sigma_interior_a=np.full((4, 4), np.nan),
            sigma_interior_b=np.full((4, 4), np.nan),
            **kwargs,
        )


def test_seam_read_all_nan_sigma_interiors_refuse() -> None:
    """All-NaN σ interiors refuse (ValueError naming the σ pool).

    Valid mean inputs with both σ interiors all-NaN leave an empty pooled
    σ increment set; the read must refuse rather than emit a NaN
    D_int_sigma.

    Bug caught: a missing σ-pool size check — R_seam_sigma would become
    NaN and either poison the record or crash later in seam_verdict with
    a message that no longer names the offending pool.
    """
    with pytest.raises(ValueError, match="all-NaN sigma"):
        seam_read(
            np.zeros(3),
            np.full(3, 0.5),
            _arange_4x4(),
            _arange_4x4(),
            axis=1,
            sigma_seam_a=np.zeros(3),
            sigma_seam_b=np.full(3, 0.2),
            sigma_interior_a=np.full((4, 4), np.nan),
            sigma_interior_b=np.full((4, 4), np.nan),
            **_valid_read_kwargs(),
        )


def test_seam_read_all_nan_sigma_seam_refuses() -> None:
    """An all-NaN σ seam refuses instead of producing a σ verdict.

    Valid mean inputs; σ seam side A is all-NaN, so the σ route has no
    finite co-located pair and must refuse via the shared seam_delta
    refusal (ValueError matching "all-NaN").

    Bug caught: the σ seam bypassing seam_delta's all-NaN refusal (e.g. a
    nan-ignoring shortcut returning 0.0), which would report a CLEAN σ
    verdict on no data.
    """
    with pytest.raises(ValueError, match="all-NaN"):
        seam_read(
            np.zeros(3),
            np.full(3, 0.5),
            _arange_4x4(),
            _arange_4x4(),
            axis=1,
            sigma_seam_a=np.full(3, np.nan),
            sigma_seam_b=np.full(3, 0.2),
            sigma_interior_a=2.0 * _arange_4x4(),
            sigma_interior_b=2.0 * _arange_4x4(),
            **_valid_read_kwargs(),
        )
