# OI Validation vs 2021a SSH-mapping OSE BASELINE — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `src/sverdrup/validation/` harness that reproduces the challenge's published BASELINE (OI) leaderboard row by configuring our OI engine from `baseline_oi.ipynb`, mapping the five-mission constellation over the 2017 Gulf Stream box, and scoring with the challenge's own eval code.

**Architecture:** Eight focused modules in a new `src/sverdrup/validation/` package. The challenge repo is a git submodule (`vendor/2021a_SSH_mapping_OSE`) pinned to the leaderboard-matching commit; their scoring functions are imported as ground truth. Our OI is driven through the existing `methods/oi.py` seam; a net-new xarray NetCDF output adapter matches their map schema field-for-field. Four HOLD-gated user-gates correspond to scope-spec Tasks 0–3.

**Tech Stack:** Python, xarray, numpy, scipy, httpx, stamina, pydantic, python-dotenv, pytest. Their eval may pull `pyinterp`. Internal reuse: `core/observations.py` (`ObsWindow`, `DiagonalErrorModel`), `methods/oi.py` (`OptimalInterpolation`), `core/parameters.py` (`ConstantProvider`), `core/grid.py` (`GridSpec.lonlat`), `eval/aggregate.py` (`area_weighted_rmse`).

**User decisions (already made):**
- Validation code lives in `src/sverdrup/validation/` package (importable, full test/mypy/ruff discipline). — "src/sverdrup/validation/ package"
- Drive THEIR eval by importing their `src` scoring functions into our pixi env (no full 2021 conda env). — "Import their src/ functions into our env"
- Challenge repo vendored as a git submodule pinned to the leaderboard-matching commit (not master HEAD). — design §1/§3
- Task 0's day-one deliverable: their scorer imports, runs on their own BASELINE map, reproduces all three published numbers (µ, σ, λx). — design §0/§4
- Single tile, single OI, SSH scores only; their eval is ground truth, ours is a parallel cross-check. — `validation_scope_spec.md`
- PASS tolerance set after seeing the spread; never loosened to manufacture a pass. — design §6

---

## File Structure

| Path | Responsibility |
|---|---|
| `src/sverdrup/validation/__init__.py` | Package marker; public exports. |
| `src/sverdrup/validation/config.py` | `.env` → pydantic `ValidationConfig`; fail-loud on empty creds under an authenticated access method. |
| `src/sverdrup/validation/access.py` | THREDDS/OPeNDAP/FileServer fetch (httpx Basic Auth, stamina retry); `.netrc`/`.dodsrc` generation; mirror/ftp fallbacks; catalog-URL verification. |
| `src/sverdrup/validation/their_eval.py` | Import the vendored challenge scoring functions; run on a map+track → `(mu, sigma, lambda_x)`. |
| `src/sverdrup/validation/input_adapter.py` | Five-mission L3 NetCDF → `ObsWindow`; Cryosat-2 → separate eval-only track; spin-up window; reference-frame handling. |
| `src/sverdrup/validation/output_adapter.py` | OI map → `xarray.Dataset` → NetCDF matching `OSE_ssh_mapping_BASELINE.nc` field-for-field. |
| `src/sverdrup/validation/params.py` | `baseline_oi.ipynb` params → `ConstantProvider` + `GridSpec` + temporal window; emits the audit trail. |
| `src/sverdrup/validation/run.py` | Drive 2017 single-tile OI (sliding temporal window) → daily maps → output NetCDF. |
| `src/sverdrup/validation/report.py` | Our `area_weighted_rmse` cross-check + result table + decomposed read. |
| `docs/validation/parameter_audit_trail.md` | The committed audit trail (Task 1 deliverable). |
| `tests/validation/test_*.py` | Unit tests per module (test-design discipline). |
| `vendor/2021a_SSH_mapping_OSE` | Git submodule (their MIT code), pinned commit. |

---

## Task 0: Config + secrets wiring

**Goal:** Load `.env` into a validated `ValidationConfig` that fails loud on missing creds, and finalize `.gitignore` so `.env` is ignored while `.env.example` is tracked.

**Files:**
- Create: `src/sverdrup/validation/__init__.py`
- Create: `src/sverdrup/validation/config.py`
- Create: `tests/validation/__init__.py`
- Create: `tests/validation/test_config.py`
- Modify: `.gitignore` (append only missing patterns from `gitignore_additions.txt`)

**Acceptance Criteria:**
- [ ] `git check-ignore -v .env` prints a match; `git check-ignore .env.example` exits non-zero (not ignored).
- [ ] `ValidationConfig.load()` raises a clear error naming `AVISO_USERNAME`/`AVISO_PASSWORD` when they are empty and `access_method` is `thredds` or `ftp`.
- [ ] `ValidationConfig.load()` succeeds with empty creds when `access_method == "meom_mirror"`.

**Verify:** `pixi run test tests/validation/test_config.py -v` → all pass; `git check-ignore -v .env .env.example` → `.env` matched, `.env.example` not.

**Steps:**

- [ ] **Step 1: Append missing `.gitignore` patterns.** Read the current `.gitignore`; for each line in `gitignore_additions.txt` not already present, append it. CRITICAL: `!.env.example` MUST come after `.env.*`. After editing, verify:

```bash
git check-ignore -v .env .env.example || true
# expected: .env matched by a .gitignore rule; .env.example prints nothing (exit 1)
```

- [ ] **Step 2: Write the failing tests.**

```python
# tests/validation/test_config.py
import pytest
from sverdrup.validation.config import ValidationConfig


def test_authenticated_method_with_empty_creds_fails_loud(tmp_path, monkeypatch):
    """thredds with empty creds must raise naming the missing vars.

    Catches a silent no-auth fallthrough that would later 401 deep in a fetch.
    """
    env = tmp_path / ".env"
    env.write_text("AVISO_ACCESS_METHOD=thredds\nAVISO_USERNAME=\nAVISO_PASSWORD=\n")
    with pytest.raises(ValueError, match="AVISO_USERNAME"):
        ValidationConfig.load(env_path=env)


def test_meom_mirror_allows_empty_creds(tmp_path):
    """meom_mirror is unauthenticated, so empty creds must be accepted.

    Catches an over-eager validator that blocks the no-auth fallback path.
    """
    env = tmp_path / ".env"
    env.write_text(
        "AVISO_ACCESS_METHOD=meom_mirror\nAVISO_USERNAME=\nAVISO_PASSWORD=\n"
        "MEOM_OPENDAP_BASE_URL=https://example.org/thredds\n"
    )
    cfg = ValidationConfig.load(env_path=env)
    assert cfg.access_method == "meom_mirror"
```

