# sverdrup Rename + PyPI Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers-extended-cc:subagent-driven-development (recommended) or superpowers-extended-cc:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the package `regatta` → `sverdrup` and make it a tag-driven PyPI release (hatchling + hatch-vcs, Apache-2.0, core+extras deps, Trusted-Publishing CI), then land it as the public repo `killett/sverdrup`.

**Architecture:** Mechanical repo-wide rename first, then layer PyPI packaging onto `pyproject.toml` (build backend, dynamic version from git tag, metadata, dependency split mirroring the hexagonal `core` vs `adapters` boundary). CI publishes via GitHub Actions OIDC Trusted Publishing on tag push. The `gh` token lacks the `workflow` scope, so the workflow file ships as a committed reference copy the user installs on GitHub (Option B).

**Tech Stack:** hatchling, hatch-vcs, build, twine, GitHub Actions (`pypa/gh-action-pypi-publish`), pixi, gh CLI.

**User decisions (already made):**
- Rename to `sverdrup` (final; was `regatta` → `halosphere` → `sverdrup`). PyPI name verified free (HTTP 404).
- Build backend hatchling + hatch-vcs; version is **dynamic from the git tag**.
- License **Apache-2.0**.
- Dependencies: required **core** (numpy/scipy/pyproj) + optional **extras** (`dask`, `io`, `all`).
- Publish via **GitHub Actions Trusted Publishing (OIDC)** on tag push.
- Repo: public **`killett/sverdrup`**.
- **Option B** for the workflow file: assistant cannot push `.github/workflows/*` (token has no `workflow` scope); ship a committed reference copy, user installs it on GitHub.

Design doc: `docs/superpowers/specs/2026-06-21-sverdrup-pypi-release-design.md`.

---

## Shared facts (canonical — every task matches these)

- Import name **and** distribution name: `sverdrup`. Entry point: `python -m sverdrup`.
- Package path: `src/sverdrup/` (src layout; `PYTHONPATH=src` already set in pixi activation).
- GitHub: `https://github.com/killett/sverdrup` (public).
- Runtime import → dependency mapping (verified against `src/`):
  - core/methods/distributions/derived/eval → `numpy`, `scipy`, `pyproj` (required).
  - `adapters/executor_dask.py` → `dask[distributed]` (`dask` extra).
  - `adapters/storage_fsspec.py`, `adapters/odc/*` → `xarray`, `fsspec`, `netcdf4`, `requests`, `tenacity` (`io` extra).
  - `application/pipeline.py` eagerly imports the executor + sink → the end-to-end pipeline needs `sverdrup[all]`.

---

### Task 1: Rename package `regatta` → `sverdrup`

**Goal:** Move the package directory and rewrite every `regatta` reference in code/config to `sverdrup`, leaving historical task content in `docs/` untouched.

**Files:**
- Move: `src/regatta/` → `src/sverdrup/`
- Modify: all `*.py` under `src/` and `tests/` importing `regatta`
- Modify: `src/sverdrup/__main__.py` (banner text)
- Modify: `pixi.toml` (`[workspace] name`), `pyproject.toml` (`[tool.coverage.run] source`)
- Modify: `tests/integration/config_osse.json`, `tests/oracle/conftest.py` (`/tmp/regatta_*.zarr` → `/tmp/sverdrup_*.zarr`)
- Modify: `README.md`, `CLAUDE.md` (`# Project: regatta` header + usage), `PROGRESS.md` (usage refs only)

**Acceptance Criteria:**
- [ ] `rg -ni 'regatta' --glob '!docs/**' --glob '!*.lock' .` returns nothing.
- [ ] `pixi run test` → all tests pass (same count as before: 70 passed, 1 skipped).
- [ ] `pixi run python -m sverdrup` prints the banner and exits 0.

**Verify:** `rg -ni 'regatta' --glob '!docs/**' --glob '!*.lock' . ; pixi run test 2>&1 | tail -1`

**Steps:**

- [ ] **Step 1: Move the package directory**

```bash
git mv src/regatta src/sverdrup
```

- [ ] **Step 2: Rewrite `regatta` references in code/config**

