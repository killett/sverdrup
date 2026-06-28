"""Reproduce the 2023 Ocean Data Challenges data downloads (4 challenges).

One script, selectable per challenge or ``--all``, SHA256-verified for exact
reproduction. Sibling to ``download_ssh_mapping_data_challenge_2021a.py``.

Challenges (official Ocean Data Challenges names):

* ``--ose``        2023a_SSH_mapping_OSE                 (MEOM mirror)
* ``--mapmed``     2023a_SSH_MapMed_OSE                  (MEOM mirror)
* ``--california`` 2023b_SSHmapping_HF_California        (MEOM mirror)
* ``--enatl60``    2023_SSH_mapping_train_eNATL60_test_NATL60  (Wasabi S3)

Run::

    python -m sverdrup.validation.download_ocean_data_challenges_2023 \
        (--all | --ose | --mapmed | --california | --enatl60) \
        [--data-root PATH] [--extract | --extract-existing]

Default ``--data-root`` is ``./data`` resolved against the current working
directory (no hard-coded absolute path); each challenge writes under
``data/<subdir>/``. All hosts are unauthenticated HTTPS.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import shutil
import tarfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from sverdrup.validation.access import fetch
from sverdrup.validation.config import ValidationConfig

_MEOM = (
    "https://ige-meom-opendap.univ-grenoble-alpes.fr/thredds/fileServer/"
    "meomopendap/extract/MEOM/OCEAN_DATA_CHALLENGES"
)
_WASABI = "https://s3.eu-central-1.wasabisys.com/melody/data_challenge_Daniel_Guillaume/public"

DEFAULT_DATA_ROOT = Path("data")


@dataclass(frozen=True)
class FileEntry:
    """One downloadable file: its path relative to the challenge base + dest."""

    relpath: str
    sha256: str  # expected content hash; "" means unknown (verify size only)


@dataclass(frozen=True)
class Challenge:
    """A single data challenge: where its files live and where they land."""

    key: str
    base_url: str
    subdir: str
    files: tuple[FileEntry, ...]


CHALLENGES: dict[str, Challenge] = {
    "ose": Challenge(
        "ose",
        f"{_MEOM}/2023a_SSH_mapping_OSE",
        "2023a_ssh_mapping_ose",
        (
            FileEntry("sad.tar.gz", ""),
            FileEntry("alongtrack.tar.gz", ""),
            FileEntry("independent_alongtrack.tar.gz", ""),
            FileEntry("independent_drifters.tar.gz", ""),
            FileEntry("maps/DUACS_global_allsat-alg.tar.gz", ""),
            FileEntry("maps/MIOST_geos_global_allsat-alg.tar.gz", ""),
            FileEntry("maps/MIOST_geos_barotrop_eqwaves_global_allsat-alg.tar.gz", ""),
            FileEntry("maps/NeurOST_SSH_allsat-alg.tar.gz", ""),
            FileEntry("maps/NeurOST_SSH-SST_allsat-alg.tar.gz", ""),
        ),
    ),
    "mapmed": Challenge(
        "mapmed",
        f"{_MEOM}/2023a_SSH_MapMed_OSE",
        "2023a_ssh_mapmed_ose",
        (
            FileEntry("dc_obs.tar.gz", ""),
            FileEntry("dc_eval.tar.gz", ""),
        ),
    ),
    "california": Challenge(
        "california",
        f"{_MEOM}/2023b_SSHmapping_HF_California",
        "2023b_sshmapping_hf_california",
        (
            FileEntry("dc_ref_eval.tar.gz", ""),
            FileEntry("dc_obs_swot.tar.gz", ""),
            FileEntry("dc_obs_nadirs.tar.gz", ""),
        ),
    ),
    "enatl60": Challenge(
        "enatl60",
        _WASABI,
        "2023_ssh_mapping_enatl60_natl60",
        (
            FileEntry("dc_ref/eNATL60-BLB002-daily-reg-1_20.nc", ""),
            FileEntry("dc_ref/eNATL60-BLB002-daily-reg-1_8.nc", ""),
            FileEntry("dc_ref/NATL60-CJM165-daily-reg-1_20.nc", ""),
            FileEntry("dc_ref/NATL60-CJM165-daily-reg-1_8.nc", ""),
            FileEntry("dc_obs/eNATL60-BLB002-alongtrack.gz", ""),
            FileEntry("dc_obs/NATL60-CJM165-alongtrack.gz", ""),
        ),
    ),
}


def sha256_of(path: Path) -> str:
    """Return the SHA256 hex digest of ``path`` (streamed, 1 MiB chunks)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _mirror_config() -> ValidationConfig:
    """Return an unauthenticated config (no creds; works for MEOM and Wasabi)."""
    return ValidationConfig(
        access_method="meom_mirror",
        aviso_username="",
        aviso_password="",
        thredds_base_url="",
        thredds_catalog_url="",
        meom_opendap_base_url="",
        data_root=DEFAULT_DATA_ROOT,
    )


