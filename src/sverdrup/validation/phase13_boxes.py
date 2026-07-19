"""Phase-13 pre-registered sweep boxes + designations (sealed via Task 6).

SOURCE TABLE (owner pin: quoted VERBATIM in the gate-1 pack; the
verify-at-review marks RESOLVE at gate 1, by owner verification, before
any touch authorization — spec §3/§4, plan Task 12):

    | Quantity | Basis | Source | Status |
    |---|---|---|---|
    | δ boxes ±0.7 (×2 in σ² either way) | published per-mission noise
      levels are RELATIVE contrasts only: Ka-band AltiKa (alg) low noise
      vs HY-2A (h2g) high noise; published values inform the boxes, the
      tuner sets the values (σ²_m never quoted as physical noise) |
      mission noise characterizations in the altimetry literature
      [verify-at-review: owner confirms the alg-low / h2g-high ordering
      and that ×2 brackets the published spread] | verify-at-review |
    | Λ boxes log10 ∈ [−6, −2.5] m² (σ_mode ≈ 1–56 mm) | challenge L3
      inputs are CMEMS DT2021 corrected SLA INCLUDING long-wavelength-
      error corrections (DAC / ocean tide / LWE) → the target is the
      RESIDUAL orbit/LWE structure post-correction, cm-order |
      ballarotta2023 extraction (brief input-SSH row); spec §17
      [verify-at-review: owner confirms the cm-order residual reading of
      the DT2021 correction chain] | verify-at-review |
    | R diagonal precedent | R is diagonal in all three family papers;
      real-data R values are NOT specified in any paper — the structured
      R extends the family's own state-augmentation pattern | U2021
      §2.2.1/2.2.2; B2023 App. A1 (spec §17, verified from extractions)
      | verified-in-spec |

Everything here is CLAIM-BEARING pre-registration: the Task-6 bundle
seals these constants (restated inside ``phase13_band_artifact.json``);
editing this module after the seal voids the artifact's restatement and
the tamper check refuses bands.
"""

from __future__ import annotations

# --- Sweep boxes (spec §3/§4; §19.2 fixed here) ---------------------------
# Per swept contrast delta_m (log-variance): +-0.7 ~ x2 in sigma^2 each way.
DELTA_BOX: tuple[float, float] = (-0.7, 0.7)
SWEPT_DELTAS: tuple[str, ...] = ("alg", "h2g", "j2g", "j2n")
# Derived balance: delta_s3a = -sum of the four -> range is +-4*0.7.
DELTA_S3A_DERIVED_RANGE: tuple[float, float] = (-2.8, 2.8)
# Shared mode priors, log10 m^2: sigma_mode ~ 1 mm (floor) to ~56 mm (cap),
# bracketing cm-order post-LWE residual budgets (source table above).
LOG10_LAM_BOX: tuple[float, float] = (-6.0, -2.5)
# rho reopened in lanes D/C: the signed value +-1 decade (log10_rho box),
# centered on the signed -1.5990709075704217 (spec §4: rho is the scalar
# data-vs-prior gauge the per-mission contrasts re-parameterize).
LOG10_RHO_BOX: tuple[float, float] = (-2.5990709075704217, -0.5990709075704217)

# --- Sobol engine + dim assignment (spec §7; ONE engine, per-lane MASKING,
# NO per-lane engines — pairing must survive) ------------------------------
SOBOL_ENGINE_KEY: tuple[str, str, str, int] = ("miost", "phase13-lanes", "sobol", 0)
SOBOL_DIMS: tuple[str, ...] = (
    "delta_alg",
    "delta_h2g",
    "delta_j2g",
    "delta_j2n",
    "log10_rho",
    "log_lam_bias",
    "log_lam_tilt",
)

# --- Designations (spec §4/§7/§10) ----------------------------------------
PRIMARY_COMPARISON = "lane-C winner vs lane-0 (claim-bearing, sealed bands)"
SECONDARY_COMPARISONS = (
    "lane-D winner vs lane-0 (ATTRIBUTION secondary; same bands; never claim-bearing)",
    "modes-only winner vs lane-0 (conditional lane; attribution 2x2 cell; "
    "never claim-bearing)",
)
WINNER_LANE_RULE = (
    "C-vs-D within band -> lane-D takes the acceptance chain (simpler lane "
    "on tie, spec §10)"
)
MODES_ONLY_CONDITIONAL_RULE = (
    "modes-only lane runs iff the probe-derived budget covers three sweeping "
    "lanes at n >= the floor (n3 >= 8); else 'not run' recorded with the "
    "probe arithmetic as reason (spec §7)"
)

# --- Negative wording (spec §7/§16; pinned VERBATIM) ----------------------
NEGATIVE_WORDING = "improvements within band"
NEGATIVE_SCOPE_CLAUSE = "under this search (recorded n/lane, wall, screening state)"
NEGATIVE_FRAMING = (
    "recorded as a measurement of the box-scale residual-error budget's "
    "size; no touch; measured-not-shipped (Phase-10 precedent verbatim)"
)

# --- Degradation criteria (spec §7; §19.5 fixed here) ---------------------
N_LAMBDA_USED_MIN_FRAC = 0.5  # usability fraction: n_lambda_used >= 50%
BAND_LAMBDA_X_MAX_KM = 25.0  # band-width rule (Phase-10 family value carried)
DEGRADATION_DEVIATION_NOTE = (
    "DEVIATION from Phase-10 (width-only rule): phase-13 requires BOTH the "
    "usability fraction (n_lambda_used >= 50%) AND the band-width rule "
    "(band_lambda_x <= 25 km) before the lambda tie-break fires — protocol "
    "families never fork silently, so the addition is recorded here with "
    "its reason: a wide-but-usable band and a narrow-but-sparse band are "
    "different failures and each alone must degrade to mu-primary"
)