- [ ] **Step 3: Run tests, confirm they fail.** Run: `pixi run test tests/validation/test_config.py -v` → FAIL (module not found).

- [ ] **Step 4: Implement `config.py`.**

```python
# src/sverdrup/validation/config.py
"""Validation-run configuration loaded from .env (fails loud on missing creds)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import BaseModel

AccessMethod = Literal["thredds", "meom_mirror", "ftp"]


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
    def load(cls, env_path: Path | None = None) -> "ValidationConfig":
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
        if method in ("thredds", "ftp") and (not user or not pw):
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
            data_root=Path((raw.get("DC_DATA_ROOT") or "./data/2021a_ssh_mapping_ose").strip()),
        )
```

```python
# src/sverdrup/validation/__init__.py
"""OI validation harness against the 2021a SSH-mapping OSE challenge."""

from sverdrup.validation.config import ValidationConfig

__all__ = ["ValidationConfig"]
```

```python
# tests/validation/__init__.py
```

- [ ] **Step 5: Run tests, confirm pass.** Run: `pixi run test tests/validation/test_config.py -v` → PASS. Then `pixi run typecheck` and `pixi run lint` → clean.

- [ ] **Step 6: Commit.**

```bash
git add src/sverdrup/validation/__init__.py src/sverdrup/validation/config.py \
        tests/validation/__init__.py tests/validation/test_config.py .gitignore
git commit -m "feat(validation): .env config loader (fail-loud) + .gitignore secrets wiring"
```

---

## Task 1: Vendor submodule + their-eval de-risk spike (USER-GATE)

**Goal:** Pin the challenge repo as a submodule at the leaderboard-matching commit, import one of their scoring functions, run it end-to-end on their *own* shipped BASELINE map, and reproduce all three published numbers (µ ≈ 0.85, σ ≈ 0.09, λx ≈ 140 km) — de-risking the "their eval is ground truth" premise on day one.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Create: `vendor/2021a_SSH_mapping_OSE` (git submodule, pinned commit)
- Modify: `.gitmodules`
- Create: `src/sverdrup/validation/their_eval.py`
- Create: `tests/validation/test_their_eval_spike.py`
- Modify: `pixi.toml` (add only the deps their scoring functions import, e.g. `pyinterp`, if missing)
- Append: `docs/validation/parameter_audit_trail.md` (record the pinned SHA + the reproduced numbers)

**Acceptance Criteria:**
- [ ] The submodule is pinned to a recorded commit/release that corresponds to the published leaderboard (VERIFY against the live repo; the source wins over any remembered tag).
- [ ] `their_eval.score(map_path, track_path)` imports the challenge scoring functions from the submodule and returns `(mu, sigma, lambda_x)` floats.
- [ ] Running it on the shipped `OSE_ssh_mapping_BASELINE.nc` + the withheld Cryosat-2 track reproduces µ ≈ 0.85 (±0.02), σ ≈ 0.09 (±0.02), λx ≈ 140 km (±10) — **all three**.
- [ ] The pinned SHA and the three reproduced numbers are written into `docs/validation/parameter_audit_trail.md`.

**Verify:** `pixi run test tests/validation/test_their_eval_spike.py -v -m external` → reproduces the three published numbers (skipped with a clear reason if the challenge data is not yet present locally).

**Steps:**

- [ ] **Step 1: Add the submodule, pinned.** Identify the commit/release matching the published leaderboard by browsing the live repo's releases/tags and the eval notebooks the leaderboard cites. Then:

```bash
git submodule add https://github.com/ocean-data-challenges/2021a_SSH_mapping_OSE.git vendor/2021a_SSH_mapping_OSE
cd vendor/2021a_SSH_mapping_OSE && git checkout <LEADERBOARD_COMMIT_SHA> && cd -
git add .gitmodules vendor/2021a_SSH_mapping_OSE
# record the SHA you pinned in docs/validation/parameter_audit_trail.md
```

- [ ] **Step 2: Inventory their scoring API.** From the submodule, locate the RMSE-based (µ, σ) and spectral (λx) scoring functions in `src/` and the `example_data_eval` notebook. Record the exact import path and call signature (this is recon output — the test in Step 3 asserts the *numbers*, which are known, regardless of the function name). Note what inputs they expect (map NetCDF path/Dataset, track path, mask/aux files).

- [ ] **Step 3: Write the spike test (asserts the known published numbers).**

```python
# tests/validation/test_their_eval_spike.py
import pytest
from sverdrup.validation.their_eval import score
from sverdrup.validation.config import ValidationConfig

pytestmark = pytest.mark.external  # requires challenge data + submodule


def test_their_eval_reproduces_published_baseline():
    """Their scorer on their own BASELINE map reproduces the leaderboard row.

    Catches version-skew (pinned eval != leaderboard eval) and a broken import
    path BEFORE any adapter is built. All three numbers must land, not just mu.
    """
    cfg = ValidationConfig.load()
    root = cfg.data_root
    map_path = root / "dc_maps" / "OSE_ssh_mapping_BASELINE.nc"
    track_path = next((root / "dc_obs").glob("*c2*l3*.nc"))
    if not map_path.exists() or not track_path.exists():
        pytest.skip(f"challenge data not present under {root}; fetch first (Task 2)")
    mu, sigma, lambda_x = score(map_path, track_path)
    assert mu == pytest.approx(0.85, abs=0.02), f"mu={mu}"
    assert sigma == pytest.approx(0.09, abs=0.02), f"sigma={sigma}"
    assert lambda_x == pytest.approx(140.0, abs=10.0), f"lambda_x={lambda_x}"
```

Register the `external` marker in `pyproject.toml` `[tool.pytest.ini_options].markers` if not already present.

- [ ] **Step 4: Implement `their_eval.py` as a thin wrapper over their functions.**

