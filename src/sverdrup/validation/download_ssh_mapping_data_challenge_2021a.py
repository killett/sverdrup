"""Reproduce the SSH Mapping Data Challenge 2021a data downloads (MEOM mirror).

Exactly reproduces, on any machine, the 14 files we pulled from the
unauthenticated MEOM mirror for the "SSH Mapping Data Challenge 2021a"
(Ocean Data Challenges; repo ``ocean-data-challenges/2021a_SSH_mapping_OSE``,
Zenodo DOI 10.5281/zenodo.4045400). Each file is SHA256-verified against the
manifest below, so reproduction is provable and pinned against silent updates.

Run::

    python -m sverdrup.validation.download_ssh_mapping_data_challenge_2021a \
        [--data-root PATH]

The default ``--data-root`` is ``./data/2021a_ssh_mapping_ose`` resolved against
the current working directory (no hard-coded absolute path). Credentials are not
needed — the MEOM mirror is unauthenticated.
"""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path

from sverdrup.validation.access import fetch
from sverdrup.validation.config import ValidationConfig

MEOM_BASE = (
    "https://ige-meom-opendap.univ-grenoble-alpes.fr/thredds/fileServer/"
    "meomopendap/extract/MEOM/OCEAN_DATA_CHALLENGES/2021a-SSH-mapping-OSE"
)

DEFAULT_DATA_ROOT = Path("data/2021a_ssh_mapping_ose")


@dataclass(frozen=True)
class FileEntry:
    """One manifest entry: where the file lives and its expected content hash."""

    subdir: str
    name: str
    sha256: str
    size: int


# The 14 MEOM-mirror files, with the exact SHA256 + byte size of what we
# downloaded. Editing this list is how the script's "exact" contract is defined.
MANIFEST: tuple[FileEntry, ...] = (
    FileEntry(
        "dc_obs",
        "dt_gulfstream_alg_phy_l3_20161201-20180131_285-315_23-53.nc",
        "40040dbf5ba8c0206ab90feb62187bf4a4ea35fc0f4746a79e6e9e1fedef2386",
        22496760,
    ),
    FileEntry(
        "dc_obs",
        "dt_gulfstream_c2_phy_l3_20161201-20180131_285-315_23-53.nc",
        "9641db6101b4f082bae0d12639f9fc4e36a44d5a0f697eeb4352a74f3f1477f6",
        23604339,
    ),
    FileEntry(
        "dc_obs",
        "dt_gulfstream_h2g_phy_l3_20161201-20180131_285-315_23-53.nc",
        "4cf3e569fd159f1cbbe984bf97b8759de99a29c6642a47a9fa9dde1c8d6189d1",
        19848868,
    ),
    FileEntry(
        "dc_obs",
        "dt_gulfstream_j2g_phy_l3_20161201-20180131_285-315_23-53.nc",
        "18550993687115e73b11c76fcb0274a75d896d3da0d0107df49d88c84d76b56b",
        4142849,
    ),
    FileEntry(
        "dc_obs",
        "dt_gulfstream_j2n_phy_l3_20161201-20180131_285-315_23-53.nc",
        "b3f37425dee13128b38694f8ca6ec4835c2304f70abe9b7cf184cb340c9c6153",
        6024552,
    ),
    FileEntry(
        "dc_obs",
        "dt_gulfstream_j3_phy_l3_20161201-20180131_285-315_23-53.nc",
        "87b82fed2cb7c3e162cc1034464275dd8b6ec1292d12d842b841507fbf98bbb8",
        23175157,
    ),
    FileEntry(
        "dc_obs",
        "dt_gulfstream_s3a_phy_l3_20161201-20180131_285-315_23-53.nc",
        "d36f152d62f63b681ecd4b5456292f47c2e4423f461e05fa69eae9033efdf30b",
        22009976,
    ),
    FileEntry(
        "dc_maps",
        "OSE_ssh_mapping_4dvarNet_2022.nc",
        "f24c38ddf5bc6f26d86af2d57a096ac5207531ab0b797de77a766507c06202a1",
        58412852,
    ),
    FileEntry(
        "dc_maps",
        "OSE_ssh_mapping_BFN.nc",
        "3cda19c91965f1d128610358b565a62bfb5f8b48e16bf47bca361db98f479ff0",
        700845764,
    ),
    FileEntry(
        "dc_maps",
        "OSE_ssh_mapping_DUACS.nc",
        "8239459ea2dab859fe1f571e5eec4c51339ccc80a70485ca2439dbf6b01ae2a8",
        4684262,
    ),
    FileEntry(
        "dc_maps",
        "OSE_ssh_mapping_MIOST.nc",
        "e58caea7132d621542694e15ed262e0d5387243f2e60fe55e9ef594e3370a0c7",
        29804673,
    ),
    FileEntry(
        "dc_maps",
        "OSE_ssh_mapping_convlstm_ssh-sst.nc",
        "27f1bb5e190b11ea4ad40fd43a0f145671348d014124aec73f20c6db494d60f5",
        58413072,
    ),
    FileEntry(
        "dc_maps",
        "OSE_ssh_mapping_convlstm_ssh.nc",
        "b78d3ddd5654328f5ea80e06d17a8b7eea4e9d297d9613cf97979cbf5691e682",
        58413072,
    ),
    FileEntry(
        "dc_maps",
        "OSE_ssh_mapping_neurost_ssh-sst.nc",
        "475cad99f1711a1f82dca51632b38dd94b88dfdc56f09c3f38a12ab56b66e4ff",
        58413072,
    ),
)


