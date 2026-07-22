"""Cross-env gate machinery (phase-14 0b-4; SPEC §10 gate 4 — decomposed).

Two halves, NEVER one blended number (fork-g pin 1):

- ``--leg crn`` / ``compare-crn``: the BIT-exact half. The manifest hashes
  the KEYED-UNIFORM streams (``miost_crn._keyed_uniform`` — the production
  randomness layer) per consumed axis, member 0. Recorded interpretation:
  "raw CRN draw byte-streams" = the randomness; ``ndtri`` + variance
  scaling are ARITHMETIC and belong to the solve half — hashing uniforms
  isolates randomness from arithmetic exactly as pin 1 demands.
- ``--leg solve`` / ``compare-solve``: mean + member-0 maps, PCG iters,
  the BLAS recipe in effect. Compare REPORTS max-abs/RMS deltas —
  tolerance is recorded from measurement (Task 18), never asserted before
  it exists.

Pinned subject: the SIGNED BOX frame, window w0 (first 60-day window of
2017), dc2021a source (five mapping missions), frozen signed config
(``shipped_miost5`` + ``PHASE13_WINNER_PARAMS``), signed member root.
The lane-D signed config carries NO pass modes, so the consumed axes are
``obs`` + ``coef`` (recorded in the manifest).

Pinned single-thread deterministic recipe (exported by ``print-env``):
``OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
PYTHONHASHSEED=0``.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated, Any

import numpy as np
import typer

app = typer.Typer(add_completion=False)

PINNED_ENV = {
    "OPENBLAS_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "PYTHONHASHSEED": "0",
}

# Window-obs subset rule for the pinned subject (recorded; half-open).
_W0_RULE = "t >= w0.start_day and t < w0.start_day + w_days"


def _sha(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def _versions() -> dict[str, str]:
    """numpy/scipy/openblas versions + container digest for the manifest."""
    import os

    import scipy  # type: ignore[import-untyped]  # noqa: PLC0415

    try:  # numpy >= 2 exposes build deps via show_config dict mode
        cfg: Any = np.show_config(mode="dicts")
    except TypeError:  # pragma: no cover - older numpy
        cfg = {}
    blas = str(cfg.get("Build Dependencies", {}).get("blas", {}).get("name", "unknown"))
    return {
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "blas": blas,
        "python": sys.version.split()[0],
        "container_digest": os.environ.get("CONTAINER_IMAGE_DIGEST", "unrecorded"),
    }


def _uniform_stream(
    axis: str, identity: np.ndarray, root: int, member: int
) -> np.ndarray:
    """The production keyed-uniform stream for one axis (the randomness)."""
    from sverdrup.methods.miost_crn import (  # noqa: PLC0415
        _keyed_uniform,
        _member_key,
    )

    return _keyed_uniform(_member_key(root, member, axis), identity)


def _synthetic_identities() -> dict[str, np.ndarray]:
    """A tiny deterministic window for the CI-local same-host smoke."""
    n = 64
    lon = np.linspace(295.0, 305.0, n)
    lat = np.linspace(33.0, 43.0, n)
    t = np.linspace(0.0, 60.0, n)
    mh = np.arange(n, dtype=float) % 5.0
    obs_identity = np.ascontiguousarray(np.column_stack([lon, lat, t, mh]))
    coef_identity = np.ascontiguousarray(
        np.column_stack([np.arange(32, dtype=float)] * 6)
    )
    return {"obs": obs_identity, "coef": coef_identity}


def _pinned_identities() -> tuple[dict[str, np.ndarray], int, dict[str, Any]]:
    """The REAL pinned subject's identity rows + signed root + provenance."""
    from sverdrup.adapters.altimetry import BBox  # noqa: PLC0415
    from sverdrup.adapters.altimetry.dc2021a import Dc2021aSource  # noqa: PLC0415
    from sverdrup.core.parameters import ConstantProvider  # noqa: PLC0415
    from sverdrup.core.seeding import derive_seed  # noqa: PLC0415
    from sverdrup.methods.miost import (  # noqa: PLC0415
        PHASE13_WINNER_PARAMS,
        _obs_identity,
        shipped_miost5,
    )
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415
    from sverdrup.validation.params import baseline_config  # noqa: PLC0415
    from sverdrup.validation.run import halo_obs  # noqa: PLC0415

    mapping_five = ("alg", "h2g", "j2g", "j2n", "s3a")
    src = Dc2021aSource()
    obs = src.load(
        BBox(0.0, 360.0, -90.0, 90.0),
        np.datetime64("2016-11-01"),
        np.datetime64("2018-03-01"),
        missions=mapping_five,
    )
    grid = baseline_config()[1]
    framed = halo_obs(obs, grid, halo_deg=1.0)
    w0 = WindowPlan().windows[0]
    c = framed.coords()
    keep = (c[:, 2] >= w0.start_day) & (c[:, 2] < w0.start_day + w0.w_days)
    mission = framed.mission
    if mission is None:  # pragma: no cover - dc2021a always tags
        raise RuntimeError("dc2021a returned untagged obs")
    obs_identity = _obs_identity(c[keep, 0], c[keep, 1], c[keep, 2], mission[keep])
    method = shipped_miost5()
    spec = method._spec_from(ConstantProvider(dict(PHASE13_WINNER_PARAMS)), grid)
    els = spec.elements_for_window(w0.start_day, w0.w_days)
    root = derive_seed("miost", "stage-b-winner", "members", 0)
    prov = {
        "subject": "signed-box w0, dc2021a five-mission, frozen signed config",
        "window_rule": _W0_RULE,
        "w0_start_day": float(w0.start_day),
        "w_days": float(w0.w_days),
        "n_obs": int(keep.sum()),
        "manifest_sha_source": src.descriptor().manifest_sha(),
        "axes_note": "lane-D signed config: no pass modes -> obs+coef only",
    }
    return (
        {"obs": obs_identity, "coef": np.asarray(els.identity, dtype=float)},
        int(root),
        prov,
    )


