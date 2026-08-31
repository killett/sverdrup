"""R5 — resume-after-hard-kill, tested to BIT-IDENTITY (owner pin 117).

Four legs at ~31 h is ~5 days of exposure during which ``setsid`` protects
nothing (R4), and the resume path has never been exercised. Pin 117 sets
the bar: not "the resume completed", but **bit-identical output against an
uninterrupted run of the same configuration** — a resume that produces
subtly different results is worse than no resume, because the difference is
invisible and would enter a leg's evidence silently.

This drives the PRODUCTION path (``_tile_framed_obs`` → ``_seam_miost`` →
``merged_members``) at a deliberately small scale (117e): one window, m=2,
on a diverse tile. The mechanism under test is the per-window PCG
checkpoint (``member_solve_checkpoint_dir``), written every 50 iterations
inside the member-batch solve.

Commands:
    solve    run one window and record the coefficient digests
    compare  compare two solve records for bit-identity
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

app = typer.Typer(add_completion=False)


def _stage1_run_module() -> Any:  # noqa: ANN401 - module object
    """Import the sibling Stage-1 driver (scripts/ is not a package)."""
    import importlib.util  # noqa: PLC0415
    import sys  # noqa: PLC0415

    name = "phase14_stage1_run"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha_array(arr: Any) -> str:  # noqa: ANN401 - ndarray
    """sha256 over an array's exact bytes (C-contiguous)."""
    import numpy as np  # noqa: PLC0415

    a = np.ascontiguousarray(arr)
    return hashlib.sha256(a.tobytes()).hexdigest()


@app.command()
def solve(
    out: Annotated[Path, typer.Option(help="Where to write the solve record")],
    ckpt: Annotated[Path, typer.Option(help="PCG checkpoint directory")],
    tile: Annotated[str, typer.Option(help="Diverse tile")] = "kuroshio",
    m: Annotated[int, typer.Option(help="Members (small on purpose, pin 117e)")] = 2,
    maxiter: Annotated[int, typer.Option(help="PCG cap")] = 1200,
) -> None:
    """Solve ONE window on the production path and digest the coefficients.

    Args:
        out: Record destination.
        ckpt: Checkpoint directory — the same directory across a
            kill/resume pair is what makes the resume happen.
        tile: Registry tile.
        m: Ensemble members.
        maxiter: PCG iteration cap.
    """
    import time  # noqa: PLC0415

    import sverdrup.methods.miost as miost_mod  # noqa: PLC0415
    from sverdrup.core.parameters import ConstantProvider  # noqa: PLC0415
    from sverdrup.core.seeding import derive_seed  # noqa: PLC0415
    from sverdrup.distributions.miost_ensemble import merged_members  # noqa: PLC0415
    from sverdrup.methods.miost import PHASE13_WINNER_PARAMS  # noqa: PLC0415

    run = _stage1_run_module()

    def echo(msg: str) -> None:
        print(f"[r5-probe] {datetime.now(UTC).isoformat()} {msg}", flush=True)

    t0 = time.monotonic()
    echo(f"loading obs for {tile} (production path)")
    frame, grid, framed, _cfg = run._tile_framed_obs(tile)  # noqa: SLF001
    echo(f"framed obs {len(framed.values())}; grid {grid.x.size}x{grid.y.size}")

    ckpt.mkdir(parents=True, exist_ok=True)
    # ONE window (117e), the production window length, the production config.
    method = run._seam_miost(  # noqa: SLF001
        frame, starts=(0.0,), maxiter=maxiter, ckpt_dir=ckpt
    )
    provider = ConstantProvider(dict(PHASE13_WINNER_PARAMS))
    root = int(derive_seed("miost", "phase14-stage1", tile, 0))
    log_start = len(miost_mod.CONVERGENCE_LOG)
    echo(f"solving: m={m} root={root} maxiter={maxiter} ckpt={ckpt}")
    _spec, etas, anoms, starts = merged_members(
        method,
        framed,
        grid,
        provider,
        m,
        root,
        on_window=lambda wid, day: echo(f"window {wid} solved (day {day:.0f})"),
    )
    rows = [dict(r) for r in miost_mod.CONVERGENCE_LOG[log_start:]]
    record = {
        "label": "R5-RESUME-PROBE",
        "not_evidence_bearing": (
            "PROBE: a resume-mechanism measurement at m=2, one window. No "
            "STAGE1-EVIDENCE artifact, no evidence row, no seal interaction"
        ),
        "tile": tile,
        "m": m,
        "root_int": root,
        "maxiter": maxiter,
        "windows": sorted(anoms),
        "eta_sha256": {w: _sha_array(etas[w]) for w in sorted(etas)},
        "anom_sha256": {w: _sha_array(anoms[w]) for w in sorted(anoms)},
        "starts": {w: float(starts[w]) for w in sorted(starts)},
        "pcg": rows,
        "wall_s": time.monotonic() - t0,
        "date": datetime.now(UTC).isoformat(),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2))
    echo(f"record -> {out} ({record['wall_s']:.0f}s)")


@app.command()
def compare(
    baseline: Annotated[Path, typer.Argument(help="Uninterrupted run's record")],
    resumed: Annotated[Path, typer.Argument(help="Killed-and-resumed run's record")],
) -> None:
    """Assert the resumed coefficients are BIT-IDENTICAL to the baseline.

    Raises:
        typer.Exit: Non-zero when any digest differs — pin 117(d): that is
            a FINDING and goes to the owner before leg 1.
    """
    a = json.loads(baseline.read_text())
    b = json.loads(resumed.read_text())
    diffs: list[str] = []
    for field in ("eta_sha256", "anom_sha256", "starts", "windows", "root_int"):
        if a[field] != b[field]:
            diffs.append(field)
    typer.echo(f"windows: {a['windows']}")
    for w in a["windows"]:
        same_eta = a["eta_sha256"][w] == b["eta_sha256"].get(w)
        same_anom = a["anom_sha256"][w] == b["anom_sha256"].get(w)
        typer.echo(
            f"  {w}: eta {'IDENTICAL' if same_eta else 'DIFFERS'} "
            f"({a['eta_sha256'][w][:12]}… vs {str(b['eta_sha256'].get(w))[:12]}…), "
            f"anom {'IDENTICAL' if same_anom else 'DIFFERS'}"
        )
    it_a = [r.get("iterations") for r in a["pcg"]]
    it_b = [r.get("iterations") for r in b["pcg"]]
    typer.echo(f"pcg iterations: baseline {it_a} vs resumed {it_b}")
    if diffs:
        typer.echo(f"NOT BIT-IDENTICAL — fields differing: {diffs}")
        raise typer.Exit(code=1)
    typer.echo(
        "BIT-IDENTICAL: the resumed run reproduces the uninterrupted one exactly"
    )


if __name__ == "__main__":
    app()
