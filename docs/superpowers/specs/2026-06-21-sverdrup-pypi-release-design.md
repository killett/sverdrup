# Design: rename to `sverdrup` + PyPI release framework

**Status:** approved (brainstorm, 2026-06-21)

> **Name history:** `regatta` → `halosphere` → **`sverdrup`** (final). The file name keeps its
> original slug; the project name inside is `sverdrup`.

**Goal.** Make the project publishable to PyPI as a tag-driven release, renamed from
`regatta` to **`sverdrup`**, with version derived from the git tag, dependencies split
along the hexagonal boundary, and publishing automated from GitHub Actions via Trusted
Publishing (OIDC). Land the source as a public repo `killett/sverdrup`.

## Decisions (settled)

- **Name:** distribution **and** import name = `sverdrup`. `python -m sverdrup` is the entry point.
  PyPI availability **verified free** — `GET https://pypi.org/pypi/sverdrup/json` → HTTP 404
  (unregistered), checked 2026-06-21 from this environment (outbound HTTPS works).
- **Build backend:** `hatchling` + `hatch-vcs` (both already in `pixi.toml`).
- **Version source:** the **git tag** via hatch-vcs (`dynamic = ["version"]`). `v0.1.0` → `0.1.0`.
- **Dependencies:** minimal required **core** + optional **extras** mirroring `core` vs `adapters`.
- **License:** `Apache-2.0` (SPDX), ship a root `LICENSE` (no `NOTICE`).
- **Publish:** GitHub Actions Trusted Publishing (OIDC) on tag push — no stored tokens.
- **Repo:** public `killett/sverdrup`, created + pushed with the available `gh` (`killett`,
  `repo` scope).
- **Workflow file = Option B.** The `gh` token lacks the `workflow` scope and it cannot be
  upgraded (it is injected via `GH_TOKEN`). So: the assistant creates the repo and pushes **all
  code**; `.github/workflows/release.yml` is committed locally but **left for the user to add**
  on GitHub (web "Add file", or a later push from a workflow-scoped token). No `gh auth refresh`.

## 1. Rename `regatta` → `sverdrup`

Mechanical, repo-wide. Touch points:

- `src/regatta/` → `src/sverdrup/` (directory move; `git mv`).
- Every `import regatta` / `from regatta...` in `src/` and `tests/` → `sverdrup`.
- `src/sverdrup/__main__.py` banner + the `python -m regatta` references.
- `pixi.toml` `[workspace] name`; `[activation.env] PYTHONPATH` stays `src`.
- `pyproject.toml` `[project] name`, `[tool.hatch.build.targets.wheel] packages`,
  `[tool.coverage.run] source`; mypy `mypy_path` stays `src`.
- Cosmetic output-path strings `file:///tmp/regatta_*.zarr` in
  `tests/integration/config_osse.json`, `tests/oracle/conftest.py`, and any defaults →
  `sverdrup_*` (string-only; not load-bearing, but rename for a clean public repo).
- `README.md`, `CLAUDE.md` (`# Project: regatta` header), `PROGRESS.md`, the design/plan docs
  under `docs/` (header/usage references only; do not rewrite historical task content).
- `python -m regatta tests/integration/config_osse.json` → `python -m sverdrup ...`.

Acceptance: `rg -ni "regatta" --glob '!docs/**' --glob '!*.lock' .` returns nothing in
code/config; full test suite green; `python -m sverdrup` runs.

## 2. Build backend + version

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "sverdrup"
dynamic = ["version"]            # replaces the static version = "0.1.0"

[tool.hatch.version]
source = "vcs"
[tool.hatch.build.hooks.vcs]
version-file = "src/sverdrup/_version.py"
[tool.hatch.build.targets.wheel]
packages = ["src/sverdrup"]
```

`src/sverdrup/_version.py` is build-generated and git-ignored. The pre-existing "keep a static
version for uv PEP 621 validation" comment is removed — `dynamic` + a real `[build-system]`
satisfies PEP 621.

## 3. Metadata

```toml
[project]
description = "Regional sea-surface-height-anomaly reconstruction with first-class predictive uncertainty"
readme = "README.md"
requires-python = ">=3.12,<3.14"
license = "Apache-2.0"
authors = [{ name = "Emmy Killett", email = "emmykillett@gmail.com" }]
keywords = ["oceanography", "sea surface height", "gaussian process",
            "optimal interpolation", "uncertainty quantification"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Scientific/Engineering :: Atmospheric Science",
    "Typing :: Typed",
]