def sha256_of(path: Path) -> str:
    """Return the SHA256 hex digest of ``path`` (streamed, 1 MiB chunks)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _mirror_config() -> ValidationConfig:
    """Return an unauthenticated meom_mirror config (no creds needed)."""
    return ValidationConfig(
        access_method="meom_mirror",
        aviso_username="",
        aviso_password="",
        thredds_base_url="",
        thredds_catalog_url="",
        meom_opendap_base_url=MEOM_BASE,
        data_root=DEFAULT_DATA_ROOT,
    )


def download_file(entry: FileEntry, data_root: Path, cfg: ValidationConfig) -> str:
    """Download + verify one manifest entry into ``data_root``.

    Args:
        entry: The manifest entry to fetch.
        data_root: The destination root; ``<data_root>/<subdir>/<name>``.
        cfg: A meom_mirror ``ValidationConfig`` (no auth).

    Returns:
        ``"skipped"`` if already present with a matching hash, else
        ``"downloaded"``.

    Raises:
        ValueError: If the downloaded file's SHA256 does not match the manifest.
    """
    dest = data_root / entry.subdir / entry.name
    if dest.exists() and sha256_of(dest) == entry.sha256:
        return "skipped"
    url = f"{MEOM_BASE}/{entry.subdir}/{entry.name}"
    fetch(url, dest, cfg)
    got = sha256_of(dest)
    if got != entry.sha256:
        raise ValueError(
            f"SHA256 mismatch for {entry.subdir}/{entry.name}: "
            f"expected {entry.sha256}, got {got}"
        )
    return "downloaded"


def download_all(data_root: Path | None = None) -> dict[str, str]:
    """Download + verify every manifest file into ``data_root``.

    Args:
        data_root: Destination root; defaults to ``./data/2021a_ssh_mapping_ose``
            resolved against the current working directory.

    Returns:
        A mapping ``"<subdir>/<name>" -> "downloaded"|"skipped"``.
    """
    root = (data_root or DEFAULT_DATA_ROOT).resolve()
    cfg = _mirror_config()
    results: dict[str, str] = {}
    for entry in MANIFEST:
        (root / entry.subdir).mkdir(parents=True, exist_ok=True)
        status = download_file(entry, root, cfg)
        key = f"{entry.subdir}/{entry.name}"
        results[key] = status
        print(f"  [{status:10}] {key}", flush=True)
    return results


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Reproduce the SSH Mapping Data Challenge 2021a downloads."
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Destination root (default: ./data/2021a_ssh_mapping_ose).",
    )
    args = parser.parse_args()
    print(f"downloading {len(MANIFEST)} files from MEOM mirror ...", flush=True)
    results = download_all(args.data_root)
    n_dl = sum(v == "downloaded" for v in results.values())
    print(f"done: {n_dl} downloaded, {len(results) - n_dl} already present + verified")


if __name__ == "__main__":
    main()