def _remote_size(url: str) -> int | None:
    """Return the server Content-Length for ``url`` (None if unavailable)."""
    r = httpx.head(url, follow_redirects=True, timeout=60.0)
    r.raise_for_status()
    length = r.headers.get("content-length")
    return int(length) if length is not None else None


def download_file(
    challenge: Challenge, entry: FileEntry, data_root: Path, cfg: ValidationConfig
) -> tuple[str, str]:
    """Download + verify one file. Returns ``(status, sha256)``.

    Verifies completeness (local size == server Content-Length) and, when the
    manifest carries a SHA256, that the content matches it.

    Args:
        challenge: The owning challenge (base URL + subdir).
        entry: The file to fetch.
        data_root: Destination root; ``<data_root>/<subdir>/<relpath>``.
        cfg: Unauthenticated download config.

    Returns:
        ``(status, sha256)`` where status is ``"skipped"`` or ``"downloaded"``.

    Raises:
        ValueError: On a size or SHA256 mismatch.
    """
    url = f"{challenge.base_url}/{entry.relpath}"
    dest = data_root / challenge.subdir / entry.relpath
    if dest.exists() and entry.sha256 and sha256_of(dest) == entry.sha256:
        return "skipped", entry.sha256
    fetch(url, dest, cfg)
    expected_size = _remote_size(url)
    if expected_size is not None and dest.stat().st_size != expected_size:
        raise ValueError(
            f"incomplete download for {entry.relpath}: "
            f"{dest.stat().st_size} bytes != Content-Length {expected_size}"
        )
    digest = sha256_of(dest)
    if entry.sha256 and digest != entry.sha256:
        raise ValueError(
            f"SHA256 mismatch for {entry.relpath}: "
            f"expected {entry.sha256}, got {digest}"
        )
    return "downloaded", digest


def extract_archive(path: Path) -> bool:
    """Extract a ``.tar.gz`` (untar) or ``.gz`` (gunzip) in place.

    Args:
        path: The archive to extract.

    Returns:
        True if extracted, False if not an archive (e.g. a raw ``.nc``).
    """
    if tarfile.is_tarfile(path):
        with tarfile.open(path, "r:*") as tar:
            tar.extractall(path.parent, filter="data")  # filter: path-traversal safe
        return True
    if path.suffix == ".gz":
        out = path.with_suffix("")  # strip .gz
        with gzip.open(path, "rb") as f_in, out.open("wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        return True
    return False


def run(
    selected: list[Challenge],
    data_root: Path,
    extract: bool,
    extract_existing: bool,
) -> dict[str, str]:
    """Download (and optionally extract) the selected challenges.

    Args:
        selected: Challenges to process.
        data_root: Destination root (relative, cwd-resolved by the caller).
        extract: Extract each archive after download.
        extract_existing: Skip downloading; only extract archives already present.

    Returns:
        A mapping ``"<subdir>/<relpath>" -> status`` ("downloaded"/"skipped"/
        "extracted"/"missing").
    """
    cfg = _mirror_config()
    results: dict[str, str] = {}
    for challenge in selected:
        for entry in challenge.files:
            key = f"{challenge.subdir}/{entry.relpath}"
            dest = data_root / challenge.subdir / entry.relpath
            if extract_existing:
                if dest.exists():
                    extract_archive(dest)
                    results[key] = "extracted"
                else:
                    results[key] = "missing"
                print(f"  [{results[key]:10}] {key}", flush=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            status, digest = download_file(challenge, entry, data_root, cfg)
            if extract:
                extract_archive(dest)
            results[key] = status
            print(f"  [{status:10}] {key}  sha256={digest}", flush=True)
    return results


def _select(args: argparse.Namespace) -> list[Challenge]:
    """Resolve the selected challenges from parsed CLI flags."""
    if args.all:
        return list(CHALLENGES.values())
    keys = [k for k in CHALLENGES if getattr(args, k)]
    return [CHALLENGES[k] for k in keys]


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Reproduce the 2023 Ocean Data Challenges downloads."
    )
    parser.add_argument("--all", action="store_true", help="all four challenges")
    parser.add_argument("--ose", action="store_true", help="2023a_SSH_mapping_OSE")
    parser.add_argument("--mapmed", action="store_true", help="2023a_SSH_MapMed_OSE")
    parser.add_argument(
        "--california", action="store_true", help="2023b_SSHmapping_HF_California"
    )
    parser.add_argument(
        "--enatl60", action="store_true", help="2023 eNATL60/NATL60 (Wasabi)"
    )
    parser.add_argument("--data-root", type=Path, default=None, help="default ./data")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--extract", action="store_true", help="extract after download")
    group.add_argument(
        "--extract-existing",
        action="store_true",
        help="skip download; extract archives already present",
    )
    args = parser.parse_args()

    selected = _select(args)
    if not selected:
        parser.error(
            "select at least one challenge (--all / --ose / --mapmed / "
            "--california / --enatl60)"
        )
    root = (args.data_root or DEFAULT_DATA_ROOT).resolve()
    print(f"challenges: {[c.key for c in selected]} -> {root}", flush=True)
    run(selected, root, args.extract, args.extract_existing)
    print("done", flush=True)


if __name__ == "__main__":
    main()
