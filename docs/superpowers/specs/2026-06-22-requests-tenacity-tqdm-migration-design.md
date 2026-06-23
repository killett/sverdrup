# Migrating a scaffolded project from `requests`/`tenacity`/`tqdm` to `httpx`/`stamina`/`rich.progress`

**Status:** Design approved 2026-06-22. Ready for implementation-plan handoff.

**Scope:** A project that was scaffolded by `claude-code-tools` while `[utils]` declared `requests/tenacity/tqdm/openjdk=25`. The `[utils]` group has since been updated to declare `httpx/pydantic/typer/rich/stamina/openjdk=25` (plus an apt-side `tmux` addition). This design covers the clean migration of that pre-existing project so that its pixi.toml, its installed env, and its source code line up with the new group composition.

This design does **not** cover changes inside `claude-code-tools` itself — those landed today in `groups.toml`. The container rebuild is a side effect of the user pulling latest `claude-code-tools` and re-launching.

---

## Background: how the launcher reacts to a changed group composition

Three mechanisms in `claude-code-tools` interact when a group's package set changes after a project has already been scaffolded against it:

1. **`hooks/check-pixi-drift.py`** — additive-only drift detector. Reads the project's `pixi.toml` and the union of `pixi_packages` + `pixi_pypi_packages` across the currently-selected groups, and emits one tab-separated line per *missing* declared dep. It does not detect packages in `pixi.toml` that are no longer declared by any selected group. Comparison is name-only (version specs in the project's pixi.toml are sovereign).

2. **`sandboxed-claude.sh --sync-pixi`** (`_sync_pixi_interactive`, `sandboxed-claude.sh:778-855`) — interactive companion that prompts per missing dep (1/2/3/4/a/s) and shells out to `pixi add` via a one-shot container exec. **Never calls `pixi remove`.** The design comment at `sandboxed-claude.sh:702` frames this as deliberate: user pixi.toml modifications are sovereign.

3. **`hooks/groups_chooser.py`** partial-match logic (`_PartialInfo`, `_tier_from_ratio`, lines 280-355, 395-454) — for each declared group, computes `present`/`missing`/`ratio`/`tier ∈ {full, high, mid, low, trace, none}`. Auto-checks groups in tier `full` or `high` (ratio ≥ 0.75) when CLI didn't specify `--groups`. Recorded `_installed` groups remain in seed regardless of tier. Does not surface stale-package drift to the user.

**Net implication.** When yesterday's project is launched against today's `groups.toml`:

- The chooser still pre-checks `[utils]` (recorded in `.sandbox_settings.json`).
- The "missing group deps" notice fires once listing the 5 new packages (`httpx`, `pydantic`, `typer`, `rich`, `stamina`). `--sync-pixi` will add them.
- `requests`, `tenacity`, `tqdm` sit in `pixi.toml` indefinitely. No automated detection, no automated removal. Manual `pixi remove` required.
- The chooser displays `[utils]` as tier `full` (●), **not** as a partial match. `_tier_for` (`groups_chooser.py:555-561`) short-circuits to `"full"` for any group in `_installed`, and `_installed` is sourced from `.sandbox_settings.json`'s `groups` field whenever the chooser is opened via the drift path (`sandboxed-claude.sh:2589-2598`) or `sandbox_review.py:993`. The pixi.toml partial-match data (1/6 ratio, only `openjdk` overlaps) is computed by `infer_groups.py` but never consulted for the row's tier glyph when the group is record-installed. Practical implication: the chooser TUI does NOT visually warn the user that `[utils]`'s composition has drifted. The mismatch is surfaced exclusively by the `_check_pixi_drift` notice on launch.

## Migration plan: four stages, two actors

