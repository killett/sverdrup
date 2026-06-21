# Design: rename to `halosphere` + PyPI release framework

**Status:** approved (brainstorm, 2026-06-21)

**Goal.** Make the project publishable to PyPI as a tag-driven release, renamed from
`regatta` to **`halosphere`**, with version derived from the git tag, dependencies split
along the hexagonal boundary, and publishing automated from GitHub Actions via Trusted
Publishing (OIDC). Land the source as a public repo `killett/halosphere`.

## Decisions (settled)

- **Name:** distribution **and** import name = `halosphere` (verified free on PyPI by the
  user). `python -m halosphere` is the entry point.
- **Build backend:** `hatchling` + `hatch-vcs` (both already in `pixi.toml`).
- **Version source:** the **git tag** via hatch-vcs (`dynamic = ["version"]`). `v0.1.0` → `0.1.0`.
- **Dependencies:** minimal required **core** + optional **extras** mirroring `core` vs `adapters`.
- **License:** `Apache-2.0` (SPDX), ship a root `LICENSE` (no `NOTICE`).
- **Publish:** GitHub Actions Trusted Publishing (OIDC) on tag push — no stored tokens.
- **Repo:** public `killett/halosphere`, created + pushed with the available `gh` (`killett`,
  `repo` scope). The token lacks the `workflow` scope, so the user runs
  `gh auth refresh -s workflow` once before the workflow file is pushed.

## 1. Rename `regatta` → `halosphere`

Mechanical, repo-wide. Touch points:

- `src/regatta/` → `src/halosphere/` (directory move; `git mv`).
- Every `import regatta` / `from regatta...` in `src/` and `tests/` → `halosphere`.
- `src/halosphere/__main__.py` banner + the `python -m regatta` references.
- `pixi.toml` `[workspace] name`, `[activation.env] PYTHONPATH` stays `src`.
- `pyproject.toml` `[project] name`, `[tool.hatch.build.targets.wheel] packages`,
  `[tool.coverage.run] source`, mypy `mypy_path` (stays `src`).
- Cosmetic output-path strings `file:///tmp/regatta_*.zarr` in
  `tests/integration/config_osse.json`, `tests/oracle/conftest.py`, and any defaults →
  `halosphere_*` (string-only; not load-bearing, but rename for a clean public repo).
- `README.md`, `CLAUDE.md` (`# Project: regatta` header), `PROGRESS.md`, the design/plan docs
  under `docs/` (header/usage references only; do not rewrite historical task content).
- `python -m regatta tests/integration/config_osse.json` → `python -m halosphere ...`.

Acceptance: `rg -ni "regatta" --glob '!docs/**' --glob '!*.lock' .` returns nothing in
code/config; full test suite green; `python -m halosphere` runs.

## 2. Build backend + version

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "halosphere"
dynamic = ["version"]            # replaces the static version = "0.1.0"

[tool.hatch.version]
source = "vcs"
[tool.hatch.build.hooks.vcs]
version-file = "src/halosphere/_version.py"
[tool.hatch.build.targets.wheel]
packages = ["src/halosphere"]
```

`src/halosphere/_version.py` is build-generated and git-ignored. The pre-existing "keep a
static version for uv PEP 621 validation" comment is removed — `dynamic` + a real
`[build-system]` satisfies PEP 621.

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
Homepage = "https://github.com/killett/halosphere"
Repository = "https://github.com/killett/halosphere"
Issues = "https://github.com/killett/halosphere/issues"
```

- Root `LICENSE` — full Apache-2.0 text.
- `src/halosphere/py.typed` — empty PEP 561 marker (ship the type hints). hatchling includes
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
all  = ["halosphere[dask,io]"]
```

Boundary (verified against actual `src/` imports): core/methods/distributions/derived/eval
need only numpy+scipy+pyproj. The dask executor (`adapters/executor_dask.py`), the fsspec sink
(`adapters/storage_fsspec.py`), and the ODC data sources (`adapters/odc/*`) need the extras.
`application/pipeline.py` eagerly imports the executor + sink, so the **end-to-end pipeline
requires `halosphere[all]`** — documented in the README. Floors are conservative `>=`.

## 5. Release automation — `.github/workflows/release.yml`

Trusted Publishing (OIDC); no API token anywhere.

- `on: push: tags: ['v*']`.
- **build** job: `actions/checkout` with `fetch-depth: 0` (hatch-vcs needs tags/history),
  set up Python 3.12, `python -m build`, `twine check dist/*`, upload `dist/` artifact.
- **publish** job: `needs: build`, `environment: pypi`, `permissions: id-token: write`,
  download artifact, `pypa/gh-action-pypi-publish` (OIDC).
- Optional **PR check** job (build + `twine check`, no publish) for early breakage detection.

Pushing this file requires the `workflow` scope → the user runs `gh auth refresh -s workflow`
first (Recommended option chosen).

## 6. GitHub repo

- Create public `killett/halosphere` via `gh repo create killett/halosphere --public`.
- Push the renamed, packaged `main` (after the workflow-scope re-auth so CI lands too).
- This is the first time the project leaves the local machine — done only after the rename +
  packaging are committed and the suite is green.

## 7. PyPI Trusted Publisher (user, one-time, manual)

No API exists; the user configures it on pypi.org → *Publishing* → *Add a pending publisher*:

| Field | Value |
| --- | --- |
| PyPI Project Name | `halosphere` |
| Owner | `killett` |
| Repository name | `halosphere` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

## 8. Release procedure (cutting `v0.1.0`)

1. clean `main`, full suite green, repo pushed, Trusted Publisher configured.
2. `git tag -a v0.1.0 -m "..."` → `git push origin v0.1.0`.
3. CI builds + publishes via OIDC; verify on pypi.org.

## 9. Verification (before trusting the pipeline)

- `pixi run python -m build` → sdist + wheel in `dist/`.
- `pixi run twine check dist/*` → PASS.
- Fresh-venv smoke (outside pixi): `pip install dist/*.whl` then `python -c "import halosphere;
  from halosphere.core.grid import GridSpec"`; then `pip install 'halosphere[all] @ <wheel>'`,
  `python -m halosphere`, and a pipeline import.
- Confirm hatch-vcs resolves a version: build from a temporary local `v0.0.0` tag in a test, or
  assert `importlib.metadata.version("halosphere")` is non-empty after install.
- `py.typed` present in the built wheel (`unzip -l dist/*.whl | grep py.typed`).

## Out of scope / explicitly deferred

- Conda-forge packaging (pixi remains the dev environment; PyPI is the publish target).
- Optional-extras CI test matrix (a single full-deps CI suite for now).
- Signing/attestations beyond what `gh-action-pypi-publish` does by default.

## User-side prerequisites (cannot be automated here)

1. `gh auth refresh -s workflow` (enables pushing `release.yml`).
2. Configure the PyPI Trusted Publisher (table in §7).
3. Final `git push origin v0.1.0` to trigger the publish (or authorize me to push the tag).