```python
# src/sverdrup/validation/their_eval.py
"""Drive the challenge's own scoring functions (ground truth) on a map + track."""

from __future__ import annotations

import sys
from pathlib import Path

_VENDOR = Path(__file__).resolve().parents[3] / "vendor" / "2021a_SSH_mapping_OSE"


def _ensure_on_path() -> None:
    """Put the vendored challenge ``src`` on sys.path for import."""
    src = _VENDOR / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def score(map_path: Path, track_path: Path) -> tuple[float, float, float]:
    """Score a gridded SSH map against the withheld track using THEIR code.

    Args:
        map_path: Path to a gridded map NetCDF in the challenge schema.
        track_path: Path to the withheld Cryosat-2 along-track NetCDF.

    Returns:
        ``(mu_rmse, sigma_rmse, lambda_x_km)`` as computed by the challenge's
        own RMSE-based and spectral scoring functions.
    """
    _ensure_on_path()
    # Import the actual functions discovered in Step 2; the names below are the
    # recon output recorded in the audit trail. Wire their documented call form.
    from mod_eval import rmse_based_scores, psd_based_scores  # type: ignore

    mu, sigma = rmse_based_scores(str(map_path), str(track_path))
    lambda_x = psd_based_scores(str(map_path), str(track_path))
    return float(mu), float(sigma), float(lambda_x)
```

(If their `src` won't import or run in our env, STOP and surface it — the fallback is vendoring just the scoring math, a different build. Do not paper over it.)

- [ ] **Step 5: Run the spike.** Fetch the shipped BASELINE map + the Cryosat-2 track first if not present (the unauthenticated `meom_mirror` is the simplest source for this one file; Task 2 generalizes access). Run: `pixi run test tests/validation/test_their_eval_spike.py -v -m external` → the three numbers reproduce.

- [ ] **Step 6: Record + commit.** Write the pinned SHA and the three reproduced numbers into `docs/validation/parameter_audit_trail.md`. Commit.

```bash
git add .gitmodules vendor/2021a_SSH_mapping_OSE src/sverdrup/validation/their_eval.py \
        tests/validation/test_their_eval_spike.py docs/validation/parameter_audit_trail.md \
        pixi.toml pyproject.toml
git commit -m "feat(validation): vendor challenge submodule + their-eval spike reproduces BASELINE (mu/sigma/lambda_x)"
```

**HOLD (gate 0, part A):** report the pinned SHA, the three reproduced numbers, and any import/version surprise. Do not proceed to the full run premise until the owner confirms the spike.

---

## Task 2: Access adapter + live smoke test (USER-GATE)

**Goal:** Verify the live THREDDS catalog URL and the exact auth mechanism, fetch one small remote NetCDF through the selected access path, and confirm we can read it.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Create: `src/sverdrup/validation/access.py`
- Create: `tests/validation/test_access.py`

**Acceptance Criteria:**
- [ ] The live THREDDS catalog URL for the 2021a products is confirmed to resolve, and the auth mechanism (HTTP Basic header vs `.netrc`/`.dodsrc`) is recorded.
- [ ] `access.fetch(remote_name, cfg)` downloads one small file (or reads one OPeNDAP header) and the result opens as a NetCDF (`xarray.open_dataset` succeeds; dims/vars readable).
- [ ] `access.fetch` retries only transient faults (transport errors + 5xx) and surfaces a clear auth error on 401.

**Verify:** `pixi run test tests/validation/test_access.py -v` (unit: retry predicate + `.netrc` rendering, offline) AND a captured live smoke read of one remote NetCDF header through the selected method.

**Steps:**

- [ ] **Step 1: Write offline unit tests** (retry predicate + `.netrc`/`.dodsrc` rendering — the live read is captured manually, not in CI).

```python
# tests/validation/test_access.py
import httpx
from sverdrup.validation.access import is_retryable, render_netrc


def test_is_retryable_5xx_and_transport_only():
    """Retry 5xx + transport errors; never retry a 401/404.

    Catches a predicate that would hammer an auth failure or hide a 404.
    """
    assert is_retryable(httpx.HTTPStatusError("x", request=None, response=httpx.Response(503)))
    assert is_retryable(httpx.ConnectError("boom"))
    assert not is_retryable(httpx.HTTPStatusError("x", request=None, response=httpx.Response(401)))


def test_render_netrc_contains_host_and_creds():
    """.netrc rendering includes machine + login + password lines.

    Catches a malformed .netrc that the netCDF-C OPeNDAP stack silently ignores.
    """
    text = render_netrc("tds.aviso.altimetry.fr", "user", "secret")
    assert "machine tds.aviso.altimetry.fr" in text
    assert "login user" in text and "password secret" in text
```

- [ ] **Step 2: Run tests, confirm fail.** Run: `pixi run test tests/validation/test_access.py -v` → FAIL (module not found).

- [ ] **Step 3: Implement `access.py`** (httpx Basic Auth + stamina retry following the `adapters/odc/download.py::_is_retryable` pattern; `.netrc`/`.dodsrc` generation for the OPeNDAP stack; mirror/ftp branch).

```python
# src/sverdrup/validation/access.py
"""Authenticated data access for the 2021a OSE challenge products."""

from __future__ import annotations

from pathlib import Path

import httpx
import stamina

from sverdrup.validation.config import ValidationConfig


def is_retryable(exc: Exception) -> bool:
    """Return True only for transient faults (transport errors + HTTP 5xx)."""
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return 500 <= exc.response.status_code < 600
    return False


def render_netrc(host: str, user: str, password: str) -> str:
    """Render a .netrc body for the netCDF-C / OPeNDAP stack."""
    return f"machine {host}\n  login {user}\n  password {password}\n"


def write_dap_auth(cfg: ValidationConfig, home: Path) -> None:
    """Write ~/.netrc + ~/.dodsrc if the OPeNDAP stack needs file-based auth."""
    host = httpx.URL(cfg.thredds_base_url).host
    (home / ".netrc").write_text(render_netrc(host, cfg.aviso_username, cfg.aviso_password))
    (home / ".netrc").chmod(0o600)
    (home / ".dodsrc").write_text(f"HTTP.NETRC={home / '.netrc'}\nHTTP.COOKIEJAR={home / '.dods_cookies'}\n")


@stamina.retry(on=is_retryable, attempts=4)
def fetch(url: str, dest: Path, cfg: ValidationConfig) -> Path:
    """Download one file via HTTPS Basic Auth (THREDDS FileServer) to ``dest``.

    Args:
        url: Absolute FileServer URL of the remote NetCDF.
        dest: Local destination path.
        cfg: Validation config carrying credentials + access method.

    Returns:
        The local ``dest`` path.
    """
    auth = None
    if cfg.access_method in ("thredds", "ftp"):
        auth = (cfg.aviso_username, cfg.aviso_password)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, auth=auth, follow_redirects=True, timeout=60.0) as r:
        r.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in r.iter_bytes():
                fh.write(chunk)
    return dest
```

- [ ] **Step 4: Run unit tests, confirm pass.** Run: `pixi run test tests/validation/test_access.py -v` → PASS. `pixi run typecheck && pixi run lint` → clean.

- [ ] **Step 5: Live smoke read (captured).** With the owner's filled-in `.env`, resolve the live 2021a catalog URL by browsing the THREDDS catalog, then fetch one small file (e.g. one mission's L3 header, or the BASELINE map metadata) and open it:

