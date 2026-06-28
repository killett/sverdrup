"""Validation-run configuration loaded from .env (fails loud on missing creds)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import BaseModel

AccessMethod = Literal["thredds", "meom_mirror", "ftp"]

_AUTHENTICATED: tuple[AccessMethod, ...] = ("thredds", "ftp")


class ValidationConfig(BaseModel):
    """Resolved data-access configuration for the OSE validation run."""

    access_method: AccessMethod
    aviso_username: str
    aviso_password: str
    thredds_base_url: str
    thredds_catalog_url: str
    meom_opendap_base_url: str
    data_root: Path

    @classmethod
    def load(cls, env_path: Path | None = None) -> ValidationConfig:
        """Load and validate configuration from a .env file.

        Args:
            env_path: Path to the .env file; defaults to ./.env at the repo root.

        Returns:
            A validated ``ValidationConfig``.

        Raises:
            ValueError: If an authenticated access method is selected but
                ``AVISO_USERNAME``/``AVISO_PASSWORD`` are empty.
        """
        raw = dotenv_values(env_path or Path(".env"))
        method = (raw.get("AVISO_ACCESS_METHOD") or "thredds").strip()
        user = (raw.get("AVISO_USERNAME") or "").strip()
        pw = (raw.get("AVISO_PASSWORD") or "").strip()
        if method in _AUTHENTICATED and (not user or not pw):
            raise ValueError(
                f"Access method {method!r} is authenticated but "
                "AVISO_USERNAME / AVISO_PASSWORD are empty in .env. "
                "Fill them in (cp .env.example .env; chmod 600 .env) or set "
                "AVISO_ACCESS_METHOD=meom_mirror for the unauthenticated mirror."
            )
        return cls(
            access_method=method,  # type: ignore[arg-type]
            aviso_username=user,
            aviso_password=pw,
            thredds_base_url=(raw.get("AVISO_THREDDS_BASE_URL") or "").strip(),
            thredds_catalog_url=(raw.get("AVISO_THREDDS_CATALOG_URL") or "").strip(),
            meom_opendap_base_url=(raw.get("MEOM_OPENDAP_BASE_URL") or "").strip(),
            data_root=Path(
                (raw.get("DC_DATA_ROOT") or "./data/2021a_ssh_mapping_ose").strip()
            ),
        )
