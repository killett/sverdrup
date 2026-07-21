"""Phase-13 §8 identifiability diagnostics (plan Task 11; REPORT-ONLY).

Pure statistics over the c-block diagnostic-tap rows (one row per pass:
mission, family, time, ĉ_bias, ĉ_tilt, fitted-field chord mean). Nothing
here gates; every row lands in the gate-1 pack with the §8 shrinkage note
(var(ĉ)/Λ < 1 under a CORRECT model — the trigger reads CROSS-MISSION
CONTRASTS, never absolute distance from 1).

Row schema (built by the winner-run tap; consumed here):
    mission: str            mission id label
    family: str             "asc" | "desc" (per-pass lat trend)
    t_mean_days: float      pass mean time [days]
    c_bias, c_tilt: float   posterior-mean mode coefficients [m, m/s-unit]
    field_chord_mean: float fitted field meaned over the pass's obs [m]
    n_obs: int              obs in the pass

Small-sample honesty (Phase-11 ratification 2 precedent): under-floor
mission x family rows stay VISIBLE and flagged (None statistics), never
dropped — an absent row reads as "no problem" in a pack.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, cast

import numpy as np

Rows = list[dict[str, Any]]

_RESULTS = Path("data/2021a_ssh_mapping_ose/ours/stage_miost_gate_results.json")

#: lag-1 needs >= 3 passes (two lagged pairs) for a correlation.
_LAG1_MIN_PASSES = 3


def _by_mission(rows: Rows) -> dict[str, Rows]:
    out: dict[str, Rows] = defaultdict(list)
    for r in rows:
        out[str(r["mission"])].append(r)
    return dict(out)


def _by_mission_family(rows: Rows) -> dict[tuple[str, str], Rows]:
    out: dict[tuple[str, str], Rows] = defaultdict(list)
    for r in rows:
        out[(str(r["mission"]), str(r["family"]))].append(r)
    return dict(out)


def variance_ratio_table(
    rows: Rows, lam_bias: float, lam_tilt: float
) -> dict[str, dict[str, Any]]:
    """§8.1 variance-ratio table per mission: var(ĉ)/Λ + pass counts.

    Sample variance uses ddof=1 (the shrinkage reading compares ratios
    ACROSS missions; the estimator is documented beside the table).

    Args:
        rows: Tap rows (schema above).
        lam_bias: Winner Λ_bias [m²].
        lam_tilt: Winner Λ_tilt [m²].

    Returns:
        Per-mission dict: var_ratio_bias, var_ratio_tilt, n_passes,
        pass-length median/IQR (n_obs proxy).
    """
    table: dict[str, dict[str, Any]] = {}
    for mission, rs in _by_mission(rows).items():
        cb = np.asarray([r["c_bias"] for r in rs], float)
        ct = np.asarray([r["c_tilt"] for r in rs], float)
        n_obs = np.asarray([r["n_obs"] for r in rs], float)
        n = cb.size
        table[mission] = {
            "n_passes": int(n),
            "var_ratio_bias": float(np.var(cb, ddof=1) / lam_bias) if n >= 2 else None,
            "var_ratio_tilt": float(np.var(ct, ddof=1) / lam_tilt) if n >= 2 else None,
            "pass_len_median_obs": float(np.median(n_obs)),
            "pass_len_iqr_obs": [
                float(np.percentile(n_obs, 25)),
                float(np.percentile(n_obs, 75)),
            ],
        }
    return table


def saturation_fraction(
    rows: Rows, lam_bias: float, lam_tilt: float
) -> dict[str, dict[str, Any]]:
    """§8.2 share of passes with |ĉ| > 2√Λ per mission x mode (null < 5%).

    Args:
        rows: Tap rows.
        lam_bias: Winner Λ_bias [m²].
        lam_tilt: Winner Λ_tilt [m²].

    Returns:
        Per-mission dict: bias/tilt saturation fractions + n_passes.
    """
    out: dict[str, dict[str, Any]] = {}
    for mission, rs in _by_mission(rows).items():
        cb = np.asarray([r["c_bias"] for r in rs], float)
        ct = np.asarray([r["c_tilt"] for r in rs], float)
        out[mission] = {
            "n_passes": int(cb.size),
            "bias": float(np.mean(np.abs(cb) > 2.0 * np.sqrt(lam_bias))),
            "tilt": float(np.mean(np.abs(ct) > 2.0 * np.sqrt(lam_tilt))),
        }
    return out


def lag1_autocorr(rows: Rows) -> dict[tuple[str, str], dict[str, Any]]:
    """§8.3 absorption discriminator: lag-1 autocorr of the bias sequence.

    Per mission x FAMILY (asc/desc separated — mixing injects alternating
    structure), TIME-ordered, lag-1 in pass index; median inter-pass Δt
    recorded per row; null band ±2/√n_passes.

    Args:
        rows: Tap rows.

    Returns:
        Per (mission, family): r1 (None under floor), null_band,
        n_passes, median_dt_days.
    """
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for key, rs in _by_mission_family(rows).items():
        t = np.asarray([r["t_mean_days"] for r in rs], float)
        c = np.asarray([r["c_bias"] for r in rs], float)
        order = np.argsort(t, kind="stable")
        t, c = t[order], c[order]
        n = c.size
        row: dict[str, Any] = {
            "n_passes": int(n),
            "null_band": float(2.0 / np.sqrt(n)),
            "median_dt_days": float(np.median(np.diff(t))) if n >= 2 else None,
        }
        if n >= _LAG1_MIN_PASSES:
            row["r1"] = float(np.corrcoef(c[:-1], c[1:])[0, 1])
        else:
            row["r1"] = None  # visible, flagged, never dropped
        out[key] = row
    return out


def field_correlation(rows: Rows) -> dict[tuple[str, str], dict[str, Any]]:
    """§8.4 field-correlation complement: corr(ĉ_bias, field chord mean).

    Sign logic (spec §8.4 verbatim): POSITIVE beyond the null band ⇒
    absorption (field signal leaking INTO the modes); NEGATIVE beyond the
    band ⇒ compensation seesaw (over-parameterization signature);
    inside the band ⇒ clean separation.

    Args:
        rows: Tap rows.

    Returns:
        Per (mission, family): r (None under floor), null_band, n_passes,
        reading in {"absorption", "compensation", "clean"}.
    """
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for key, rs in _by_mission_family(rows).items():
        c = np.asarray([r["c_bias"] for r in rs], float)
        f = np.asarray([r["field_chord_mean"] for r in rs], float)
        n = c.size
        band = float(2.0 / np.sqrt(n))
        row: dict[str, Any] = {"n_passes": int(n), "null_band": band}
        if n >= _LAG1_MIN_PASSES and np.std(c) > 0 and np.std(f) > 0:
            r = float(np.corrcoef(c, f)[0, 1])
            row["r"] = r
            row["reading"] = (
                "absorption" if r > band else "compensation" if r < -band else "clean"
            )
        else:
            row["r"] = None
            row["reading"] = "under-floor"
        out[key] = row
    return out


def read_tap_dir(tap_dir: Path) -> tuple[Rows, list[dict[str, Any]]]:
    """Load a lane's ctap artifacts into per-pass rows + per-window blocks.

    Overlap passes (present in two adjacent windows) are DEDUPED in the
    per-pass rows by value-derived identity (mission_hash, pass_start_s),
    keeping the earlier window's row — double counting would bias every
    per-pass statistic toward the overlap regions. BOTH copies stay in
    the per-window blocks (the §8.5 stability scatter needs them).

    Args:
        tap_dir: Directory of ``ctap_*.npz`` artifacts.

    Returns:
        (deduped per-pass rows, per-window blocks sorted by window id).
    """
    rows: Rows = []
    windows: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for p in sorted(tap_dir.glob("ctap_*.npz")):
        with np.load(p, allow_pickle=False) as z:
            keys = [
                (int(m), int(s))
                for m, s in zip(z["pass_mission"], z["pass_start_s"], strict=True)
            ]
            windows.append(
                {
                    "window": str(z["window"]),
                    "keys": keys,
                    "c_bias": [float(c) for c in z["c_bias"]],
                }
            )
            for i, key in enumerate(keys):
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "mission": str(z["pass_mission_label"][i]),
                        "family": str(z["family"][i]),
                        "t_mean_days": float(z["t_mean_days"][i]),
                        "c_bias": float(z["c_bias"][i]),
                        "c_tilt": float(z["c_tilt"][i]),
                        "field_chord_mean": float(z["field_chord_mean"][i]),
                        "n_obs": int(z["n_obs"][i]),
                    }
                )
    return rows, windows


def tables_for_json(table: dict[Any, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Flatten (mission, family) tuple keys to "mission/family" strings."""
    return {
        ("/".join(k) if isinstance(k, tuple) else str(k)): v for k, v in table.items()
    }