```bash
pixi run python -c "import xarray as xr; print(xr.open_dataset('<local_or_opendap_url>'))"
```

Record the verified catalog URL + the working auth mechanism in `docs/validation/parameter_audit_trail.md`.

- [ ] **Step 6: Commit.**

```bash
git add src/sverdrup/validation/access.py tests/validation/test_access.py docs/validation/parameter_audit_trail.md
git commit -m "feat(validation): THREDDS access adapter + verified catalog/auth smoke read"
```

**HOLD (gate 0, part B):** report the verified catalog URL, the working auth path, and any spec discrepancy from recon. Do not proceed to bulk download / parameter extraction until the owner confirms.

---

## Task 3: Parameter extraction + audit trail (USER-GATE)

**Goal:** Read `baseline_oi.ipynb` in full, extract every OI parameter into our config, resolve the SLA-vs-SSH / MDT reference frame explicitly, and produce the parameter audit trail.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured. A wrong parameter reading here invalidates the whole claim.

**Files:**
- Create: `src/sverdrup/validation/params.py`
- Create: `tests/validation/test_params.py`
- Append: `docs/validation/parameter_audit_trail.md`

**Acceptance Criteria:**
- [ ] Every OI baseline parameter is extracted from `baseline_oi.ipynb`: spatial correlation length scale(s) (+ any lat/anisotropy dependence), temporal correlation window, signal variance, noise variance, OI influence radius / neighbourhood, the output grid (resolution + the 285–315/23–53 box + time stepping), and along-track preprocessing (detrending, MDT, editing).
- [ ] The audit trail maps each value → its notebook cell/line → our setting (`variance`, `length_scale`, `time_scale`, error-model noise, grid, temporal window).
- [ ] The audit trail states explicitly which quantity (SLA or SSH) flows at each stage and where the MDT (`mdt.nc`) enters — design §5.
- [ ] `baseline_config()` returns a `ConstantProvider`, a `GridSpec` over the box, and the temporal half-window (days) that `OptimalInterpolation.solve` accepts without error.

**Verify:** `pixi run test tests/validation/test_params.py -v` → the provider resolves all three OI param names to floats and the grid covers the box; the audit-trail file exists with the reference-frame section filled.

**Steps:**

- [ ] **Step 1: Read the notebook + extract.** Read `vendor/2021a_SSH_mapping_OSE/notebooks/baseline_oi.ipynb` end to end. For each parameter, note the cell/line and value. Resolve the reference frame: are the L3 inputs SLA? Does their map/eval compare in SLA or SSH space? Where does `mdt.nc` get added/subtracted? Record all of it in `docs/validation/parameter_audit_trail.md`.

- [ ] **Step 2: Write the failing test** (values filled from Step 1 extraction — shown here with the box + names that are already known; substitute the exact scalars you extract).

```python
# tests/validation/test_params.py
from sverdrup.validation.params import baseline_config
from sverdrup.core.grid import GridSpec


def test_baseline_config_resolves_oi_params_and_box():
    """The extracted config resolves all OI params and covers the GS box.

    Catches a mis-wired parameter name (OI reads variance/length_scale/time_scale)
    or a grid that does not cover lon 285-315 / lat 23-53.
    """
    provider, grid, temporal_half_window_days = baseline_config()
    assert isinstance(grid, GridSpec)
    for name in ("variance", "length_scale", "time_scale"):
        assert isinstance(float(provider.resolve(name, grid)), float)
    lon, lat = grid._lonlat_nodes()
    assert lon.min() >= 285.0 - 1e-6 and lon.max() <= 315.0 + 1e-6
    assert lat.min() >= 23.0 - 1e-6 and lat.max() <= 53.0 + 1e-6
    assert temporal_half_window_days > 0
```

- [ ] **Step 3: Run test, confirm fail.** Run: `pixi run test tests/validation/test_params.py -v` → FAIL (module not found).

- [ ] **Step 4: Implement `params.py`** (fill the scalars from Step 1; the structure below is fixed — only the extracted numbers vary).

```python
# src/sverdrup/validation/params.py
"""baseline_oi.ipynb parameters translated into our OI config (audit-trailed)."""

from __future__ import annotations

from sverdrup.core.grid import GridSpec
from sverdrup.core.parameters import ConstantProvider


def baseline_config() -> tuple[ConstantProvider, GridSpec, float]:
    """Return the baseline_oi OI provider, output grid, and temporal half-window.

    Values are transcribed from baseline_oi.ipynb; see
    docs/validation/parameter_audit_trail.md for the cell-by-cell mapping.

    Returns:
        ``(provider, grid, temporal_half_window_days)``. ``provider`` resolves
        ``variance`` (signal variance), ``length_scale`` (km, spatial corr.),
        and ``time_scale`` (days, temporal corr.). ``grid`` is the 285-315 /
        23-53 box at the notebook's resolution.
    """
    provider = ConstantProvider(
        {
            "variance": SIGNAL_VARIANCE,        # <- from notebook (signal variance)
            "length_scale": SPATIAL_CORR_KM,    # <- from notebook (spatial corr length)
            "time_scale": TEMPORAL_CORR_DAYS,   # <- from notebook (temporal corr window)
        }
    )
    grid = GridSpec.lonlat(
        lon=_arange(285.0, 315.0, GRID_RES_DEG),  # <- from notebook (resolution)
        lat=_arange(23.0, 53.0, GRID_RES_DEG),
    )
    return provider, grid, TEMPORAL_HALF_WINDOW_DAYS  # <- influence window in days
```