| Stage | Actor | Action | Effect |
|---|---|---|---|
| **0. Container rebuild** | host: user | `sandboxed-claude.sh <project>` after pulling latest `claude-code-tools` | New image tag built with updated `[utils]` warm-cache. |
| **1. Sync new deps in** | host: user | `sandboxed-claude.sh --sync-pixi <project>`, press `a` at the prompt | `pixi add httpx pydantic typer rich stamina` runs in a one-shot container exec. `pixi.lock` regenerates. |
| **2. Remove stale deps** | container shell: user | `sandboxed-claude.sh --entry bash <project>` then `pixi remove requests tenacity tqdm` | Three stale entries leave `[dependencies]`. `pixi.lock` regenerates. Project env now matches new `[utils]` exactly. |
| **3. Source-code migration** | Claude Code, prompt-driven inside the project | Paste the prompt produced by the implementation-plan phase | Three commits on the current branch, one per phase, each verified by `pixi run pre-commit run --all-files && pixi run test`. |

**Ordering invariant:** Stage 2 must run before stage 3. With stale packages still importable, Claude Code can't use `ModuleNotFoundError` at verification time to catch missed call sites.

**Throttle note:** `_check_pixi_drift` (sandboxed-claude.sh:702-770) throttles the notice to once per `(groups.toml mtime × group set)` per project, keyed on `$_state_root/sync-checks/<project_hash>.last-sync-check`. `--sync-pixi` short-circuits the throttle. If the user has already launched into the project once after pulling and didn't see the notice (because it was throttled), `--sync-pixi` still works.

## Stage 3: source-code migration prompt structure

A single self-contained prompt block, pasted into Claude Code inside the target project. The prompt does the following.

**Pre-flight check** (fails closed):

```
pixi list | rg -q 'httpx|stamina' && ! pixi list | rg -q '^(requests|tenacity|tqdm)\s'
```

If false, the prompt instructs Claude to stop and surface "stage 2 not done" to the user.

**Three sequential commits**, each with this shape:

1. Inventory call sites via `rg` over the project for the old import + key symbols. If zero hits, skip phase with a one-line note.
2. Rewrite each file per the API translation tables (below).
3. Verify: `pixi run pre-commit run --all-files` then `pixi run test`.
4. Commit with Conventional Commits message in imperative mood:
   - `refactor: migrate HTTP client from requests to httpx`
   - `refactor: migrate retry layer from tenacity to stamina`
   - `refactor: migrate progress bars from tqdm to rich.progress`
5. Stop conditions: pre-commit hook fails → fix, re-stage, **new commit** (per CLAUDE.md "never amend"). Tests fail after a rename refactor → STOP, surface which test, which assertion, and which library-behavior delta caused it. Do not paper over with try/except.

**Final aggregate verification** (last commit only): `pixi run pre-commit run --all-files && pixi run test --cov`.

**Out of scope for the prompt:** does not edit pixi.toml, does not add new tests, does not amend/rebase, does not branch (commits on the current branch).

## API translation tables (substantive content for stage 3)

### Phase 1: `requests` → `httpx`

**Direct substitutions:**

| Before | After | Notes |
|---|---|---|
| `import requests` | `import httpx` | |
| `requests.get/post/put/patch/delete/head(url, ...)` | same on `httpx` | drop-in |
| `r.status_code`, `r.text`, `r.content`, `r.headers`, `r.json()`, `r.raise_for_status()` | unchanged | |
| `requests.Session()` | `httpx.Client()` | wrap usage in `with httpx.Client() as client:` |
| `session.<verb>(...)` | `client.<verb>(...)` | |

**Exception class map:**

| Before | After |
|---|---|
| `requests.exceptions.RequestException` | `httpx.RequestError` |
| `requests.exceptions.HTTPError` | `httpx.HTTPStatusError` |
| `requests.exceptions.ConnectionError` | `httpx.ConnectError` |
| `requests.exceptions.Timeout` | `httpx.TimeoutException` |
| `requests.exceptions.TooManyRedirects` | `httpx.TooManyRedirects` |

**FLAG-to-user patterns (do not auto-rewrite):**

| Pattern | Reason |
|---|---|
| `r.ok` | No `.ok` on httpx response. Ambiguous whether the original meant `status_code == 200` or `status_code < 400`. Ask. |
| `requests.get(..., stream=True)` with `r.iter_content()` | httpx streaming uses `with httpx.stream("GET", url) as r: for chunk in r.iter_bytes():`. Structural rewrite. |
| Any call site without explicit `timeout=` | **Behavior delta.** requests default = None (infinite); httpx default = 5s. Flag and ask the user whether to preserve `timeout=None` or set an explicit number. |
| Any call site relying on default redirect-following | **Behavior delta.** requests follows redirects by default; httpx does not. Add `follow_redirects=True` where appropriate. |