```bash
# word-boundary rename in python sources (imports, module paths)
rg -l '\bregatta\b' src tests --glob '*.py' | xargs -r sed -i 's/\bregatta\b/sverdrup/g'
# cosmetic output-path strings (regatta_osse / regatta_oracle -> sverdrup_*)
rg -l 'regatta_' tests --glob '*.json' --glob '*.py' | xargs -r sed -i 's/regatta_/sverdrup_/g'
# pixi workspace name + pyproject coverage source
sed -i 's/^name = "regatta"/name = "sverdrup"/' pixi.toml
sed -i 's#source = \["src"\]#source = ["src"]#' pyproject.toml   # unchanged; coverage uses src path, not the name
```

- [ ] **Step 3: Fix the banner and remaining prose refs by hand**

Edit `src/sverdrup/__main__.py`: change the banner string `"regatta phase-1 framework …"` → `"sverdrup phase-1 framework …"`.
Edit `README.md`, `CLAUDE.md` (`# Project: regatta` → `# Project: sverdrup`, and any `python -m regatta` / `regatta.` usage examples), and `PROGRESS.md` usage references. Do NOT edit historical task text in `docs/superpowers/plans/2026-06-21-regatta-phase1*` or the phase-1 design doc.

- [ ] **Step 4: Verify no stray references and the suite is green**

```bash
rg -ni 'regatta' --glob '!docs/**' --glob '!*.lock' .   # expect: no output
pixi run python -m sverdrup                              # expect: banner, exit 0
pixi run test 2>&1 | tail -1                             # expect: 70 passed, 1 skipped
```
Expected: no stray `regatta`, banner prints, suite green.

- [ ] **Step 5: Run pre-commit and commit**

```bash
pixi run pre-commit run --all-files | grep -E 'ruff|mypy' || true
git add -A
git commit -m "refactor: rename package regatta -> sverdrup"
```

---

### Task 2: Build backend + dynamic version (hatchling + hatch-vcs)

**Goal:** Add a real `[build-system]`, set the distribution name to `sverdrup`, and make the version derive from the git tag via hatch-vcs.

**Files:**
- Modify: `pyproject.toml` (`[project]`, add `[build-system]`, `[tool.hatch.*]`)
- Modify: `.gitignore` (ignore the generated `src/sverdrup/_version.py`)

**Acceptance Criteria:**
- [ ] `pixi run python -m build` produces `dist/sverdrup-<version>-py3-none-any.whl` and a matching sdist.
- [ ] The built version is non-empty (hatch-vcs derives it from git; no tag yet → a `0.0.0`/dev version is acceptable).
- [ ] `pixi run twine check dist/*` → PASSED.
- [ ] `src/sverdrup/_version.py` is git-ignored.

**Verify:** `pixi run python -m build 2>&1 | tail -3 ; pixi run twine check dist/*`

**Steps:**

- [ ] **Step 1: Replace the `[project]` head and add the build system**

In `pyproject.toml`, replace the top `[project]` block's `version = "0.1.0" …` line and add the build backend. The block becomes:

```toml
[project]
name = "sverdrup"
dynamic = ["version"]
requires-python = ">=3.12,<3.14"
dependencies = []   # populated in Task 4

[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/sverdrup/_version.py"

[tool.hatch.build.targets.wheel]
packages = ["src/sverdrup"]
```

(Delete the old `version = "0.1.0"  # …uv PEP 621…` line; `dynamic` + a real `[build-system]` satisfies PEP 621.)

- [ ] **Step 2: Git-ignore the generated version file**

Append to `.gitignore`:

```
src/sverdrup/_version.py
dist/
```

- [ ] **Step 3: Build and check**