(The per-obs **noise variance** is NOT a kernel param — it is carried into `DiagonalErrorModel.variance` by `input_adapter.py` in Task 4. Record its extracted value in the audit trail and expose it as a module constant `OBS_NOISE_VARIANCE` here so Task 4 imports it.)

- [ ] **Step 5: Run test, confirm pass.** Run: `pixi run test tests/validation/test_params.py -v` → PASS. `pixi run typecheck && pixi run lint` → clean.

- [ ] **Step 6: Commit.**

```bash
git add src/sverdrup/validation/params.py tests/validation/test_params.py docs/validation/parameter_audit_trail.md
git commit -m "feat(validation): extract baseline_oi params + audit trail (SLA/SSH/MDT resolved)"
```

**HOLD (gate 1):** present the audit trail. Owner confirms the parameter mapping AND the reference-frame decision before any run.

---

## Task 4: Input adapter — five missions → ObsWindow, Cryosat-2 held out

**Goal:** Convert the five-mission L3 along-track NetCDF into an `ObsWindow` (with per-obs noise in a `DiagonalErrorModel`), load Cryosat-2 into a separate eval-only structure the mapping path cannot read, honour the spin-up window, and apply the reference-frame handling from the audit trail.

**Files:**
- Create: `src/sverdrup/validation/input_adapter.py`
- Create: `tests/validation/test_input_adapter.py`
- Create: `tests/validation/fixtures/` (one small real subset NetCDF per the data discipline)

**Acceptance Criteria:**
- [ ] `load_mapping_obs(paths, cfg, params)` returns an `ObsWindow` whose `mission` labels are exactly the five mapping missions — Cryosat-2 NEVER present.
- [ ] `load_eval_track(path)` returns the Cryosat-2 track as a separate object (not an `ObsWindow` feedable to OI).
- [ ] Observations from 2016-12-01 onward are present in the mapping `ObsWindow` (spin-up included); the eval track is restricted to 2017.
- [ ] The quantity loaded matches the audit trail's reference-frame decision (SLA or SSH; MDT applied where the trail says).

**Verify:** `pixi run test tests/validation/test_input_adapter.py -v` → all pass, using the committed fixture (offline).

**Steps:**

- [ ] **Step 1: Commit a small real fixture.** Subset one mapping mission's L3 + a Cryosat-2 slice to a few days, small lon/lat box, into `tests/validation/fixtures/` (keep it tiny; bulk data stays gitignored). Record provenance in the audit trail.

- [ ] **Step 2: Write the failing tests** (the two load-bearing bugs: withheld leak + spin-up window).

```python
# tests/validation/test_input_adapter.py
import numpy as np
from sverdrup.validation.input_adapter import load_mapping_obs, load_eval_track
from sverdrup.core.observations import ObsWindow

FIVE = {"alg", "j2", "j3", "s3a", "h2g"}  # mission codes per recon; fix to actual


def test_withheld_cryosat2_never_in_mapping_set(mapping_fixture_paths, baseline_cfg, baseline_provider):
    """Cryosat-2 must never appear in the mapping ObsWindow.

    Catches a withheld-mission leak that would invalidate the OSE score.
    """
    obs = load_mapping_obs(mapping_fixture_paths, baseline_cfg, baseline_provider)
    assert isinstance(obs, ObsWindow)
    missions = set(np.unique(obs.mission).tolist())
    assert "c2" not in missions and missions <= FIVE


def test_spinup_obs_included_in_mapping_input(mapping_fixture_paths, baseline_cfg, baseline_provider):
    """Obs from 2016-12-01 onward are present in the mapping input.

    Catches an eval-window boundary error that would starve early-2017 maps of
    their temporal neighbours.
    """
    obs = load_mapping_obs(mapping_fixture_paths, baseline_cfg, baseline_provider)
    times = obs.coords()[:, 2]
    assert times.min() < 0.0  # day 0 == 2017-01-01; spin-up is negative days
```

(Define `mapping_fixture_paths`, `baseline_cfg`, `baseline_provider` fixtures in a `tests/validation/conftest.py` pointing at the committed fixture + `baseline_config()`.)

- [ ] **Step 3: Run tests, confirm fail.** Run: `pixi run test tests/validation/test_input_adapter.py -v` → FAIL.

- [ ] **Step 4: Implement `input_adapter.py`.**

```python
# src/sverdrup/validation/input_adapter.py
"""Challenge L3 along-track NetCDF -> our ObsWindow (Cryosat-2 held out)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import xarray as xr

from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ParameterProvider
from sverdrup.validation.config import ValidationConfig
from sverdrup.validation.params import OBS_NOISE_VARIANCE

# day 0 == 2017-01-01; spin-up obs carry negative day numbers.
EPOCH = np.datetime64("2017-01-01")


@dataclass(frozen=True)
class EvalTrack:
    """The withheld Cryosat-2 track — eval only, never feedable to OI."""

    lon: np.ndarray
    lat: np.ndarray
    time_days: np.ndarray
    sla: np.ndarray


def _days_since_epoch(times: np.ndarray) -> np.ndarray:
    """Convert datetime64 times to float days since 2017-01-01."""
    return (times - EPOCH) / np.timedelta64(1, "D")


def load_mapping_obs(
    paths: list[Path], cfg: ValidationConfig, params: ParameterProvider
) -> ObsWindow:
    """Load the five mapping missions into one ObsWindow (SLA, spin-up included).

    Args:
        paths: L3 NetCDF paths for the five mapping missions (NO Cryosat-2).
        cfg: Validation config (unused here beyond provenance; kept for symmetry).
        params: Parameter provider (records provenance of the run).

    Returns:
        An ``ObsWindow`` with per-obs noise in a ``DiagonalErrorModel``.
    """
    lon, lat, tim, sla, mis = [], [], [], [], []
    for p in paths:
        ds = xr.open_dataset(p)
        n = ds["longitude"].size
        lon.append(np.asarray(ds["longitude"]).reshape(n))
        lat.append(np.asarray(ds["latitude"]).reshape(n))
        tim.append(_days_since_epoch(np.asarray(ds["time"]).reshape(n)))
        sla.append(np.asarray(ds["sla_filtered"]).reshape(n))  # var name from recon
        mis.append(np.full(n, _mission_code(p)))
    lon_a = np.concatenate(lon)
    values = np.concatenate(sla)
    err = DiagonalErrorModel(np.full(values.size, OBS_NOISE_VARIANCE))
    return ObsWindow.from_arrays(
        lon_a, np.concatenate(lat), np.concatenate(tim), values, err,
        mission=np.concatenate(mis),
    )


def load_eval_track(path: Path) -> EvalTrack:
    """Load the withheld Cryosat-2 track for evaluation only (2017 restricted)."""
    ds = xr.open_dataset(path)
    t = _days_since_epoch(np.asarray(ds["time"]))
    keep = t >= 0.0  # eval is 2017 only; no spin-up in the eval track
    return EvalTrack(
        np.asarray(ds["longitude"])[keep], np.asarray(ds["latitude"])[keep],
        t[keep], np.asarray(ds["sla_filtered"])[keep],
    )


def _mission_code(path: Path) -> str:
    """Map a filename to its mission code (from the challenge naming)."""
    name = path.name.lower()
    for code in ("alg", "j2", "j3", "s3a", "h2g"):
        if code in name:
            return code
    raise ValueError(f"unrecognised mapping mission in {path.name}")
```