def assemble_lane(tap_dir: Path, lam_bias: float, lam_tilt: float) -> dict[str, Any]:
    """All five §8 tables for one lane's tap directory.

    Args:
        tap_dir: The lane's ctap directory.
        lam_bias: Winner Λ_bias [m²] (from the recorded ctap evidence).
        lam_tilt: Winner Λ_tilt [m²].

    Returns:
        Evidence-ready block (JSON-safe keys) with the §8 shrinkage note.
    """
    rows, windows = read_tap_dir(tap_dir)
    return {
        "n_passes_deduped": len(rows),
        "n_windows": len(windows),
        "estimator_note": (
            "var(chat)/Lambda < 1 under a CORRECT model (posterior "
            "shrinkage; law of total variance) — the follow-on trigger "
            "reads CROSS-MISSION CONTRASTS, never absolute distance "
            "from 1 (spec §8.1)"
        ),
        "variance_ratio": variance_ratio_table(rows, lam_bias, lam_tilt),
        "saturation": saturation_fraction(rows, lam_bias, lam_tilt),
        "lag1_autocorr": tables_for_json(lag1_autocorr(rows)),
        "lag1_confounder_note": (
            "persistent genuine environmental residuals (SSB, wet-tropo) "
            "also autocorrelate; the flag is HIGH multi-day persistence, "
            "and the field-correlation row breaks the ambiguity (spec §8.3)"
        ),
        "field_correlation": tables_for_json(field_correlation(rows)),
        "adjacent_window_agreement": adjacent_window_agreement(windows),
    }


