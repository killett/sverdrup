"""Tests for the result report assembly + decomposed-read classifier (design §6)."""

from sverdrup.validation.report import ResultRow, classify_result, render_table


def _row(mu=0.85, sigma=0.09, lambda_x=140.0):
    return ResultRow(mu=mu, sigma=sigma, lambda_x=lambda_x)


def test_classifier_flags_eval_layer_disagreement():
    """When our eval disagrees with theirs on the SAME map -> case (iii).

    Catches a classifier that would mislabel an eval-layer bug as a pass/miss.
    """
    verdict = classify_result(
        ours=_row(0.86, 0.09, 141),
        baseline_published=_row(0.85, 0.09, 140),
        baseline_reproduced=_row(0.85, 0.09, 140),
        our_eval_mu_same_map=0.95,  # disagrees with their 0.86 on our map
        tol_mu=0.03,
    )
    assert verdict.code == "iii"


def test_classifier_flags_harness_skew_first():
    """If the sanity anchor itself can't be reproduced -> case (ii), checked first.

    Catches a classifier that blames our OI when the eval harness is the bug.
    """
    verdict = classify_result(
        ours=_row(0.85),
        baseline_published=_row(0.85),
        baseline_reproduced=_row(0.70),  # cannot reproduce the anchor
        our_eval_mu_same_map=0.85,
        tol_mu=0.03,
    )
    assert verdict.code == "ii"


def test_classifier_flags_oi_mismatch():
    """Anchor + eval agree but our OI scores off -> case (i) parameter mismatch.

    Catches a classifier that calls a real OI mismatch a PASS.
    """
    verdict = classify_result(
        ours=_row(0.70, 0.09, 140),
        baseline_published=_row(0.85, 0.09, 140),
        baseline_reproduced=_row(0.85, 0.09, 140),
        our_eval_mu_same_map=0.70,
        tol_mu=0.03,
    )
    assert verdict.code == "i"


def test_classifier_passes_when_all_agree():
    """Anchor reproduces, evals agree, our OI matches BASELINE -> PASS.

    Catches an over-strict classifier that fails a genuine reproduction.
    """
    verdict = classify_result(
        ours=_row(0.855, 0.09, 139),
        baseline_published=_row(0.85, 0.09, 140),
        baseline_reproduced=_row(0.851, 0.09, 140),
        our_eval_mu_same_map=0.857,
        tol_mu=0.03,
    )
    assert verdict.code == "PASS"


def test_render_table_contains_rows_and_verdict():
    """RESULT.md body carries the ours/BASELINE/DUACS rows + the verdict + tol.

    Catches a report that drops the comparison rows or the decomposed read.
    """
    verdict = classify_result(
        ours=_row(0.85),
        baseline_published=_row(0.85),
        baseline_reproduced=_row(0.85),
        our_eval_mu_same_map=0.85,
        tol_mu=0.03,
    )
    md = render_table(
        ours=_row(0.85),
        baseline_published=_row(0.85, 0.09, 140),
        duacs_published=_row(0.88, 0.07, 152),
        sanity_reproduced=_row(0.877, 0.065, 152.3),
        sanity_name="DUACS",
        our_eval_mu_same_map=0.85,
        verdict=verdict,
        tol_mu=0.03,
    )
    assert "ours (OI)" in md
    assert "BASELINE (published)" in md
    assert "DUACS (published)" in md
    assert "Verdict: PASS" in md
    assert "±0.03" in md