(Exact variable names — `longitude`/`latitude`/`time`/`sla_filtered` — and mission codes are recon outputs from the live L3 files; substitute the verified names. Apply the audit-trail reference-frame step here if the eval compares in SSH space: add `mdt` where the trail says.)

- [ ] **Step 5: Run tests, confirm pass.** Run: `pixi run test tests/validation/test_input_adapter.py -v` → PASS. `pixi run typecheck && pixi run lint` → clean.

- [ ] **Step 6: Commit.**

```bash
git add src/sverdrup/validation/input_adapter.py tests/validation/test_input_adapter.py \
        tests/validation/conftest.py tests/validation/fixtures/
git commit -m "feat(validation): input adapter — five missions -> ObsWindow, Cryosat-2 held out"
```

---

## Task 5: Output adapter — OI map → challenge NetCDF schema (USER-GATE)

**Goal:** Write our gridded OI map to a NetCDF that matches `OSE_ssh_mapping_BASELINE.nc` field-for-field, so their eval ingests it unchanged.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Create: `src/sverdrup/validation/output_adapter.py`
- Create: `tests/validation/test_output_adapter.py`

**Acceptance Criteria:**
- [ ] `write_map(times, lats, lons, ssh, dest)` produces a NetCDF whose dimensions, coordinate names + order, SSH variable name + units, time axis encoding, and fill/mask convention match the shipped BASELINE map exactly (field-for-field comparison of names/dtypes/units, not values).
- [ ] The written file round-trips through `their_eval.score` (it ingests unchanged and returns three floats).

**Verify:** `pixi run test tests/validation/test_output_adapter.py -v` → schema-match assertions pass against the shipped BASELINE header (committed as a tiny schema fixture or the local file, marked `external` if it needs the full file).

**Steps:**

- [ ] **Step 1: Capture the BASELINE schema** (from Task 0/2). Record dims, coord names/order, the SSH var name + units + dtype, time units/calendar, `_FillValue`/mask. Put a tiny schema-only fixture (a header/CDL or a 1×2×2 sample written in their schema) under `tests/validation/fixtures/`.

- [ ] **Step 2: Write the failing schema-match test.**

```python
# tests/validation/test_output_adapter.py
import numpy as np
import xarray as xr
from sverdrup.validation.output_adapter import write_map


def test_output_matches_baseline_schema(tmp_path, baseline_schema_ref):
    """Our NetCDF matches the BASELINE schema field-for-field.

    Catches a silent number-shifter: wrong coord order, var name, units, or
    fill convention that their eval would misread.
    """
    ref = xr.open_dataset(baseline_schema_ref)
    ssh_name = list(ref.data_vars)[0]  # the SSH variable in their schema
    dest = tmp_path / "ours.nc"
    write_map(
        times=ref["time"].values[:1],
        lats=ref["lat"].values, lons=ref["lon"].values,
        ssh=np.zeros((1, ref.sizes["lat"], ref.sizes["lon"])),
        dest=dest,
    )
    ours = xr.open_dataset(dest)
    assert list(ours.dims) == list(ref.dims)
    assert list(ours.coords) == list(ref.coords)
    assert ssh_name in ours.data_vars
    assert ours[ssh_name].dims == ref[ssh_name].dims
    assert ours[ssh_name].attrs.get("units") == ref[ssh_name].attrs.get("units")
```

(`baseline_schema_ref` fixture points at the tiny schema sample from Step 1.)

- [ ] **Step 3: Run test, confirm fail.** Run: `pixi run test tests/validation/test_output_adapter.py -v` → FAIL.

- [ ] **Step 4: Implement `output_adapter.py`** (fill `SSH_VAR`, `SSH_UNITS`, coord names, time encoding from the captured schema).

```python
# src/sverdrup/validation/output_adapter.py
"""Our gridded OI map -> NetCDF in the challenge BASELINE schema."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

SSH_VAR = "ssh"          # <- exact name from the BASELINE schema
SSH_UNITS = "m"          # <- exact units from the BASELINE schema
TIME_UNITS = "days since 2012-10-01"  # <- exact encoding from the BASELINE schema


def write_map(
    times: np.ndarray, lats: np.ndarray, lons: np.ndarray,
    ssh: np.ndarray, dest: Path,
) -> Path:
    """Write a (time, lat, lon) SSH map to ``dest`` in the challenge schema.

    Args:
        times: 1-D time coordinate (datetime64 or encoded per the schema).
        lats: 1-D latitude coordinate.
        lons: 1-D longitude coordinate.
        ssh: ``(time, lat, lon)`` SSH field.
        dest: Output NetCDF path.

    Returns:
        ``dest``.
    """
    ds = xr.Dataset(
        {SSH_VAR: (("time", "lat", "lon"), ssh, {"units": SSH_UNITS})},
        coords={"time": ("time", times), "lat": ("lat", lats), "lon": ("lon", lons)},
    )
    enc = {"time": {"units": TIME_UNITS}}
    dest.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(dest, encoding=enc)
    return dest
```

- [ ] **Step 5: Run schema-match test, confirm pass.** Run: `pixi run test tests/validation/test_output_adapter.py -v` → PASS. `pixi run typecheck && pixi run lint` → clean.

