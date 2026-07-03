"""Task-0 MIOST cost probe — measurement only, no method code.

Measures, before the MIOST design session:

(a) actual per-mission observation counts from the 2021a challenge along-track
    files (6 training missions; c2 excluded — eval only), per candidate solve
    window, inside the 10x10 deg Gulf Stream mapping box;
(b) reduced-basis problem sizes (N_coef, nnz(G), stored-G bytes, flops/apply)
    over a grid of candidate configurations;
(c) a micro-benchmark of vectorized wavelet (cos-product) evaluation throughput
    on this machine, replacing any assumed GFLOP/s figure;
(d) a feasibility table plus a recommended local operating envelope.

Sizing model (owner-specified, 2026-07-03):
    spatial positions per scale = ceil(D_x/(alpha*lam)) * ceil(D_y/(alpha*lam))
    per-obs overlapping elements per scale = (3/alpha)^2 * n_dir * 2 * (2*L_t/dt)
    support L = 1.5*lam (diameter 3*lam), L_t = 10 d, pavement dt = 5 d,
    scales geometric from lam_min to <= 800 km.
Assumption (flagged, not in the papers): geometric ratio sqrt(2) — implied by
the probe grid's lam_min in {80, 113} being consecutive sqrt(2) steps.

Usage: pixi run python scripts/probe_miost_cost.py
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import numpy as np
import xarray as xr

DATA_DIR = Path("data/2021a_ssh_mapping_ose/dc_obs")
TRAINING_MISSIONS = ("alg", "h2g", "j2g", "j2n", "j3", "s3a")  # c2 = eval only
BOX_LON = (295.0, 305.0)
BOX_LAT = (33.0, 43.0)
WINDOW_START = np.datetime64("2017-01-01")

ALPHAS = (0.5, 0.75, 1.0, 1.5)
N_DIRS = (8, 12)
WINDOWS_D = (60, 365)
LAM_MINS = (80.0, 113.0)
LAM_MAX = 800.0
SCALE_RATIO = math.sqrt(2.0)
L_T_DAYS = 10.0
DT_DAYS = 5.0
SUPPORT_FACTOR = 1.5  # L = 1.5 * wavelength -> support diameter 3 * wavelength
CG_ITERATIONS = 100  # "typically 100 iterations" (U2022 Sect. 3.2.3)

KM_PER_DEG = 111.32
MID_LAT = 0.5 * (BOX_LAT[0] + BOX_LAT[1])
D_X_KM = (BOX_LON[1] - BOX_LON[0]) * KM_PER_DEG * math.cos(math.radians(MID_LAT))
D_Y_KM = (BOX_LAT[1] - BOX_LAT[0]) * KM_PER_DEG

RAM_BUDGET_BYTES = 16e9 * 0.5  # stored-G must fit in half of a 16 GB machine
SOLVE_BUDGET_S = 3600.0  # one hour per solve


def scale_set(
    lam_min: float, lam_max: float = LAM_MAX, ratio: float = SCALE_RATIO
) -> list[float]:
    """Return the geometric wavelength ladder from lam_min up to lam_max.

    Args:
        lam_min: Smallest wavelength [km].
        lam_max: Largest admissible wavelength [km].
        ratio: Geometric ratio between consecutive scales.

    Returns:
        Wavelengths [km], ascending.
    """
    scales = []
    lam = lam_min
    while lam <= lam_max + 1e-9:
        scales.append(lam)
        lam *= ratio
    return scales


def n_coefficients(alpha: float, n_dir: int, window_days: float, lam_min: float) -> int:
    """Count basis coefficients for one configuration.

    Per scale: spatial positions x temporal positions x directions x 2 phases
    (sine/cosine pairs).

    Args:
        alpha: Element spacing as a fraction of wavelength.
        n_dir: Number of plane-wave directions.
        window_days: Solve window length [days].
        lam_min: Smallest wavelength [km].

    Returns:
        Total coefficient count N_coef.
    """
    n_t = math.ceil(window_days / DT_DAYS)
    total = 0
    for lam in scale_set(lam_min):
        n_x = max(1, math.ceil(D_X_KM / (alpha * lam)))
        n_y = max(1, math.ceil(D_Y_KM / (alpha * lam)))
        total += n_x * n_y * n_t * n_dir * 2
    return total


def nnz_g(n_obs: int, alpha: float, n_dir: int, lam_min: float) -> int:
    """Count non-zeros of G for one configuration.

    Per observation and per scale: (3/alpha)^2 spatial overlaps x n_dir x 2
    phases x (2*L_t/dt) temporal overlaps.

    Args:
        n_obs: Observation count in the window.
        alpha: Element spacing as a fraction of wavelength.
        n_dir: Number of plane-wave directions.
        lam_min: Smallest wavelength [km].

    Returns:
        Total nnz(G).
    """
    per_obs_per_scale = (3.0 / alpha) ** 2 * n_dir * 2 * (2.0 * L_T_DAYS / DT_DAYS)
    return int(round(n_obs * len(scale_set(lam_min)) * per_obs_per_scale))


def count_obs() -> dict[str, dict[int, int]]:
    """Count in-box observations per training mission and per window.

    Returns:
        Mapping mission -> {window_days -> count} for finite-SLA points inside
        the 10x10 deg box with time in [WINDOW_START, WINDOW_START + window).
    """
    counts: dict[str, dict[int, int]] = {}
    for mission in TRAINING_MISSIONS:
        path = next(DATA_DIR.glob(f"dt_gulfstream_{mission}_*.nc"))
        ds = xr.open_dataset(path)
        lon = ds["longitude"].values
        lat = ds["latitude"].values
        t = ds["time"].values
        sla = ds["sla_unfiltered"].values
        in_box = (
            (lon >= BOX_LON[0])
            & (lon <= BOX_LON[1])
            & (lat >= BOX_LAT[0])
            & (lat <= BOX_LAT[1])
            & np.isfinite(sla)
        )
        counts[mission] = {}
        for window in WINDOWS_D:
            end = WINDOW_START + np.timedelta64(window, "D")
            counts[mission][window] = int(
                np.sum(in_box & (t >= WINDOW_START) & (t < end))
            )
        ds.close()
    return counts


def benchmark_basis_eval(n: int = 4_000_000, repeats: int = 5) -> float:
    """Measure vectorized cos-product wavelet evaluation throughput.

    Evaluates cos(kx*dx + ky*dy + phi) * cos(pi/2 dx/L) * cos(pi/2 dy/L)
    * cos(pi/2 dt/Lt) on random inputs (the U2021 Eq. 18-19 element form).

    Args:
        n: Elements evaluated per repeat.
        repeats: Timing repeats; best is returned.

    Returns:
        Measured throughput [element evaluations / s].
    """
    rng = np.random.default_rng(0)
    dx, dy, dt = (rng.uniform(-1, 1, n) for _ in range(3))
    kx, ky, phi = (rng.uniform(0, 2 * np.pi, n) for _ in range(3))
    best = math.inf
    for _ in range(repeats):
        t0 = time.perf_counter()
        out = (
            np.cos(kx * dx + ky * dy + phi)
            * np.cos(0.5 * np.pi * dx)
            * np.cos(0.5 * np.pi * dy)
            * np.cos(0.5 * np.pi * dt)
        )
        best = min(best, time.perf_counter() - t0)
        if out.shape != (n,):  # keep ``out`` live; guard against broadcast bugs
            raise RuntimeError(f"unexpected eval shape {out.shape}")
    return n / best


def benchmark_csr_matvec(
    nnz: int = 20_000_000, n_rows: int = 200_000, repeats: int = 5
) -> float:
    """Measure stored-G (CSR) matvec throughput.

    Args:
        nnz: Non-zeros in the benchmark matrix.
        n_rows: Rows in the benchmark matrix.
        repeats: Timing repeats; best is returned.

    Returns:
        Measured throughput [nnz processed / s] for one matvec.
    """
    from scipy.sparse import csr_matrix  # type: ignore[import-untyped]

    rng = np.random.default_rng(1)
    per_row = nnz // n_rows
    n_cols = 4 * per_row
    indices = rng.integers(0, n_cols, size=n_rows * per_row).astype(np.int32)
    indptr = np.arange(0, n_rows * per_row + 1, per_row, dtype=np.int64)
    data = rng.standard_normal(n_rows * per_row)
    mat = csr_matrix((data, indices, indptr), shape=(n_rows, n_cols))
    vec = rng.standard_normal(n_cols)
    best = math.inf
    for _ in range(repeats):
        t0 = time.perf_counter()
        mat @ vec
        best = min(best, time.perf_counter() - t0)
    return (n_rows * per_row) / best


@dataclass
class ConfigCost:
    """Costs for one probe configuration."""

    alpha: float
    n_dir: int
    window_days: int
    lam_min: float
    n_obs: int
    n_coef: int
    nnz: int

    def stored_g_bytes(self) -> float:
        """Stored-G footprint [bytes]: float64 data + int32 CSR column index."""
        return self.nnz * 12.0

    def solve_s_stored(self, matvec_rate: float) -> float:
        """CG solve wall time with stored G [s]: 2 matvecs/iter x 100 iters."""
        return CG_ITERATIONS * 2.0 * self.nnz / matvec_rate

    def solve_s_matrix_free(self, eval_rate: float) -> float:
        """CG solve wall time matrix-free [s]: 2 basis sweeps/iter x 100 iters."""
        return CG_ITERATIONS * 2.0 * self.nnz / eval_rate


def main() -> None:
    """Run the probe and print the feasibility table."""
    print(
        f"box: lon {BOX_LON} lat {BOX_LAT} -> D_x={D_X_KM:.0f} km, D_y={D_Y_KM:.0f} km"
    )
    print(f"scales(80): {[f'{s:.0f}' for s in scale_set(80.0)]}")
    print(f"scales(113): {[f'{s:.0f}' for s in scale_set(113.0)]}")

    counts = count_obs()
    print("\n(a) in-box obs per training mission (c2 excluded):")
    print(f"{'mission':>8} " + " ".join(f"{w:>9}d" for w in WINDOWS_D))
    for mission, per_window in counts.items():
        print(f"{mission:>8} " + " ".join(f"{per_window[w]:>10,}" for w in WINDOWS_D))
    totals = {w: sum(c[w] for c in counts.values()) for w in WINDOWS_D}
    print(f"{'TOTAL':>8} " + " ".join(f"{totals[w]:>10,}" for w in WINDOWS_D))

    print("\n(c) micro-benchmarks (best of 5):")
    eval_rate = benchmark_basis_eval()
    matvec_rate = benchmark_csr_matvec()
    print(f"  basis eval (cos-product): {eval_rate / 1e6:,.0f} M elem/s")
    print(f"  stored-G CSR matvec:      {matvec_rate / 1e6:,.0f} M nnz/s")

    print(
        "\n(b)+(d) feasibility table "
        f"(budgets: stored-G <= {RAM_BUDGET_BYTES / 1e9:.0f} GB, "
        f"solve <= {SOLVE_BUDGET_S / 60:.0f} min, {CG_ITERATIONS} CG iters):"
    )
    header = (
        f"{'alpha':>5} {'ndir':>4} {'win':>4} {'lmin':>4} | {'N_obs':>9} {'N_coef':>11} "
        f"{'nnz(G)':>13} {'G GB':>7} | {'stored':>8} {'mfree':>8} | verdict"
    )
    print(header)
    print("-" * len(header))
    ok_configs: list[ConfigCost] = []
    for alpha, n_dir, window, lam_min in product(ALPHAS, N_DIRS, WINDOWS_D, LAM_MINS):
        cost = ConfigCost(
            alpha=alpha,
            n_dir=n_dir,
            window_days=window,
            lam_min=lam_min,
            n_obs=totals[window],
            n_coef=n_coefficients(alpha, n_dir, window, lam_min),
            nnz=nnz_g(totals[window], alpha, n_dir, lam_min),
        )
        g_gb = cost.stored_g_bytes() / 1e9
        t_stored = cost.solve_s_stored(matvec_rate)
        t_free = cost.solve_s_matrix_free(eval_rate)
        fits = g_gb * 1e9 <= RAM_BUDGET_BYTES
        fast_enough = (t_stored if fits else t_free) <= SOLVE_BUDGET_S
        verdict = ("OK-stored" if fits else "OK-mfree") if fast_enough else "TOO SLOW"
        if fast_enough:
            ok_configs.append(cost)
        print(
            f"{alpha:>5} {n_dir:>4} {window:>4} {lam_min:>4.0f} | {cost.n_obs:>9,} "
            f"{cost.n_coef:>11,} {cost.nnz:>13,} {g_gb:>7.2f} | "
            f"{t_stored:>7.1f}s {t_free:>7.1f}s | {verdict}"
        )

    print("\nrecommended local operating envelope (all budget-clearing configs):")
    if ok_configs:
        worst = max(ok_configs, key=lambda c: c.nnz)
        print(
            f"  {len(ok_configs)}/{len(ALPHAS) * len(N_DIRS) * len(WINDOWS_D) * len(LAM_MINS)} "
            f"configs clear budgets; largest clearing config: alpha={worst.alpha}, "
            f"n_dir={worst.n_dir}, window={worst.window_days}d, lam_min={worst.lam_min:.0f} km "
            f"(nnz={worst.nnz:,}, G={worst.stored_g_bytes() / 1e9:.2f} GB)"
        )
    else:
        print("  NONE — local runs infeasible under the stated budgets.")


if __name__ == "__main__":
    main()
