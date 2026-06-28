"""Authenticated data access for the 2021a OSE challenge products.

Source reality (2026-06-27): the original ODC THREDDS (``tds.aviso.altimetry.fr``)
is dead. The live, unauthenticated source is the MEOM mirror
(``access_method == "meom_mirror"``); ``fetch`` therefore sends no auth for that
method and HTTP Basic auth only for the authenticated ``thredds``/``ftp`` paths.
``render_netrc``/``write_dap_auth`` remain for the netCDF-C OPeNDAP stack should
an authenticated OPeNDAP endpoint return.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import stamina

from sverdrup.validation.config import ValidationConfig


def is_retryable(exc: Exception) -> bool:
    """Return True only for transient faults (transport errors + HTTP 5xx).

    Args:
        exc: The exception raised during a fetch attempt.

    Returns:
        True for httpx transport errors and 5xx responses; False for 4xx
        (e.g. 401/404) and any non-transport exception.
    """
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return 500 <= exc.response.status_code < 600
    return False


def render_netrc(host: str, user: str, password: str) -> str:
    """Render a .netrc body for the netCDF-C / OPeNDAP stack.

    Args:
        host: The remote host (``machine`` line).
        user: Login name.
        password: Login password.

    Returns:
        A ``.netrc`` file body with machine/login/password lines.
    """
    return f"machine {host}\n  login {user}\n  password {password}\n"


def write_dap_auth(cfg: ValidationConfig, home: Path) -> None:
    """Write ~/.netrc + ~/.dodsrc if the OPeNDAP stack needs file-based auth.

    Args:
        cfg: Validation config carrying credentials + the THREDDS base URL.
        home: Directory to write ``.netrc``/``.dodsrc`` into (usually ``$HOME``).
    """
    host = httpx.URL(cfg.thredds_base_url).host
    netrc = home / ".netrc"
    netrc.write_text(render_netrc(host, cfg.aviso_username, cfg.aviso_password))
    netrc.chmod(0o600)
    (home / ".dodsrc").write_text(
        f"HTTP.NETRC={netrc}\nHTTP.COOKIEJAR={home / '.dods_cookies'}\n"
    )


@stamina.retry(on=is_retryable, attempts=4)
def fetch(url: str, dest: Path, cfg: ValidationConfig) -> Path:
    """Download one file over HTTPS to ``dest`` (Basic auth only when required).

    Sends HTTP Basic credentials for the authenticated ``thredds``/``ftp``
    access methods and no auth for the unauthenticated ``meom_mirror`` mirror.
    Retries transient faults only (transport errors + 5xx); a 401/404 raises.

    Args:
        url: Absolute URL of the remote NetCDF (e.g. a THREDDS FileServer or
            MEOM fileServer URL).
        dest: Local destination path (parent dirs created as needed).
        cfg: Validation config carrying credentials + access method.

    Returns:
        The local ``dest`` path.
    """
    auth: tuple[str, str] | None = None
    if cfg.access_method in ("thredds", "ftp"):
        auth = (cfg.aviso_username, cfg.aviso_password)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream(
        "GET", url, auth=auth, follow_redirects=True, timeout=120.0
    ) as response:
        response.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in response.iter_bytes():
                fh.write(chunk)
    return dest