- [ ] **Step 6: Round-trip through their reader** (external): write a zero map at full grid + time axis, pass to `their_eval.score`, confirm it ingests unchanged and returns three floats (values irrelevant here — the point is no schema rejection).

- [ ] **Step 7: Commit.**

```bash
git add src/sverdrup/validation/output_adapter.py tests/validation/test_output_adapter.py tests/validation/fixtures/
git commit -m "feat(validation): output adapter — OI map -> BASELINE NetCDF schema (field-for-field)"
```

**HOLD (gate 2):** present green adapters + the schema-match evidence (the field-for-field diff vs the shipped BASELINE). Owner confirms before the full run.

---

## Task 6: Run driver — 2017 single-tile OI → daily maps → NetCDF

**Goal:** Drive `OptimalInterpolation.solve` over 2017 on the single tile using a sliding temporal window of obs, assemble the daily map stack, and write it through the output adapter.

**Files:**
- Create: `src/sverdrup/validation/run.py`
- Create: `tests/validation/test_run.py`

**Acceptance Criteria:**
- [ ] `run_year(mapping_obs, params, grid, temporal_half_window_days, dest)` produces a NetCDF with one map per output day over the 2017 eval period.
- [ ] Each output day's solve sees only obs within `±temporal_half_window_days` of that day (sliding window), and the spin-up obs feed early-2017 days.
- [ ] On the committed fixture (a few days), `run_year` completes and the output passes the Task-5 schema-match.

**Verify:** `pixi run test tests/validation/test_run.py -v` → produces a multi-day map on the fixture, schema-valid, finite where obs support it.

**Steps:**

- [ ] **Step 1: Write the failing test** (small fixture, 3 output days).

```python
# tests/validation/test_run.py
import numpy as np
import xarray as xr
from sverdrup.validation.run import run_year


def test_run_year_produces_daily_maps(tmp_path, mapping_fixture_obs, baseline_provider, small_grid):
    """run_year emits one schema-valid map per output day from windowed obs.

    Catches a broken temporal-window assembly (empty maps / wrong day count).
    """
    dest = tmp_path / "ours.nc"
    out = run_year(
        mapping_obs=mapping_fixture_obs, params=baseline_provider, grid=small_grid,
        temporal_half_window_days=10.0, output_days=[0.0, 1.0, 2.0], dest=dest,
    )
    ds = xr.open_dataset(out)
    assert ds.sizes["time"] == 3
    assert np.isfinite(ds[list(ds.data_vars)[0]].values).any()
```

- [ ] **Step 2: Run test, confirm fail.** Run: `pixi run test tests/validation/test_run.py -v` → FAIL.

- [ ] **Step 3: Implement `run.py`** (per output day: subset obs by the temporal window, build a per-day `ObsWindow`, solve, stack `dist.mean`).

```python
# src/sverdrup/validation/run.py
"""Drive 2017 single-tile OI over a sliding temporal window -> daily map NetCDF."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from sverdrup.core.grid import GridSpec
from sverdrup.core.observations import DiagonalErrorModel, ObsWindow
from sverdrup.core.parameters import ParameterProvider
from sverdrup.methods.oi import OptimalInterpolation
from sverdrup.validation.output_adapter import write_map


def _window(obs: ObsWindow, day: float, half: float) -> ObsWindow:
    """Subset ``obs`` to those within ``±half`` days of ``day``."""
    c = obs.coords()
    keep = np.abs(c[:, 2] - day) <= half
    var = np.asarray(obs.error_model.as_matrix(len(obs)).diagonal())[keep]
    return ObsWindow.from_arrays(
        c[keep, 0], c[keep, 1], c[keep, 2], obs.values()[keep],
        DiagonalErrorModel(var),
        mission=None if obs.mission is None else np.asarray(obs.mission)[keep],
    )


def run_year(
    mapping_obs: ObsWindow, params: ParameterProvider, grid: GridSpec,
    temporal_half_window_days: float, output_days: list[float], dest: Path,
) -> Path:
    """Run OI for each output day and write the stacked daily maps.

    Args:
        mapping_obs: All five-mission obs (spin-up included).
        params: The baseline OI parameter provider.
        grid: The output grid over the box.
        temporal_half_window_days: Half-width of the obs influence window.
        output_days: Output day numbers (0 == 2017-01-01).
        dest: Output NetCDF path.

    Returns:
        ``dest``.
    """
    oi = OptimalInterpolation()
    maps = []
    for day in output_days:
        win = _window(mapping_obs, day, temporal_half_window_days)
        dist = oi.solve(win, grid, params, time_days=day)
        maps.append(np.asarray(dist.mean))
    ssh = np.stack(maps, axis=0)
    lon, lat = grid._lonlat_nodes()
    times = np.array(output_days, dtype="timedelta64[D]") + np.datetime64("2017-01-01")
    return write_map(times, np.unique(lat), np.unique(lon), ssh, dest)
```

(If `dist.mean` shape is `(ny, nx)` it stacks directly; confirm against `GaussianPredictiveDistribution.mean` and reshape if the grid is flattened. The full-year driver iterates all 2017 days; `output_days` is the seam the test uses with 3 days.)

- [ ] **Step 4: Run test, confirm pass.** Run: `pixi run test tests/validation/test_run.py -v` → PASS. `pixi run typecheck && pixi run lint` → clean.

- [ ] **Step 5: Commit.**

```bash
git add src/sverdrup/validation/run.py tests/validation/test_run.py
git commit -m "feat(validation): run driver — 2017 single-tile OI sliding-window -> daily map NetCDF"
```

---

## Task 7: Dual evaluation + result report (USER-GATE — the result)

**Goal:** Run the full 2017 OI, score our map and the shipped BASELINE map with THEIR eval (the three-number sanity anchor re-confirmed), run our `area_weighted_rmse` cross-check on the same map, and produce the result table + decomposed read.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- Create: `src/sverdrup/validation/report.py`
- Create: `tests/validation/test_report.py`
- Create: `docs/validation/RESULT.md`

