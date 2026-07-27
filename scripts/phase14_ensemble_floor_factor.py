"""DERIVE the Rule-0.b attributability factor (owner ruling 2026-07-27, pin 36).

Pin 36 rejected the 3x factor carried over from the solver floor: the
solver floor bounds a DETERMINISTIC quantity where 3x is a margin, while
``F_ens`` is the expectation of a sampling statistic whose null
distribution is tightly concentrated. A 3x threshold discards any true
artifact below ~2.8x the floor, and at the recorded geometry it leaves the
sigma instrument with NO reachable CLEAN or ELEVATED cell.

This script derives the factor from the null distribution instead of
picking one, and records the derivation beside the constant:

1. Measure the effective independent node count ``N_eff`` of a RECORDED
   null realization on the 2*overlap strip. The realization used is the
   cross-tile sigma difference ``sigma_n - sigma_s``, which the T4
   diagnosis established IS pure ensemble Monte-Carlo noise (the two tiles
   draw independent CRN because their pavement origins differ) — so it is
   a null field measured on the true spatial AND temporal correlation
   structure. No solves.
2. Simulate the null of ``T = RMS(sigma_delta)/F_ens`` at the production
   ``m``, at that ``N_eff``, both equal-weighted and weighted by the
   recorded sigma-level heterogeneity.
3. Set the factor from a stated upper quantile plus an explicit margin for
   the model assumptions (Gaussian members, separable correlation,
   one-realization ACF bias, the exact-vs-asymptotic floor gap).
4. Check the pin-36c reachability condition and report the smallest ``m``
   at which a CLEAN sigma verdict becomes reachable at all.
5. Cross-check the predicted spread against the two RECORDED half-split
   realizations at m=50 (0.9829 and 1.0036) — an independent measurement
   the simulation never saw.

NO SOLVES. Reads persisted maps and recorded numbers only.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import numpy as np
import typer

from sverdrup.validation.ensemble_floor_null import (
    clean_reachable,
    effective_node_count,
    min_m_for_clean,
    node_term_moments,
    null_t_quantile,
    null_t_samples,
)

app = typer.Typer(add_completion=False)

EVIDENCE = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")
NODE = "ensemble_floor_factor_derivation"

# Stated confidence for the one-sided attributability quantile: a null
# reading is called attributable at most this often. One row in a thousand
# is the tolerance for FALSELY reading a seamless solve as a seam signal.
CONFIDENCE = 0.999
# Explicit margin on the derived quantile, covering (stated, not hidden):
#  - Gaussianity of the member perturbations (the chi2 null),
#  - separability of the correlation across (time, lat, lon) in N_eff,
#  - single-realization bias in the measured autocorrelation,
#  - the exact-vs-asymptotic floor gap (E[T] = 0.99873 at m=100, so the
#    sigma/sqrt(m-1) floor already sits 0.13% high).
MARGIN = 1.05
K_SAMPLES = 200_000
# Pool for the per-node moment estimates (one pass, no replication loop).
N_POOL = 100_000_000
SEED = 20260727
# The two RECORDED half-split T values (m=50), diagnosis line 4 — an
# independent check the simulation never saw.
RECORDED_HALF_SPLIT_T = {"seam_n": 0.9829219928254623, "seam_s": 1.0035663634063174}


def _quantile_summary(t: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(t)),
        "sd": float(np.std(t, ddof=1)),
        "q50": float(np.quantile(t, 0.5)),
        "q99": float(np.quantile(t, 0.99)),
        "q999": float(np.quantile(t, 0.999)),
        "q9999": float(np.quantile(t, 0.9999)),
        "max": float(np.max(t)),
    }


def _weights_for(sigma_level_field: np.ndarray, n_eff: int) -> np.ndarray:
    """Coarse-grain the recorded sigma^2 heterogeneity onto N_eff nodes.

    Uses evenly spaced quantiles of the per-node sigma^2 distribution, so
    the effective nodes carry the recorded spread without any RNG.

    Args:
        sigma_level_field: Per-node sigma values over the domain.
        n_eff: Effective independent node count.

    Returns:
        ``(n_eff,)`` positive weights.
    """
    finite = sigma_level_field[np.isfinite(sigma_level_field)] ** 2
    qs = (np.arange(n_eff) + 0.5) / n_eff
    w: np.ndarray = np.asarray(np.quantile(finite, qs), dtype=np.float64)
    floored: np.ndarray = np.maximum(w, float(np.max(w)) * 1e-12)
    return floored


@app.command()
def derive(
    evidence_path: Annotated[Path, typer.Option("--evidence-path")] = EVIDENCE,
    k: Annotated[int, typer.Option(help="Null replications")] = K_SAMPLES,
    record: Annotated[bool, typer.Option(help="Write the evidence block")] = True,
) -> None:
    """Derive the factor, check reachability, record the derivation."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(
        "phase14_stage1_run", Path(__file__).with_name("phase14_stage1_run.py")
    )
    if spec is None or spec.loader is None:  # pragma: no cover - import plumbing
        raise RuntimeError("cannot load phase14_stage1_run")
    stage1 = importlib.util.module_from_spec(spec)
    sys.modules["phase14_stage1_run"] = stage1
    spec.loader.exec_module(stage1)

    results = json.loads(evidence_path.read_text())
    s1 = results["phase14"]["stage1"]
    m = int(s1["seam_pair"]["m"])
    rows = {(r["route"], r["field_kind"]): r for r in s1["seam_rows"]}
    pair_sigma = rows[("pair", "sigma")]
    d_int_sigma = float(pair_sigma["d_int"])

    north, south = stage1.SEAM_PAIR_TILES
    sig = {t: stage1._strip_fields(stage1.SEAM_STD_MAPS[t], t) for t in (north, south)}
    null_field = sig[north] - sig[south]
    from sverdrup.validation.seam_metrics import ensemble_floor, sigma_level_rms

    sigma_level = sigma_level_rms(sig[north], sig[south])
    f_ens = ensemble_floor(sigma_level, m)

    n_total = int(np.isfinite(null_field).sum())
    n_eff = int(round(effective_node_count(null_field)))
    typer.echo(
        f"null realization: cross-tile sigma difference on the strip, "
        f"shape {null_field.shape}, N={n_total}, N_eff={n_eff} "
        f"(ratio {n_eff / n_total:.4g})"
    )

    weights = _weights_for(
        np.concatenate([sig[north].ravel(), sig[south].ravel()]), n_eff
    )
    # Per-node moments once, then the quantile analytically at ANY N_eff:
    # the direct product k * N_eff is ~1e10 draws at this N_eff, which is
    # not a derivation anyone re-runs. The predictor is VALIDATED against
    # the direct harness at affordable N_eff below.
    moments = node_term_moments(m=m, n_pool=N_POOL, seed=SEED)
    q_flat = null_t_quantile(moments=moments, n_eff=n_eff, confidence=CONFIDENCE)
    q_wtd = null_t_quantile(
        moments=moments, n_eff=n_eff, confidence=CONFIDENCE, weights=weights
    )
    quantile = max(q_flat, q_wtd)
    factor = float(np.ceil(quantile * MARGIN * 100.0) / 100.0)

    validation = []
    for n_val, k_val in ((2_000, k), (8_000, max(k // 4, 10_000))):
        direct = _quantile_summary(
            null_t_samples(m=m, n_eff=n_val, k=k_val, seed=SEED + 3 + n_val)
        )
        pred = null_t_quantile(moments=moments, n_eff=n_val, confidence=CONFIDENCE)
        validation.append(
            {
                "n_eff": n_val,
                "k": k_val,
                "direct_q999": direct["q999"],
                "predicted_q999": pred,
                "rel_error": abs(pred - direct["q999"]) / direct["q999"],
                "direct_mean": direct["mean"],
                "direct_sd": direct["sd"],
            }
        )
        typer.echo(
            f"validation n_eff={n_val} k={k_val}: direct q999 "
            f"{direct['q999']:.5f} vs predicted {pred:.5f} "
            f"(rel {validation[-1]['rel_error']:.2e})"
        )
    worst_rel = max(v["rel_error"] for v in validation)
    flat = {
        "mean_t": float(np.sqrt(moments["mean"])),
        "q999": q_flat,
        "per_node_mean": moments["mean"],
        "per_node_var": moments["var"],
        "per_node_skew": moments["skew"],
    }
    wtd = {
        "q999": q_wtd,
        "effective_count": 1.0 / float(np.sum((weights / weights.sum()) ** 2)),
    }

    reachable = clean_reachable(
        factor=factor, f_ens=f_ens, clean_max=1.0, d_int_sigma=d_int_sigma
    )
    m_needed = min_m_for_clean(
        factor=factor, sigma_level=sigma_level, clean_max=1.0, d_int_sigma=d_int_sigma
    )
    m_needed_at_three = min_m_for_clean(
        factor=3.0, sigma_level=sigma_level, clean_max=1.0, d_int_sigma=d_int_sigma
    )

    # Independent cross-check at m=50 against the recorded half-splits.
    mom50 = node_term_moments(m=50, n_pool=N_POOL // 5, seed=SEED + 2)
    half = {
        "mean_t": float(np.sqrt(mom50["mean"])),
        "sd_t": float(np.sqrt(mom50["var"] / n_eff) / (2.0 * np.sqrt(mom50["mean"]))),
        "q999": null_t_quantile(moments=mom50, n_eff=n_eff, confidence=CONFIDENCE),
    }
    lo, hi = (
        float(np.quantile(np.array(list(RECORDED_HALF_SPLIT_T.values())), 0.0)),
        float(np.quantile(np.array(list(RECORDED_HALF_SPLIT_T.values())), 1.0)),
    )
    covered = bool(
        lo >= half["mean_t"] - 4 * half["sd_t"]
        and hi <= half["mean_t"] + 4 * half["sd_t"]
    )

    typer.echo(
        f"null T at m={m}, N_eff={n_eff}: E[T] {flat['mean_t']:.5f}, "
        f"q{CONFIDENCE} {q_flat:.5f} equal-weight / {q_wtd:.5f} sigma-weighted "
        f"(weighted effective count {wtd['effective_count']:.0f}); predictor "
        f"validated to {worst_rel:.2e}"
    )
    typer.echo(
        f"DERIVED FACTOR = {factor:.2f}  (q{CONFIDENCE} {quantile:.4f} x margin "
        f"{MARGIN}) — was 3.0 by carry-over"
    )
    typer.echo(
        f"reachability: factor x F_ens = {factor * f_ens:.7g} vs clean_max x "
        f"D_int_sigma = {d_int_sigma:.7g} -> CLEAN "
        f"{'REACHABLE' if reachable else 'NOT REACHABLE'} at m={m}; "
        f"CLEAN needs m >= {m_needed} (at the old 3.0: m >= {m_needed_at_three})"
    )
    typer.echo(
        f"m=50 cross-check: recorded half-split T {lo:.4f}/{hi:.4f} vs predicted "
        f"E[T] {half['mean_t']:.4f} sd {half['sd_t']:.5f} -> "
        f"{'CONSISTENT' if covered else 'INCONSISTENT'}"
    )

    if not record:
        return
    block: dict[str, Any] = {
        "label": "DERIVATION",
        "ruling": "docs/superpowers/2026-07-27-owner-ruling-crn-sigma-rule0.md",
        "pin": "36(b) — DERIVE the factor, do not pick one",
        "quantity": "T = RMS(sigma_delta) / F_ens under the null of NO seam",
        "construction": (
            "for Gaussian members s = F_ens*sqrt(chi2_{m-1}) exactly, so T is "
            "the (sigma^2-weighted) RMS over effectively-independent nodes of "
            "sqrt(chi2_a) - sqrt(chi2_b); scale-free in sigma"
        ),
        "null_realization": {
            "field": "cross-tile sigma difference (sigma_n - sigma_s) on the strip",
            "why_it_is_a_null": (
                "the T4 diagnosis established this difference IS pure ensemble "
                "MC noise — the two tiles draw independent CRN because their "
                "pavement origins differ — so it carries the true spatial AND "
                "temporal correlation with no seam signal"
            ),
            "caveat": (
                "the two tiles solve on different lattices, so this null's "
                "correlation is not exactly that of a within-configuration null; "
                "stated, not hidden"
            ),
            "shape_time_lat_lon": list(null_field.shape),
            "n_finite_nodes": n_total,
            "n_eff": n_eff,
            "n_eff_over_n": n_eff / n_total,
            "n_eff_method": (
                "N_eff = N / prod_axes(1 + 2*sum_{lag>0}(1-lag/L)rho(lag)^2); the "
                "(1-lag/L) weight is the exact finite-domain pair count, and "
                "separability across axes is an assumption"
            ),
        },
        "m": m,
        "sigma_level": sigma_level,
        "f_ens": f_ens,
        "d_int_sigma": d_int_sigma,
        "confidence": CONFIDENCE,
        "margin": MARGIN,
        "margin_covers": [
            "Gaussianity of the member perturbations (the chi2 null)",
            "separability of the correlation across (time, lat, lon) in N_eff",
            "single-realization bias in the measured autocorrelation",
            "the exact-vs-asymptotic floor gap (E[T]=0.99873 at m=100)",
        ],
        "k_samples": k,
        "seed": SEED,
        "null_equal_weight": flat,
        "null_sigma_weighted": wtd,
        "predictor": {
            "method": (
                "per-node moments from an N_pool draw pool, then Cornish-Fisher "
                "over N_eff (exact mean/var/skew scaling for arbitrary weights)"
            ),
            "n_pool": N_POOL,
            "validation_vs_direct_simulation": validation,
            "worst_rel_error": worst_rel,
        },
        "quantile_used": quantile,
        "factor_derived": factor,
        "factor_prior_by_carry_over": 3.0,
        "reachability": {
            "condition": "factor * F_ens < clean_max * D_int_sigma (pin 36c)",
            "factor_times_f_ens": factor * f_ens,
            "clean_max_times_d_int_sigma": d_int_sigma,
            "clean_reachable_at_m": reachable,
            "min_m_for_clean": m_needed,
            "min_m_for_clean_at_factor_3": m_needed_at_three,
        },
        "m50_cross_check": {
            "recorded_half_split_t": RECORDED_HALF_SPLIT_T,
            "simulated": half,
            "consistent": covered,
            "note": (
                "the recorded half-splits are two independent null realizations "
                "at m=50 on the real geometry; the simulation never saw them"
            ),
        },
        "no_solves_run": True,
        "date": datetime.now(UTC).date().isoformat(),
    }
    s1[NODE] = block
    from sverdrup.application.calibration.harness import atomic_write_json

    atomic_write_json(evidence_path, results)
    typer.echo(f"recorded: phase14.stage1.{NODE}")


if __name__ == "__main__":
    app()
