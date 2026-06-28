# Design — 2023 Ocean Data Challenges downloader

## Goal

One Python script that reproduces, on any machine, the data downloads for the
**four 2023 Ocean Data Challenges**, selectable per-challenge or all at once,
SHA256-verified for exact reproduction. Sibling to
`download_ssh_mapping_data_challenge_2021a.py`.

## The four challenges (official names + hosts)

| Selector | Challenge (repo) | Host | Files | ~Size |
|---|---|---|---|---|
| `--ose` | `2023a_SSH_mapping_OSE` | MEOM mirror | `sad`, `alongtrack`, `independent_alongtrack`, `independent_drifters` (.tar.gz) + `maps/{DUACS,MIOST_geos,MIOST_geos_barotrop_eqwaves,NeurOST_SSH,NeurOST_SSH-SST}_…_allsat-alg.tar.gz` | ~10–12 GB |
| `--mapmed` | `2023a_SSH_MapMed_OSE` | MEOM mirror | `dc_obs.tar.gz`, `dc_eval.tar.gz` | ~5 MB |
| `--california` | `2023b_SSHmapping_HF_California` | MEOM mirror | `dc_ref_eval`, `dc_obs_swot`, `dc_obs_nadirs` (.tar.gz) | ~9 GB |
| `--enatl60` | `2023_SSH_mapping_train_eNATL60_test_NATL60` | **Wasabi S3** | `dc_ref/{eNATL60-BLB002,NATL60-CJM165}-daily-reg-1_{20,8}.nc` + `dc_obs/{…}-alongtrack.gz` | ~61 GB |

`--all` selects all four (~80 GB). All hosts are unauthenticated HTTPS.

## Module + entry point

- `src/sverdrup/validation/download_ocean_data_challenges_2023.py`
- `python -m sverdrup.validation.download_ocean_data_challenges_2023 (--all | --ose | --mapmed | --california | --enatl60) [--data-root PATH] [--extract | --extract-existing]`
- At least one challenge selector (or `--all`) is required.

## Layout + behaviour

- Per-challenge `Challenge(base_url, subdir, files=[(relpath, sha256)])`.
- Default data-root `./data` resolved against the **cwd** (never `/workspace`);
  each challenge writes under `data/<challenge-subdir>/…`, dirs created
  `parents=True`.
- Download via `access.fetch` (anon HTTPS — MEOM and Wasabi alike).
- **Verification:** completeness — local size == server `Content-Length`
  (the "downloaded successfully" check); plus SHA256 against the embedded
  manifest. The manifest SHA256s are computed from the first real download and
  embedded in the committed script (same model as the 2021a script).
- Idempotent: a file present with a matching SHA256 is skipped.

## Extraction

- `--extract` (off by default): after download, extract each archive in place —
  `.tar.gz` via `tarfile`, `.gz` via `gzip` — into the file's directory.
- `--extract-existing`: skip downloading entirely; extract every archive already
  present under the selected challenges' subdirs (rescue for a user who forgot
  `--extract`).
- Raw `.nc` files (eNATL60 reference grids) are not archives — no extraction.
- Neither extract flag is exercised by the tests.

## Testing

- **Offline unit tests:** each challenge manifest well-formed (non-empty,
  unique relpaths, 64-hex SHA256s); selectors map to the right challenges;
  `--all` = all four; default data-root is relative; `--extract` defaults off.
- **`external` test:** really download the tiny **MapMed** challenge (~5 MB) to
  a temp dir and verify structure + SHA256. The large challenges are validated
  by the actual permanent-location `--all` run, not by tests.

## The run

After implementation, execute `--all` into the permanent `./data` (~80 GB) and
confirm every file downloads and verifies.

## Non-goals

No parallelism, no partial-resume, no progress bar beyond per-file logging
(YAGNI). Serial streaming with `access.fetch`'s retry handles the large files.