[project.urls]
Homepage = "https://github.com/killett/sverdrup"
Repository = "https://github.com/killett/sverdrup"
Issues = "https://github.com/killett/sverdrup/issues"
```

- Root `LICENSE` — full Apache-2.0 text.
- `src/sverdrup/py.typed` — empty PEP 561 marker (ship the type hints). hatchling includes
  package files under `packages` by default; confirm it lands in the wheel.

## 4. Dependencies — core required + extras

```toml
dependencies = [
    "numpy>=1.26",
    "scipy>=1.11",
    "pyproj>=3.6",
]

[project.optional-dependencies]
dask = ["dask[distributed]>=2024.1"]
io   = ["xarray>=2024.1", "fsspec>=2024.1", "netcdf4>=1.6",
        "requests>=2.31", "tenacity>=8.2"]
all  = ["sverdrup[dask,io]"]
```

Boundary (verified against actual `src/` imports): core/methods/distributions/derived/eval need
only numpy+scipy+pyproj. The dask executor (`adapters/executor_dask.py`), the fsspec sink
(`adapters/storage_fsspec.py`), and the ODC data sources (`adapters/odc/*`) need the extras.
`application/pipeline.py` eagerly imports the executor + sink, so the **end-to-end pipeline
requires `sverdrup[all]`** — documented in the README. Floors are conservative `>=`.

## 5. Release automation — `.github/workflows/release.yml` (committed locally; user pushes)

Trusted Publishing (OIDC); no API token anywhere.

- `on: push: tags: ['v*']`.
- **build** job: `actions/checkout` with `fetch-depth: 0` (hatch-vcs needs tags/history),
  set up Python 3.12, `python -m build`, `twine check dist/*`, upload `dist/` artifact.
- **publish** job: `needs: build`, `environment: pypi`, `permissions: id-token: write`,
  download artifact, `pypa/gh-action-pypi-publish` (OIDC).
- Optional **PR check** job (build + `twine check`, no publish).

**Option B handling:** this file is written and committed in the local repo, but it is **not
pushed** by the assistant (the `GH_TOKEN` lacks the `workflow` scope). The user adds it to GitHub
afterward — easiest via the repo's web "Add file → Upload/Create file", pasting the committed
contents — or by pushing from an environment whose token has `workflow`.

## 6. GitHub repo

- Create public `killett/sverdrup` via `gh repo create killett/sverdrup --public`.
- Push the renamed, packaged `main` **minus the workflow file** (Option B). Concretely: push
  `main`; if the push is rejected because it carries `.github/workflows/release.yml`, restructure
  so that file is not in the pushed history (e.g. keep it on a local-only path or stage it in a
  follow-up the user pushes). Simplest: commit everything **except** `release.yml` to the pushed
  history, and leave `release.yml` as an untracked/separate file the user adds on GitHub.
- This is the first time the project leaves the local machine — done only after the rename +
  packaging are committed and the suite is green.

## 7. PyPI Trusted Publisher (user, one-time, manual)

No API exists; the user configures it on pypi.org → *Publishing* → *Add a pending publisher*:

| Field | Value |
| --- | --- |
| PyPI Project Name | `sverdrup` |
| Owner | `killett` |
| Repository name | `sverdrup` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

## 8. Release procedure (cutting `v0.1.0`)

1. clean `main`, full suite green, repo pushed, `release.yml` on GitHub, Trusted Publisher
   configured (`sverdrup` already verified free on PyPI).
2. `git tag -a v0.1.0 -m "..."` → `git push origin v0.1.0`.
3. CI builds + publishes via OIDC; verify on pypi.org.

## 9. Verification (before trusting the pipeline)

- `pixi run python -m build` → sdist + wheel in `dist/`.
- `pixi run twine check dist/*` → PASS.
- Fresh-venv smoke (outside pixi): `pip install dist/*.whl` then `python -c "import sverdrup;
  from sverdrup.core.grid import GridSpec"`; then `pip install 'sverdrup[all] @ <wheel>'`,
  `python -m sverdrup`, and a pipeline import.
- Confirm hatch-vcs resolves a version after install:
  `python -c "import importlib.metadata as m; print(m.version('sverdrup'))"` is non-empty.
- `py.typed` present in the built wheel (`unzip -l dist/*.whl | grep py.typed`).

## Out of scope / explicitly deferred

- Conda-forge packaging (pixi remains the dev environment; PyPI is the publish target).
- Optional-extras CI test matrix (a single full-deps CI suite for now).
- Signing/attestations beyond what `gh-action-pypi-publish` does by default.

## User-side prerequisites (cannot be automated here)

1. Add `.github/workflows/release.yml` to the GitHub repo (Option B — assistant cannot push it
   with a non-`workflow`-scoped token).
2. Configure the PyPI Trusted Publisher (table in §7).
3. Final `git push origin v0.1.0` to trigger the publish (or authorize the assistant to push the tag).

(`sverdrup` PyPI-name availability is already verified — see Decisions.)