@app.command("print-env")
def print_env() -> None:
    """The pinned single-thread deterministic recipe + versions."""
    for k, v in PINNED_ENV.items():
        typer.echo(f"{k}={v}")
    for k, v in _versions().items():
        typer.echo(f"# {k}: {v}")


@app.command()
def crn(
    out: Annotated[Path, typer.Option(help="Output crn_manifest.json path")],
    member: Annotated[int, typer.Option()] = 0,
    synthetic: Annotated[
        bool,
        typer.Option(help="Tiny deterministic window (CI-local smoke), no data"),
    ] = False,
) -> None:
    """Emit the CRN manifest: per-axis sha256 of the keyed-uniform streams."""
    if synthetic:
        identities = _synthetic_identities()
        root = 12345
        prov: dict[str, Any] = {"subject": "synthetic-smoke"}
    else:
        identities, root, prov = _pinned_identities()
    axes = {}
    for axis, identity in identities.items():
        stream = _uniform_stream(axis, identity, root, member)
        axes[axis] = {"sha256": _sha(stream), "n": int(stream.size)}
    manifest = {
        "schema_version": 1,
        "member": member,
        "root": root,
        "axes": axes,
        "env_recipe": PINNED_ENV,
        "versions": _versions(),
        "provenance": prov,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    typer.echo(f"wrote {out}")


@app.command("compare-crn")
def compare_crn(a: Path, b: Path) -> None:
    """Assert bit-exact equality of two CRN manifests (hash compare, no FP)."""
    ma = json.loads(a.read_text())
    mb = json.loads(b.read_text())
    if ma["axes"] != mb["axes"] or ma["root"] != mb["root"]:
        typer.echo("MISMATCH: CRN streams differ — the identity assumption broke")
        typer.echo(json.dumps({"a": ma["axes"], "b": mb["axes"]}, indent=1))
        raise typer.Exit(code=1)
    typer.echo("EQUAL: CRN draws bit-exact across the two manifests")


@app.command()
def solve(
    out: Annotated[Path, typer.Option(help="Output npz path (PROBE-labeled)")],
) -> None:
    """The solve half: mean + member-0 maps for the pinned subject.

    PROBE-labeled output; runs under the pinned recipe at Task 18 (Tier-2)
    and on this box for the same-host legs. Never evaluation-bearing.
    """
    from sverdrup.core.parameters import ConstantProvider  # noqa: PLC0415
    from sverdrup.core.seeding import derive_seed  # noqa: PLC0415
    from sverdrup.distributions.miost_ensemble import (  # noqa: PLC0415
        mean_fields,
        merged_members,
        std_fields,
    )
    from sverdrup.methods.miost import (  # noqa: PLC0415
        PHASE13_WINNER_PARAMS,
        shipped_miost5,
    )
    from sverdrup.methods.miost_windows import WindowPlan  # noqa: PLC0415
    from sverdrup.validation.params import baseline_config  # noqa: PLC0415
    from sverdrup.validation.run import halo_obs  # noqa: PLC0415

    identities, root, prov = _pinned_identities()  # provenance reuse
    from sverdrup.adapters.altimetry import BBox  # noqa: PLC0415
    from sverdrup.adapters.altimetry.dc2021a import Dc2021aSource  # noqa: PLC0415

    obs = Dc2021aSource().load(
        BBox(0.0, 360.0, -90.0, 90.0),
        np.datetime64("2016-11-01"),
        np.datetime64("2018-03-01"),
        missions=("alg", "h2g", "j2g", "j2n", "s3a"),
    )
    grid = baseline_config()[1]
    framed = halo_obs(obs, grid, halo_deg=1.0)
    method = shipped_miost5()
    provider = ConstantProvider(dict(PHASE13_WINNER_PARAMS))
    root = derive_seed("miost", "stage-b-winner", "members", 0)
    plan = WindowPlan(starts=(WindowPlan().starts[0],))
    days = [float(plan.starts[0] + 30.0)]  # one mid-window day map
    spec, etas_a, anoms, starts = merged_members(
        method, framed, grid, provider, 1, root
    )
    means = mean_fields(spec, starts, etas_a, grid, plan, days)
    stds = std_fields(spec, starts, anoms, grid, plan, days)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        out,
        mean=means,
        member_std=stds,
        label="PROBE",
        env_recipe=json.dumps(PINNED_ENV),
        versions=json.dumps(_versions()),
        provenance=json.dumps(prov),
    )
    typer.echo(f"wrote {out} (PROBE)")


@app.command("compare-solve")
def compare_solve(a: Path, b: Path) -> None:
    """REPORT max-abs and RMS deltas between two solve outputs.

    Reports only — the tolerance is recorded from the Task-18 measurement,
    never asserted before it exists.
    """
    da, db = np.load(a), np.load(b)
    report = {}
    for key in ("mean", "member_std"):
        delta = np.asarray(da[key], dtype=float) - np.asarray(db[key], dtype=float)
        report[key] = {
            "max_abs": float(np.nanmax(np.abs(delta))),
            "rms": float(np.sqrt(np.nanmean(delta**2))),
        }
    typer.echo(json.dumps(report, indent=1))


def _pixi_blas_versions() -> str:  # pragma: no cover - convenience only
    """`pixi list` rows for openblas/numpy/scipy (recorded at Tier-2)."""
    pixi = shutil.which("pixi") or "pixi"
    out = subprocess.run(  # noqa: S603
        [pixi, "list"], capture_output=True, text=True, check=False
    ).stdout
    return "\n".join(
        line
        for line in out.splitlines()
        if any(p in line for p in ("openblas", "numpy", "scipy"))
    )


if __name__ == "__main__":
    app()