```bash
rm -rf dist
pixi run python -m build 2>&1 | tail -3
ls dist/
pixi run twine check dist/*
```
Expected: a `sverdrup-<version>` wheel + sdist; `twine check` → PASSED.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .gitignore
git commit -m "build: add hatchling + hatch-vcs tag-driven versioning"
```

---

### Task 3: Metadata + LICENSE + py.typed

**Goal:** Add complete PyPI metadata, the Apache-2.0 `LICENSE`, and the PEP 561 `py.typed` marker so the wheel ships type hints.

**Files:**
- Modify: `pyproject.toml` (`[project]` metadata + `[project.urls]`)
- Create: `LICENSE` (Apache-2.0 full text)
- Create: `src/sverdrup/py.typed` (empty)

**Acceptance Criteria:**
- [ ] `pixi run twine check dist/*` → PASSED (valid metadata) after rebuild.
- [ ] The built wheel contains `sverdrup/py.typed` and the sdist contains `LICENSE`.
- [ ] License is declared as `Apache-2.0` with the matching OSI classifier.

**Verify:** `pixi run python -m build 2>&1 | tail -2 ; unzip -l dist/*.whl | grep -E 'py.typed' ; pixi run twine check dist/*`

**Steps:**

- [ ] **Step 1: Fetch the canonical Apache-2.0 text**

```bash
curl -sSL https://www.apache.org/licenses/LICENSE-2.0.txt -o LICENSE
head -2 LICENSE   # expect the Apache License header
```

- [ ] **Step 2: Add the type marker**

```bash
touch src/sverdrup/py.typed
```

- [ ] **Step 3: Fill in `[project]` metadata**

In `pyproject.toml`, expand `[project]` (keep `name`, `dynamic`, `requires-python` from Task 2) with:

```toml
description = "Regional sea-surface-height-anomaly reconstruction with first-class predictive uncertainty"
readme = "README.md"
license = "Apache-2.0"
authors = [{ name = "Emmy Killett", email = "emmykillett@gmail.com" }]
keywords = ["oceanography", "sea surface height", "gaussian process", "optimal interpolation", "uncertainty quantification"]
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

- [ ] **Step 4: Rebuild and verify packaging artifacts**

```bash
rm -rf dist
pixi run python -m build 2>&1 | tail -2
unzip -l dist/*.whl | grep -E 'py.typed'        # expect sverdrup/py.typed
tar tzf dist/*.tar.gz | grep -E '/LICENSE$'     # expect LICENSE in sdist
pixi run twine check dist/*                      # expect PASSED
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml LICENSE src/sverdrup/py.typed
git commit -m "build: add Apache-2.0 license, PyPI metadata, and py.typed marker"
```

---

### Task 4: Dependencies — core required + optional extras

**Goal:** Declare runtime dependencies for pip users: a minimal required core plus `dask`/`io`/`all` extras mirroring the hexagonal boundary.

**Files:**
- Modify: `pyproject.toml` (`[project] dependencies`, `[project.optional-dependencies]`)

**Acceptance Criteria:**
- [ ] Built wheel METADATA lists `numpy`, `scipy`, `pyproj` as `Requires-Dist` (unconditional).
- [ ] METADATA declares extras `dask`, `io`, `all` (`Provides-Extra`) with the mapped packages.
- [ ] `pixi run twine check dist/*` → PASSED after rebuild.

**Verify:** `pixi run python -m build 2>&1 | tail -2 ; unzip -p dist/*.whl '*/METADATA' | grep -E 'Requires-Dist|Provides-Extra'`

**Steps:**

- [ ] **Step 1: Populate dependencies**

In `pyproject.toml`, set the `dependencies` list (replacing the `[]` placeholder from Task 2) and add the extras table:

```toml
dependencies = [
    "numpy>=1.26",
    "scipy>=1.11",
    "pyproj>=3.6",
]

[project.optional-dependencies]
dask = ["dask[distributed]>=2024.1"]
io = ["xarray>=2024.1", "fsspec>=2024.1", "netcdf4>=1.6", "requests>=2.31", "tenacity>=8.2"]
all = ["sverdrup[dask,io]"]
```

- [ ] **Step 2: Rebuild and inspect metadata**

