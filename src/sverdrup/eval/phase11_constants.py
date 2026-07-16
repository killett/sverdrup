"""Phase-11 pre-registered constants (spec §1 pins; owner plan-approval obligations 1, 2, 5)."""

DERIVATION_VERSION = 2  # orbit-geometry artifact schema/algorithm version
# v2 (2026-07-16): REPEAT_RATIO_MAX corrected 0.5 -> 0.25 (see below); the
# version bump invalidates v1 cache keys so stale artifacts re-derive.

# GroundTrack probe geometry (spec §4).
DTHETA_DEG = 15.0
# Rationale: half the angular resolution element atan(2.25/4) ~= 29 deg at the
# Jason-class radius (bin ~4); covers per-pass heading spread without eating
# the baseline annulus.
DK_HALFWIDTH_BINS = 2.25
# Rationale: leakage-matched — equals the MEASURED radial-Hann mainlobe
# half-width in zonal-fundamental units (see MAINLOBE_HALFWIDTH_BINS).
MAINLOBE_HALFWIDTH_BINS = 2.25  # measured 2026-07-15; test re-measures +-0.1
N_MODES_BASELINE_FLOOR = 8
MAX_WIDENINGS = 3  # symmetric +1 bin per side per widening; beyond -> under_floor flag

# Orbit-class classifier (obligation 2).
CLUSTER_TOL_DEG = 0.05  # ~4.4 km at 38N — far below any track spacing
REPEAT_RATIO_MAX = 0.25
# Rule: cluster the family's phi0-crossing longitudes with tolerance
# CLUSTER_TOL_DEG; orbit_class = "repeat" iff n_clusters / n_crossings <= REPEAT_RATIO_MAX.
# Rationale: a repeat orbit (<= 35 d period) revisits each track >= 10x/year
# -> ratio <= 0.1; a drifting orbit's crossings almost never coincide.
# EXECUTOR-SET CORRECTION (2026-07-16, disclosed for owner ratification at
# the phase-close gate; Phase-10 wall-budget precedent): the plan's
# pre-registered 0.5 assumed drifting ratios ~= 1.0, but on the REAL year of
# obs the dense drifting missions chain under single linkage — measured
# ratios: s3a 0.064 / j2n ~0.14 (true repeat) vs h2g 0.438 / alg 0.464
# (true drifting: SARAL-DP since 2016-07, HY-2A geodetic since 2016-03) —
# so 0.5 misclassified alg/h2g as repeat with fictitious ~9 km spacings.
# 0.25 ~= geometric mean of the CLOSEST measured sides (sqrt(0.14 * 0.438)
# = 0.248), >= 1.75x margin each way.
# Cluster-size evidence corroborates: median cluster size 16 (s3a) vs 2
# (alg/h2g chance pairs).

# Spectral fidelity band rule (spec §5).
BAND_LO_FLOOR_KM = 100.0  # lower edge = max(100, 3 * grid dy_km)
BAND_HI_CAP_KM = 300.0  # upper edge = min(300, Lx / MIN_BIN_INDEX)
MIN_BIN_INDEX = 4

# Evidence/report schema versions (spec §7).
REPORT_SCHEMA_VERSION = 1