def main() -> None:
    """Assemble §8 diagnostics for the tapped winners → evidence.

    Reads ``phase13.miost.ctap.<lane>`` (written by the winner-ctap runs)
    and writes ``phase13.miost.diagnostics.<lane>``. REPORT-ONLY.
    """
    from sverdrup.application.calibration.harness import (  # noqa: PLC0415
        atomic_write_json,
    )

    results = cast(dict[str, Any], json.loads(_RESULTS.read_text()))
    miost = results.setdefault("phase13", {}).setdefault("miost", {})
    ctap = miost.get("ctap", {})
    if not ctap:
        raise SystemExit("no phase13.miost.ctap evidence — run --winner-ctap first")
    diagnostics: dict[str, Any] = {}
    for lane, block in ctap.items():
        diagnostics[lane] = assemble_lane(
            Path(block["tap_dir"]),
            lam_bias=float(block["lam_bias"]),
            lam_tilt=float(block["lam_tilt"]),
        )
        print(
            f"[diag {lane}] {diagnostics[lane]['n_passes_deduped']} passes, "
            f"{diagnostics[lane]['n_windows']} windows",
            flush=True,
        )
    miost["diagnostics"] = diagnostics
    atomic_write_json(_RESULTS, results)
    print("[diag] written to phase13.miost.diagnostics", flush=True)


def adjacent_window_agreement(windows: list[dict[str, Any]]) -> dict[str, Any]:
    """§8.5 free stability row: overlap-pass ĉ agreement across windows.

    Passes are matched by VALUE-DERIVED identity (mission_hash,
    pass_start_s) — never positionally (the segmentation's own ordering
    rule). A pass appearing in exactly two adjacent windows contributes
    one scatter pair.

    Args:
        windows: Per-window dicts: window (id), keys (list of identity
            tuples), c_bias (aligned values).

    Returns:
        n_matched, rmse_bias, corr_bias (None when < 2 pairs).
    """
    pairs: list[tuple[float, float]] = []
    for i in range(len(windows) - 1):
        a, b = windows[i], windows[i + 1]
        a_map = dict(zip([tuple(k) for k in a["keys"]], a["c_bias"], strict=True))
        b_map = dict(zip([tuple(k) for k in b["keys"]], b["c_bias"], strict=True))
        for k in a_map.keys() & b_map.keys():
            pairs.append((float(a_map[k]), float(b_map[k])))
    if not pairs:
        return {"n_matched": 0, "rmse_bias": None, "corr_bias": None}
    x = np.asarray([p[0] for p in pairs])
    y = np.asarray([p[1] for p in pairs])
    return {
        "n_matched": len(pairs),
        "rmse_bias": float(np.sqrt(np.mean((x - y) ** 2))),
        "corr_bias": float(np.corrcoef(x, y)[0, 1])
        if len(pairs) >= 2 and np.std(x) > 0 and np.std(y) > 0
        else None,
    }


if __name__ == "__main__":
    main()