```bash
rm -rf dist
pixi run python -m build 2>&1 | tail -2
unzip -p dist/*.whl '*/METADATA' | grep -E 'Requires-Dist|Provides-Extra'
pixi run twine check dist/*
```
Expected: `Requires-Dist: numpy>=1.26` (and scipy, pyproj); `Provides-Extra: dask|io|all`; PASSED.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "build: declare core runtime deps + dask/io/all extras"
```

---

### Task 5: Release workflow (committed reference copy — Option B)

**Goal:** Author the Trusted-Publishing GitHub Actions workflow as a committed, pushable reference copy (not under `.github/workflows/`, which the `gh` token cannot push), for the user to install on GitHub.

**Files:**
- Create: `docs/superpowers/ci/release.yml`
- Modify: `README.md` (a short "Releasing" section pointing at it)

**Acceptance Criteria:**
- [ ] `docs/superpowers/ci/release.yml` is valid YAML.
- [ ] It triggers on `push` tags `v*`, builds with `fetch-depth: 0`, runs `twine check`, and publishes via `pypa/gh-action-pypi-publish` with `permissions: id-token: write` and `environment: pypi`.
- [ ] README documents that the user must copy it to `.github/workflows/release.yml` on GitHub (Option B).

**Verify:** `pixi run yq '.on.push.tags' docs/superpowers/ci/release.yml` (valid parse) and `rg -n 'id-token|gh-action-pypi-publish|fetch-depth' docs/superpowers/ci/release.yml`

**Steps:**

- [ ] **Step 1: Write the workflow**

Create `docs/superpowers/ci/release.yml`:

```yaml
name: release