### Phase 2: `tenacity` → `stamina`

**Direct substitutions:**

```python
# Before
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.HTTPError),
)
def fetch(): ...
```

```python
# After
import stamina

@stamina.retry(on=httpx.HTTPError, attempts=3)
def fetch(): ...
```

Drop `wait=` arguments unless the call site explicitly tuned backoff in a way the user cares about — stamina applies exponential-with-jitter and sane caps by default.

**Composite stop conditions:**

| Before | After |
|---|---|
| `stop=stop_after_attempt(N) \| stop_after_delay(T)` | `@stamina.retry(on=..., attempts=N, timeout=T)` |

**FLAG-to-user patterns:**

| Pattern | Reason |
|---|---|
| `@retry()` with no arguments | tenacity default retries forever on any exception. Rewrite to `@stamina.retry(on=Exception, attempts=3)` and flag: explicit cap was added; confirm intent. |
| `retry=retry_if_result(...)` | stamina has no retry-on-result. Flag; leave call site untouched and ask the user to refactor the underlying function to raise on the bad result. |
| `@retry_async(...)` | Rewrite to `@stamina.retry(...)` — stamina's decorator is async-native. |
| `before_sleep=` / `after=` hooks | stamina exposes telemetry via structlog/prometheus/otel hooks instead of per-decorator callbacks. Flag and ask the user how to wire logging. |

### Phase 3: `tqdm` → `rich.progress`

**Iterable wrapping (mechanical):**

| Before | After |
|---|---|
| `from tqdm import tqdm` / `from tqdm.auto import tqdm` / `from tqdm.notebook import tqdm` | `from rich.progress import track` |
| `for x in tqdm(items):` | `for x in track(items):` |
| `for x in tqdm(items, desc="..."):` | `for x in track(items, description="..."):` |
| `for x in tqdm(items, total=N):` | `for x in track(items, total=N):` |

`rich.progress.track` auto-detects terminal vs notebook; the three tqdm import variants collapse to one rich import.

**Manual progress (no iterable):**

```python
# Before
pbar = tqdm(total=100)
for chunk in stream:
    process(chunk)
    pbar.update(len(chunk))
pbar.close()
```

```python
# After
from rich.progress import Progress
with Progress() as progress:
    task = progress.add_task("...", total=100)
    for chunk in stream:
        process(chunk)
        progress.update(task, advance=len(chunk))
```

**Description / postfix updates mid-loop:**

| Before | After |
|---|---|
| `pbar.set_description("X")` | `progress.update(task, description="X")` |
| `pbar.set_postfix(loss=0.5)` | `progress.update(task, description=f"loss={0.5:.2f}")` — rich has no separate postfix; fold into description. |
| `tqdm.write("...")` | `progress.console.print("...")` inside the with-block. |

**FLAG-to-user patterns:**

| Pattern | Reason |
|---|---|
| Nested `tqdm(outer)` + `tqdm(inner)` | rich uses a single `Progress` instance with multiple tasks; structural rewrite. |
| `tqdm` used as a context manager | Same shape as the manual-progress rewrite. |

## Open questions

None at design time. All design choices were resolved during brainstorming:

- Stale-package removal: **manual** (`pixi remove`); no companion `--prune-pixi` flag built.
- tqdm replacement: **rich.progress** rather than re-adding tqdm.
- Source-migration sequencing: **three independent commits** on the current branch, verification (`pixi run pre-commit run --all-files && pixi run test`) after each.

## Files touched by this migration

This design itself touches only `docs/superpowers/specs/2026-06-22-requests-tenacity-tqdm-migration-design.md` in `claude-code-tools`.

The eventual stage-3 prompt (produced by the implementation-plan phase) will, when executed by Claude Code inside the target project, touch:

- The project's source `.py` files containing `import requests` / `import tenacity` / `import tqdm`.
- Possibly README.md / docs if `rg` finds the old library names in example code.

The project's `pyproject.toml` is not edited — `[tool.ruff]` / `[tool.mypy]` config is library-agnostic.
