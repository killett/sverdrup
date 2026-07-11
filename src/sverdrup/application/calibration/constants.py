"""Phase-8 pre-registered constants (spec 2026-07-10; plan-pinned values)."""

SIGMA_OBS2 = 0.03**2  # m^2 — obs-noise floor; anchor: Phase-7 spec §2.2 R_ref
S_STAR = 10.062847634082484  # shipped scalar (methods/miost.py STAGE_B_INFLATION_S)
COVERAGE_TARGET = 0.6827
COVERAGE_TOL = 0.10
TIE_BAND = 0.01  # ±1% tie band on the selection statistic
CLIP_PAD = 1.25  # log-s clip pad factor (spec §9), applied as ±log(1.25)

# 2°-cell grid == S-fold block grid (one definition, spec plan-obligation 3):
# lon edges 295,297,...,305; lat edges 33,35,...,43 → 5×5 = 25 cells.
CELL_DEG = 2.0

# T-folds (plan-obligation 1): 6 rotations, verify-2 contiguous months of 2017.
T_FOLDS = (
    ("01", "02"),
    ("03", "04"),
    ("05", "06"),
    ("07", "08"),
    ("09", "10"),
    ("11", "12"),
)

# S-folds (plan-obligation 1): 4 folds over the 25 blocks, sizes (7, 6, 6, 6),
# seeded permutation; salt increments deterministically if the ≥50%-per-fit-region
# constraint fails (recorded).
S_FOLD_COUNT = 4
S_FOLD_SEED_ARGS = ("miost", "phase8", "s-folds")  # + salt as member_index
GUARD_RING_DEG = 0.5

# n_eff (plan-obligation 2): n_eff = n / (1 + 2 * sum(rho_k, k=1..K)),
# K = first k with rho_k < RHO_CUTOFF, capped at RHO_MAX_LAG.
RHO_CUTOFF = 0.05
RHO_MAX_LAG = 20
MIN_N_EFF = 200.0  # per held-out block; below → merge with nearest-centroid
# block in the SAME fold (deterministic, recorded)

# Promotion (plan-obligation 5): PRIMARY = Pearson r(per-cell log chi2_red,
# per-cell log proxy); |r| >= 0.6 promotes. Deficit variant reported alongside.
PROMOTION_R = 0.6

# Optimizers (plan-obligation 6):
NEWTON_MAX_ITER = 50
NEWTON_TOL = 1e-10  # |step| in log s
LBFGSB_GTOL = 1e-8  # scipy L-BFGS-B gtol; method name serialized in fit_id
POLY_MAX_DOF = 6
JET_CORE_QUANTILE = 0.75  # spec §6 mask threshold