on:
  push:
    tags: ["v*"]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # hatch-vcs needs full history + tags
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Build
        run: |
          python -m pip install --upgrade build twine
          python -m build
          python -m twine check dist/*
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write   # OIDC for Trusted Publishing
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
```

- [ ] **Step 2: Document the Option-B install step in README**

Add a `## Releasing` section to `README.md`:

```markdown
## Releasing

Publishing to PyPI is automated via GitHub Actions Trusted Publishing on tag push. The
workflow lives at `docs/superpowers/ci/release.yml`; copy it to `.github/workflows/release.yml`
in the GitHub repo (a one-time step — the local tooling token cannot push workflow files).
Configure the PyPI trusted publisher (project `sverdrup`, owner `killett`, repo `sverdrup`,
workflow `release.yml`, environment `pypi`), then `git tag -a vX.Y.Z -m "..." && git push origin vX.Y.Z`.
```

- [ ] **Step 3: Validate and commit**

```bash
pixi run yq '.' docs/superpowers/ci/release.yml > /dev/null && echo "yaml ok"
rg -n 'id-token|gh-action-pypi-publish|fetch-depth' docs/superpowers/ci/release.yml
git add docs/superpowers/ci/release.yml README.md
git commit -m "ci: add Trusted-Publishing release workflow (reference copy) + docs"
```

---

### Task 6: Build + clean-venv install smoke (USER GATE)

**Goal:** Prove the built `sverdrup` wheel installs from scratch in an isolated environment, imports, exposes the version, ships `py.typed`, and that `sverdrup[all]` enables the end-to-end pipeline.

> **USER-ORDERED GATE — NON-SKIPPABLE.** This task was requested by the user in the current conversation. It MUST NOT be closed by walking around it, by declaring it "verified inline", or by substituting a cheaper check. Close only after every item in `acceptanceCriteria` has been re-validated independently, with output captured.

**Files:**
- None (verification only; operates on `dist/` from Tasks 2–4)

**Acceptance Criteria:**
- [ ] `python -m build` produces a wheel + sdist and `twine check dist/*` prints `PASSED`.
- [ ] In a fresh venv, `pip install dist/*.whl` succeeds and `python -c "import sverdrup; from sverdrup.core.grid import GridSpec"` prints `ok`.
- [ ] `importlib.metadata.version("sverdrup")` is non-empty in that venv.
- [ ] `unzip -l dist/*.whl | grep py.typed` shows `sverdrup/py.typed`.
- [ ] `pip install "<wheel>[all]"` then `python -m sverdrup` exits 0 and `from sverdrup.application.pipeline import run_pipeline` imports.

**Verify:** the full block in Step 1 (captured output for each criterion).

**Steps:**

- [ ] **Step 1: Build, then smoke-test in a throwaway venv**

```bash
set -e
rm -rf dist /tmp/sv
pixi run python -m build 2>&1 | tail -2
pixi run twine check dist/*                       # expect: PASSED
unzip -l dist/*.whl | grep py.typed               # expect: sverdrup/py.typed

python -m venv /tmp/sv
/tmp/sv/bin/pip install -q --upgrade pip
WHL=$(ls dist/*.whl)
/tmp/sv/bin/pip install -q "$WHL"
/tmp/sv/bin/python -c "import sverdrup; from sverdrup.core.grid import GridSpec; print('ok')"
/tmp/sv/bin/python -c "import importlib.metadata as m; print('version', m.version('sverdrup'))"

/tmp/sv/bin/pip install -q "${WHL}[all]"
/tmp/sv/bin/python -m sverdrup                    # expect: banner, exit 0
/tmp/sv/bin/python -c "from sverdrup.application.pipeline import run_pipeline; print('pipeline import ok')"
```
Expected: `PASSED`, `sverdrup/py.typed`, `ok`, a non-empty `version …`, banner, `pipeline import ok`.

- [ ] **Step 2: Record evidence**

Capture the printed output for each acceptance criterion in the task close. No commit (verification only); if the build wrote `dist/` it stays git-ignored.

---

### Task 7: Create + push the public GitHub repo `killett/sverdrup`

**Goal:** Create the public repo and push `main` (code + reference workflow under `docs/`), with no `.github/workflows/` file in the tree so the `repo`-scoped token's push is accepted.

**Files:**
- None in the working tree (git/remote operations); uses `gh` authed as `killett`.

**Acceptance Criteria:**
- [ ] `gh repo view killett/sverdrup --json visibility,name` shows `name=sverdrup`, `visibility=PUBLIC`.
- [ ] `git ls-remote origin refs/heads/main` resolves (main pushed).
- [ ] No `.github/workflows/` path exists in the repo (Option B — workflow ships under `docs/superpowers/ci/`).

**Verify:** `gh repo view killett/sverdrup --json visibility,name ; git ls-remote origin refs/heads/main`

**Steps:**

- [ ] **Step 1: Confirm a clean, green tree before publishing**

```bash
git status --short          # expect: clean
test -d .github/workflows && echo "WORKFLOW DIR PRESENT - stop" || echo "no workflow dir (good)"
```
If `.github/workflows/` exists, stop and resolve (it would be rejected by the token).

- [ ] **Step 2: Create the public repo and push**

```bash
gh repo create killett/sverdrup --public --description "Regional SSHA reconstruction with first-class predictive uncertainty"
git remote add origin https://github.com/killett/sverdrup.git
git push -u origin main
```

- [ ] **Step 3: Verify the remote**

```bash
gh repo view killett/sverdrup --json visibility,name
git ls-remote origin refs/heads/main
```
Expected: `PUBLIC`, `sverdrup`; a commit hash for `main`.

- [ ] **Step 4: Hand off the remaining one-time user steps**

Report to the user (no automation possible):
1. Copy `docs/superpowers/ci/release.yml` → `.github/workflows/release.yml` on GitHub (Add file → Create file).
2. Configure the PyPI Trusted Publisher: project `sverdrup`, owner `killett`, repo `sverdrup`, workflow `release.yml`, environment `pypi`.
3. Cut the release: `git tag -a v0.1.0 -m "sverdrup 0.1.0" && git push origin v0.1.0`.

---

## Self-review

**Spec coverage** — §1 rename → Task 1; §2 build backend + version → Task 2; §3 metadata/LICENSE/py.typed → Task 3; §4 deps + extras → Task 4; §5 workflow (Option B) → Task 5; §6 repo create+push → Task 7; §9 verification → Task 6. §7 (PyPI trusted publisher) + §8 (cut the tag) are user-side one-time steps, handed off in Task 7 Step 4 (cannot be automated). No spec section unmapped.

**Placeholder scan** — every step contains the actual command/code/config. No TBD/TODO.

**Type/name consistency** — `sverdrup` import+dist name, `src/sverdrup/`, `killett/sverdrup`, extras `dask`/`io`/`all`, workflow at `docs/superpowers/ci/release.yml`, environment `pypi` — consistent across Tasks 1–7 and the README/workflow.

**Deviation from spec §5/§6 (recorded):** the workflow ships at `docs/superpowers/ci/release.yml` (committed, pushable) rather than as an untracked `.github/workflows/release.yml`. Reason: avoids the token's `workflow`-scope push rejection cleanly while keeping the file version-controlled; the user installs it on GitHub. Same Option-B outcome.
