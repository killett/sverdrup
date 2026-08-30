# Deletion record — two test-written strays in the evidence directory (owner pin 110)

**Authorised by owner pin 110, 2026-08-30.** A deletion from the evidence directory that
leaves no trace is its own provenance gap, so this is the trace: what they were, when they
were written, by which test, and — for the NetCDF — its sha256 taken **before** removal.

## The artifacts

| | Artifact 1 | Artifact 2 |
|---|---|---|
| Path | `data/2021a_ssh_mapping_ose/ours/phase14_stage1/dt_seam_n_j3_phy_l3_2017_stage1.nc` | `data/2021a_ssh_mapping_ose/ours/phase14_stage1/kuroshio_pcg_ckpt/` |
| Kind | CMEMS-MY j3 along-track holdout, clipped to the `seam_n` core, 26 348 points | PCG member-batch checkpoint directory, **empty** |
| Size | 105 787 bytes | 0 entries |
| **sha256 before removal** | `a8d32733d38a0ed00c5b94e42675a74d53a19dc73e2f823b110b3fa7bde892ea` | n/a (empty directory) |
| Written (UTC) | 2026-08-29T22:48:43Z | 2026-08-29T22:50:01Z |
| Labels it carried | `label: STAGE1-EVIDENCE`, `mission: j3`, `tile: seam_n` | none |

## How they came to exist

`test_run_reaches_gated_solve_stub_when_eligible`, in its **pre-T5b form**, asserted that
`run("seam_n")` raised `NotImplementedError` at the `_solve_leg` stub. T5b replaced that
stub with the real leg. In the window between the leg landing and that stale test being
rewritten, one local run of `tests/test_phase14_stage1_run.py` executed the test — which
called the REAL `run("seam_n")` with `ladder.tier1_eligible` monkeypatched True.

The leg then did what it is built to do: it found T4's existing `seam_n` member store and
maps in `phase14_stage1/`, **resumed from them** rather than solving (which is why this
cost seconds rather than hours), created its checkpoint directory, and reached the scoring
stage — where it built the `seam_n` validation track before the test failed on the
assertion that no `NotImplementedError` had been raised.

## What was NOT affected

- **The evidence store is untouched.** `stage_miost_gate_results.json` mtime is
  2026-07-30T03:47, and `phase14.stage1` carries no `tiles`, `report_rows`,
  `anisotropy_inputs`, `land_mask_exercise` or `equatorial_lane0_manifest` node. No
  evidence row, seal interaction or tally change occurred.
- **T4's artifacts are unchanged.** The `seam_n`/`seam_s` maps and member stores were READ
  (the resume path), never rewritten — the leg skips map writing when the files exist.

## Why they were deleted rather than kept

The NetCDF carried `label: STAGE1-EVIDENCE` — an evidence label on an artifact that
entered the directory through a test, with no build record, no evidence row and no
witness. Under the reuse pattern in place at the time (`if not track.exists()`), a later
`seam_n` leg would have **silently adopted it**. Its own metadata was also wrong in the way
pin 111 names (inherited daily-file attrs claiming a two-day coverage span).

## Fixes landed with this record — the symptoms are not the defect

- **Pin 110(a) — test isolation.** An autouse fixture redirects `STAGE1_DIR`, `EVIDENCE`
  and `LANE0_DIR` for every test in `tests/test_phase14_stage1_run.py`, and
  `_solve_leg` now threads those paths explicitly into every recorder (default arguments
  bind at import time, so monkeypatching the module constant alone would NOT have stopped
  the writes). `test_no_test_write_reaches_the_real_data_tree` takes an inventory of the
  REAL tree, exercises the leg, and asserts it is unchanged.
- **Pin 110(b) — reuse is gated on provenance.** `write_track_build_record` writes a
  sidecar carrying the track's sha256, tile, mission, point count and source-file count;
  `assert_track_reusable` refuses reuse when the record is missing, when the digest no
  longer matches the bytes, or when the record names a different tile. A leftover has no
  build record and is refused loudly instead of adopted silently.
- **Pin 111 — the attrs bug.** `build_tile_validation_track` now concatenates with
  `combine_attrs="drop"` and writes provenance describing the concatenation itself; the
  coverage span is test-pinned against the actual min/max times, not against the setting.