**Acceptance Criteria:**
- [ ] Their eval is run on BOTH our full-year map and the shipped BASELINE map; the BASELINE-from-their-map numbers reproduce the published (µ, σ, λx) — the sanity anchor — with λx explicitly reported and flagged as the sensitive number.
- [ ] Our `area_weighted_rmse` is run on the same map; the delta vs their µ(RMSE) is reported.
- [ ] `RESULT.md` contains the result table (ours ∥ BASELINE 0.85/0.09/140 ∥ DUACS 0.88/0.07/152), the reproduced-published-BASELINE sanity number, the parallel-eval delta, and the decomposed read (PASS / informative-miss (i)/(ii)/(iii) per design §6).
- [ ] No tolerance is loosened to manufacture a pass; the PASS tolerance is stated and applied as recorded.

**Verify:** `pixi run test tests/validation/test_report.py -v` (unit: table assembly + decomposed-read classification logic, offline) AND the captured full-run `RESULT.md` with all numbers.

**Steps:**

- [ ] **Step 1: Write the failing unit test** for the report assembly + the decomposed-read classifier (offline — feeds synthetic numbers through the classifier).

```python
# tests/validation/test_report.py
from sverdrup.validation.report import classify_result, ResultRow


def test_classifier_flags_eval_layer_disagreement():
    """When our eval disagrees with theirs on the SAME map -> case (iii).

    Catches a classifier that would mislabel an eval-layer bug as a pass/miss.
    """
    verdict = classify_result(
        ours=ResultRow(mu=0.86, sigma=0.09, lambda_x=141),
        baseline_published=ResultRow(mu=0.85, sigma=0.09, lambda_x=140),
        baseline_reproduced=ResultRow(mu=0.85, sigma=0.09, lambda_x=140),
        our_eval_mu_same_map=0.95,  # disagrees with their 0.86 on our map
        tol_mu=0.03,
    )
    assert verdict.code == "iii"
```

- [ ] **Step 2: Run test, confirm fail.** Run: `pixi run test tests/validation/test_report.py -v` → FAIL.

- [ ] **Step 3: Implement `report.py`** (the `ResultRow` dataclass, `classify_result` implementing design §6's decomposition, and a `render_table` writing `RESULT.md`).

```python
# src/sverdrup/validation/report.py
"""Assemble the dual-eval result table + the decomposed read (design section 6)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResultRow:
    """One (mu, sigma, lambda_x) score triple."""

    mu: float
    sigma: float
    lambda_x: float


@dataclass(frozen=True)
class Verdict:
    """Decomposed read: PASS or informative-miss (i)/(ii)/(iii)."""

    code: str       # "PASS" | "i" | "ii" | "iii"
    explanation: str


def classify_result(
    ours: ResultRow, baseline_published: ResultRow, baseline_reproduced: ResultRow,
    our_eval_mu_same_map: float, tol_mu: float,
) -> Verdict:
    """Classify the run per design section 6 (decompose, do not pass/fail).

    Args:
        ours: Their eval on OUR map.
        baseline_published: The leaderboard row (0.85/0.09/140).
        baseline_reproduced: Their eval on THEIR shipped BASELINE map.
        our_eval_mu_same_map: Our area-weighted RMSE on OUR map.
        tol_mu: The agreed mu tolerance (set after seeing the spread).

    Returns:
        A ``Verdict`` with the decomposed read.
    """
    if abs(baseline_reproduced.mu - baseline_published.mu) > tol_mu:
        return Verdict("ii", "Cannot reproduce published BASELINE from their own map "
                             "-> driving their eval wrong or version skew (harness bug).")
    if abs(our_eval_mu_same_map - ours.mu) > tol_mu:
        return Verdict("iii", "Our eval disagrees with theirs on the SAME map "
                              "-> our eval layer differs from canonical.")
    if abs(ours.mu - baseline_published.mu) > tol_mu:
        return Verdict("i", "We reproduce their BASELINE but our OI map scores "
                            "differently -> parameter/grid/masking/reference-frame mismatch.")
    return Verdict("PASS", "Reproduces the BASELINE row; sanity anchor + parallel eval agree.")
```

- [ ] **Step 4: Run test, confirm pass.** Run: `pixi run test tests/validation/test_report.py -v` → PASS. `pixi run typecheck && pixi run lint` → clean.

- [ ] **Step 5: Full run (captured).** Run the full-year OI (`run_year` over all 2017 days) → our map. Then:

```bash
pixi run python -m sverdrup.validation.report  # orchestrates: their_eval on {ours, baseline}, our area_weighted_rmse, write RESULT.md
```

Confirm the sanity anchor reproduces all three published numbers from the shipped BASELINE map (λx explicitly), record our three numbers, the parallel-eval delta, and the decomposed read.

- [ ] **Step 6: Commit.**

```bash
git add src/sverdrup/validation/report.py tests/validation/test_report.py docs/validation/RESULT.md
git commit -m "feat(validation): dual-eval report + decomposed read (the BASELINE result)"
```

**HOLD (gate 3):** present `RESULT.md` — the table + the decomposed read. Owner decides disposition. Then update `PROGRESS.md` with the outcome.

---

## Self-Review

**Spec coverage:** every design section maps to a task — §0/§4 de-risk spike → Task 1; §1 modules → Tasks 0,2,4,5,6,7; §3 version pin → Task 1; §5 reference frame → Task 3 (+ applied in Task 4); §6 decomposed read → Task 7; §7 tests → distributed across tasks; §8 four HOLDs → Tasks {1,2}/3/5/7 user-gates. Scope-spec "single tile / their eval ground truth / params from notebook / PASS tol deferred" all honoured.

**Placeholder scan:** the only non-literal values are external-discovery outputs (exact scalar params in `params.py`, exact NetCDF var/coord names in `input_adapter.py`/`output_adapter.py`, their function names in `their_eval.py`). These are explicitly recon-bound and the tasks that produce them (1,3) are gated; the *structure* and the *acceptance numbers* (0.85/0.09/140) are concrete. No lazy TBDs.

**Type consistency:** `ObsWindow.from_arrays(lon,lat,time,values,error_model,mission)`, `DiagonalErrorModel(variance)`, `OptimalInterpolation().solve(obs,grid,params,time_days)`, `params.resolve("variance"|"length_scale"|"time_scale", grid)`, `area_weighted_rmse(error_field, grid)`, `GridSpec.lonlat(lon=,lat=)` — all match the read source. `their_eval.score(map_path, track_path) -> (mu, sigma, lambda_x)` used consistently in Tasks 1, 5, 7. `baseline_config() -> (provider, grid, half_window)` and `OBS_NOISE_VARIANCE` consistent between Tasks 3 and 4.
