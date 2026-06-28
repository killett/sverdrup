# Design — SSH Mapping Data Challenge 2021a download reproducer

## Goal

A self-contained Python script that **exactly reproduces** the 2021a challenge
data downloads on any machine, from the live unauthenticated MEOM mirror, with
content verified by SHA256 so reproduction is provable (not just "files appeared").

## Official name

The challenge is the **"SSH Mapping Data Challenge 2021a"** (Ocean Data
Challenges; repo `ocean-data-challenges/2021a_SSH_mapping_OSE`, Zenodo DOI
10.5281/zenodo.4045400). The script is named after it so a later 2023 sibling
slots beside it.

## Scope

- **In:** the 14 MEOM-mirror files — 7 `dc_obs/` along-track L3 files (5 mapping
  missions: `alg`, `h2g`, `j2g`, `j2n`, `j3`, `s3a`; + the withheld eval mission
  `c2`) and 7 `dc_maps/` reconstruction maps (`DUACS`, `MIOST`, `BFN`,
  `4dvarNet_2022`, `convlstm_ssh`, `convlstm_ssh-sst`, `neurost_ssh-sst`).
- **Out:** the git submodule (git-managed via `git submodule update --init`),
  and the AVISO-SFTP MDT (rejected/unused; the validation builds MDT from the
  tracks). MEOM is unauthenticated, so the script needs **no credentials**.

## Module + entry point

- `src/sverdrup/validation/download_ssh_mapping_data_challenge_2021a.py`
- Run: `python -m sverdrup.validation.download_ssh_mapping_data_challenge_2021a [--data-root PATH]`
- Sibling convention: a future `download_ssh_mapping_data_challenge_2023.py`.

## Behaviour

- **Manifest** (module constants): the MEOM fileServer base URL
  (`https://ige-meom-opendap.univ-grenoble-alpes.fr/thredds/fileServer/`
  `meomopendap/extract/MEOM/OCEAN_DATA_CHALLENGES/2021a-SSH-mapping-OSE`) and a
  list of `(subdir, filename, sha256, size)` for all 14 files.
- **Relative output:** default data-root `./data/2021a_ssh_mapping_ose` resolved
  against the **current working directory** (never a hard-coded `/workspace`);
  `--data-root` overrides. Subdirs `dc_obs/`, `dc_maps/` created with
  `parents=True` (no pre-existing-dir assumption).
- **Download:** reuse `access.fetch` (httpx stream + stamina transient-retry)
  with a `meom_mirror` `ValidationConfig` (no auth).
- **Verify-exact:** after each download, compute SHA256 and compare to the
  manifest; mismatch → raise (this is what guarantees exactness and pins against
  silent MEOM updates).
- **Idempotent:** a file already present whose SHA256 matches the manifest is
  skipped; missing-or-mismatched files are (re)downloaded then verified.
- Returns/prints a per-file status (downloaded / skipped-ok / verified).

## Testing

- **Offline (committed, always runs):** assert the manifest's 14 SHA256s match
  the already-downloaded files under `data/2021a_ssh_mapping_ose/` — proves the
  manifest is correct without network.
- **`external` (committed, on-demand, ~1 GB):** run the downloader into a
  `tmp_path`, then assert (a) structure = `dc_obs/`+`dc_maps/` with the 14 files,
  and (b) every re-downloaded file's SHA256 matches the manifest **and** the
  corresponding existing file.
- **Manual gate (run once now):** execute the real download into a throwaway
  temp dir and diff the resulting tree + hashes against the existing data before
  declaring done.

## Out-of-scope / non-goals

No parallelism, no resume-of-partial-files, no progress bar beyond simple
per-file logging; YAGNI. The 700 MB BFN file is the only large one; serial
streaming (with access.fetch's retry) is fine.
