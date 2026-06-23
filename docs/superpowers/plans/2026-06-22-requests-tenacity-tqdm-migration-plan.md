# Requests/Tenacity/Tqdm Migration — Stage 3 Prompt

> **For agentic workers:** This plan delivers a paste-ready prompt for a *different* Claude Code session, launched inside the target project. It is NOT executed in the claude-code-tools session that wrote it. There is one task: produce the prompt artifact; that task is already complete by the existence of this file.

**Goal:** Provide a self-contained Claude Code prompt that, when pasted into a session running inside the target project, performs the source-code migration from `requests`/`tenacity`/`tqdm` to `httpx`/`stamina`/`rich.progress` per the spec.

**Architecture:** A single prompt block, designed to be pasted verbatim into Claude Code's input inside the target project's working directory. The prompt drives Claude through three independent commits (one per library replacement), with verification (`pixi run pre-commit run --all-files && pixi run test`) after each. Pre-flight check fails closed; stop conditions explicit; behavior deltas flagged rather than auto-rewritten.

**Tech Stack:** httpx, stamina, rich.progress (target libraries); pixi, ruff, mypy, pytest, pre-commit (verification tooling already present in any project scaffolded by `claude-code-tools`).

**User decisions (already made):**
- Stale-package removal: **manual** (`pixi remove`); no companion launcher flag built. The prompt assumes stages 1-2 are done and verifies it as the first action.
- tqdm replacement: **rich.progress**, not re-add tqdm.
- Source-migration sequencing: **three independent commits** on the current branch, verification after each. No branching, no amending.
- Verification command: matches the standard `claude-code-tools` scaffolded-project tooling (`pixi run pre-commit run --all-files` + `pixi run test`; final commit also runs `pixi run test --cov`).

**Spec:** `docs/superpowers/specs/2026-06-22-requests-tenacity-tqdm-migration-design.md` — the contract this plan implements.

---

## How to use this plan

This file contains, in the "Paste-ready prompt" section below, a single self-contained prompt block.

**Prerequisites (perform manually in the launcher before pasting):**

1. **Stage 0** — container rebuild after pulling latest `claude-code-tools`:
   ```
   sandboxed-claude.sh <project>
   ```
   Quit Claude once the rebuild finishes.

2. **Stage 1** — sync new deps into the project's pixi.toml:
   ```
   sandboxed-claude.sh --sync-pixi <project>
   ```
   Press `a` at the prompt to apply all five missing packages (`httpx`, `pydantic`, `typer`, `rich`, `stamina`). Quit Claude once the sync finishes.

3. **Stage 2** — remove stale packages:
   ```
   sandboxed-claude.sh --entry bash <project>
   pixi remove requests tenacity tqdm
   exit
   ```

**Then to execute Stage 3:**

4. Launch Claude Code inside the target project:
   ```
   sandboxed-claude.sh <project>
   ```
5. Once Claude Code is ready in the project's working directory, **paste the entire prompt block from the next section** into Claude Code's input and submit.

Claude will perform the pre-flight check, then run the three-commit migration. If the pre-flight check fails (i.e., stages 1-2 weren't done), Claude will stop and ask you to complete them first.

---

## Paste-ready prompt

Everything inside the triple-backtick block below is the prompt. Copy from the first character of the prompt body to the last and paste as-is.

````
You are running inside a project that was scaffolded by `claude-code-tools`. The project's `[utils]` group was recently updated upstream: `requests`, `tenacity`, and `tqdm` are gone; `httpx`, `pydantic`, `typer`, `rich`, and `stamina` are in. The project's `pixi.toml` and installed env have already been updated by manual stages 1-2. Your job is to migrate the source code: rewrite call sites for the three retired libraries to their new equivalents, in three independent commits on the current branch.

═══ PRE-FLIGHT CHECK ═══

Before doing anything else, run this single shell pipeline:

```
pixi list | rg -q 'httpx|stamina' && ! pixi list | rg -q '^(requests|tenacity|tqdm)\s'
```

Interpret the result by exit code:

- **Exit 0 (pre-flight passes):** Continue to Phase 1.
- **Exit non-zero (pre-flight fails):** STOP. Report to the user verbatim: "Pre-flight failed. The project's pixi env still has stale packages or is missing the new ones. Run stages 1 (`sandboxed-claude.sh --sync-pixi <project>`) and 2 (`pixi remove requests tenacity tqdm` inside `--entry bash`) per the migration spec, then re-paste this prompt." Do not attempt any rewrites until pre-flight passes.

═══ PHASE 1: requests → httpx ═══

**Step 1.1 — Inventory.** Run:

```
rg -l 'import requests|from requests' --type py
```

If zero hits, log "Phase 1: no requests call sites found; skipping" and jump to Phase 2.

Otherwise, for each file in the result, also grep within it for:
- `requests.get`, `requests.post`, `requests.put`, `requests.patch`, `requests.delete`, `requests.head`
- `requests.Session`
- `requests.exceptions.`
- `.ok` on response variables (search for `\.ok\b`)
- `stream=True`
- usages of `timeout=` keyword (or absence of it on `requests.*` calls)
- usages of `allow_redirects=` (or absence of it)

**Step 1.2 — Rewrite.** Apply these mechanical substitutions to every affected file:

| Before | After |
|---|---|
| `import requests` | `import httpx` |
| `from requests import X` | `from httpx import X` (X usually unchanged) |
| `requests.get/post/put/patch/delete/head(url, ...)` | `httpx.<verb>(url, ...)` — drop-in |
| `r.status_code`, `r.text`, `r.content`, `r.headers`, `r.json()`, `r.raise_for_status()` | unchanged |
| `requests.Session()` | `httpx.Client()` — wrap usages in `with httpx.Client() as client:` |
| `session.<verb>(...)` | `client.<verb>(...)` |

Exception class map (apply in `except` clauses and `isinstance` checks):

| Before | After |
|---|---|
| `requests.exceptions.RequestException` | `httpx.RequestError` |
| `requests.exceptions.HTTPError` | `httpx.HTTPStatusError` |
| `requests.exceptions.ConnectionError` | `httpx.ConnectError` |
| `requests.exceptions.Timeout` | `httpx.TimeoutException` |
| `requests.exceptions.TooManyRedirects` | `httpx.TooManyRedirects` |

**FLAG-TO-USER patterns — do NOT auto-rewrite these. Stop and ask:**

- `r.ok` — httpx response has no `.ok` property. Ambiguous whether the original code meant `r.status_code == 200` or `r.status_code < 400`. Ask the user which semantics they want and apply their answer.
- `requests.get(..., stream=True)` paired with `r.iter_content()` — httpx streaming uses `with httpx.stream("GET", url) as r: for chunk in r.iter_bytes():`. Structural rewrite. Show the user the affected block and confirm before rewriting.
- Any call site that does NOT pass `timeout=` explicitly — **behavior delta:** requests default = None (infinite); httpx default = 5 seconds. After the rewrite this call will start raising `httpx.ReadTimeout` if the response takes more than 5 seconds. Ask the user per call site: `timeout=None` (preserve old behavior) or an explicit value.
- Any call site that does NOT pass `allow_redirects=` AND seems to rely on redirect-following — **behavior delta:** requests follows redirects by default; httpx does NOT. Default rewrite: add `follow_redirects=True` (httpx's parameter name). Flag for review.

**Step 1.3 — Verify.** Run, in order:

```
pixi run pre-commit run --all-files
```

If it fails, fix the issue (almost certainly ruff/mypy/import-sort fallout from the import changes), re-stage, run pre-commit again. Do NOT amend. Per the project's CLAUDE.md: if pre-commit fails, the commit did not happen — fix and create a new commit attempt.

Then:

```
pixi run test
```

Interpret the result:

- **All pass:** continue to Step 1.4.
- **Any fail:** STOP. Report to the user:
  - Which test failed.
  - Which assertion message it produced.
  - Your hypothesis of which library-behavior delta caused it (timeout default, redirect default, exception class hierarchy, `.ok` ambiguity, etc.).
  - Do NOT paper over the failure with `try/except` or by changing the test. Ask the user to triage.

**Step 1.4 — Commit.**

```
git add -A
git commit -m 'refactor: migrate HTTP client from requests to httpx'
```

═══ PHASE 2: tenacity → stamina ═══

**Step 2.1 — Inventory.**

```
rg -l 'import tenacity|from tenacity' --type py
```

If zero hits, log "Phase 2: no tenacity call sites found; skipping" and jump to Phase 3.

For each affected file, grep for: `@retry`, `@retry_async`, `stop_after_attempt`, `stop_after_delay`, `wait_exponential`, `retry_if_exception_type`, `retry_if_result`, `before_sleep`, `after=`, `RetryError`, `AsyncRetrying`.

**Step 2.2 — Rewrite.** Standard substitution:

Before:
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.HTTPError),
)
def fetch(): ...
```

After:
```python
import stamina

@stamina.retry(on=httpx.HTTPError, attempts=3)
def fetch(): ...
```

**Drop `wait=` arguments unconditionally** unless the call site explicitly tuned backoff in a way the user cares about (e.g. comments like "must wait at least 30s between retries to comply with rate limit"). Stamina applies exponential-with-jitter and sane caps by default.

Composite stop conditions:

| Before | After |
|---|---|
| `stop=stop_after_attempt(N) \| stop_after_delay(T)` | `@stamina.retry(on=..., attempts=N, timeout=T)` |

`RetryError` → `stamina.RetryLimitExceeded` (in `except` clauses).

**FLAG-TO-USER patterns:**

- `@retry()` with no arguments — tenacity default retries forever on any exception. Default rewrite: `@stamina.retry(on=Exception, attempts=3)`. Flag: "Added explicit `attempts=3` cap; tenacity behavior was retry-forever. Confirm intent."
- `retry=retry_if_result(...)` — stamina has no retry-on-result; it only retries on exception types. STOP and ask the user. Two options to offer: (a) refactor the underlying function to raise on the bad result, then stamina-retry on that exception class; (b) keep tenacity for this one call site (project would then need `pixi add tenacity`).
- `@retry_async(...)` — rewrite to `@stamina.retry(...)`. Stamina is async-native; the same decorator works on async functions.
- `before_sleep=...` / `after=...` callback hooks — stamina exposes retry telemetry via structlog/prometheus/otel hooks instead of per-decorator callbacks. Flag and ask the user how they want retry logging wired (or whether to drop it).

**Step 2.3 — Verify.** Same shape as Phase 1:

```
pixi run pre-commit run --all-files
pixi run test
```

Same stop semantics as Phase 1 Step 1.3.

**Step 2.4 — Commit.**

```
git add -A
git commit -m 'refactor: migrate retry layer from tenacity to stamina'
```

═══ PHASE 3: tqdm → rich.progress ═══

**Step 3.1 — Inventory.**

```
rg -l 'import tqdm|from tqdm' --type py
```

If zero hits, log "Phase 3: no tqdm call sites found; skipping" and jump to Final Verification.

For each affected file, grep for: `tqdm(`, `tqdm.auto`, `tqdm.notebook`, `.update(`, `.set_description(`, `.set_postfix(`, `tqdm.write(`, `with tqdm(`.

**Step 3.2 — Rewrite.** Iterable-wrapping (most common, mechanical):

| Before | After |
|---|---|
| `from tqdm import tqdm` (or `tqdm.auto.tqdm`, `tqdm.notebook.tqdm`) | `from rich.progress import track` |
| `for x in tqdm(items):` | `for x in track(items):` |
| `for x in tqdm(items, desc="..."):` | `for x in track(items, description="..."):` |
| `for x in tqdm(items, total=N):` | `for x in track(items, total=N):` |

Manual progress (no iterable):

Before:
```python
pbar = tqdm(total=100)
for chunk in stream:
    process(chunk)
    pbar.update(len(chunk))
pbar.close()
```

After:
```python
from rich.progress import Progress
with Progress() as progress:
    task = progress.add_task("...", total=100)
    for chunk in stream:
        process(chunk)
        progress.update(task, advance=len(chunk))
```

Mid-loop updates:

| Before | After |
|---|---|
| `pbar.set_description("X")` | `progress.update(task, description="X")` |
| `pbar.set_postfix(loss=0.5)` | `progress.update(task, description=f"loss={0.5:.2f}")` — fold into description; rich has no separate postfix. |
| `tqdm.write("...")` | `progress.console.print("...")` (only valid inside the `with Progress() as progress:` block). |

**FLAG-TO-USER patterns:**

- Nested `tqdm(outer)` + `tqdm(inner)` — rich uses one `Progress` instance with multiple tasks; the rewrite is structural. Show the user the affected block and confirm before rewriting.
- `tqdm` used as a context manager (`with tqdm(...) as pbar:`) — same shape as the manual-progress rewrite. Apply the manual-progress pattern.

**Step 3.3 — Verify.** Same:

```
pixi run pre-commit run --all-files
pixi run test
```

**Step 3.4 — Commit.**

```
git add -A
git commit -m 'refactor: migrate progress bars from tqdm to rich.progress'
```

═══ FINAL VERIFICATION ═══

After Phase 3 commits (or after the last phase that actually performed a rewrite — phases that found zero call sites are skipped, not verified), run the coverage-included test pass to match the project's CLAUDE.md "Run pytest --cov before committing" rule. This does NOT produce a new commit; it's a confidence check on the cumulative result:

```
pixi run pre-commit run --all-files
pixi run test --cov
```

If both pass, report to the user verbatim:

"Migration complete. Commits on this branch:
  - refactor: migrate HTTP client from requests to httpx
  - refactor: migrate retry layer from tenacity to stamina
  - refactor: migrate progress bars from tqdm to rich.progress
All pre-commit + test --cov checks green. Phases skipped: <list any that had zero call sites, or 'none'>. Items flagged during migration that need your decision: <list any flagged patterns from Phases 1-3 that the user resolved during the run, or 'none'>."

═══ OUT OF SCOPE — DO NOT DO ═══

- Do NOT edit `pixi.toml`. Stages 1 and 2 (manual, performed before this prompt) already handled it.
- Do NOT add new tests. This is a behavior-preserving refactor; the existing suite is the contract.
- Do NOT amend or rebase prior commits.
- Do NOT branch. Commit on the current branch.
- Do NOT touch CHANGELOG / docs / README unless `rg` finds the retired library names in those files (e.g. usage examples). If it does, fold those edits into the matching phase's commit.
- Do NOT run `pixi add`, `pixi remove`, or `pixi install` for any reason. If a phase needs a missing package, the pre-flight check should have caught it; if you discover one anyway, STOP and tell the user.

═══ STOP CONDITIONS (recap) ═══

You MUST stop and ask the user when:

- Pre-flight check fails.
- `pixi run pre-commit run --all-files` keeps failing after one fix attempt.
- `pixi run test` fails after a rewrite — report which test, which assertion, which library-behavior delta is the likely cause.
- A FLAG-TO-USER pattern (`.ok`, `stream=True`, missing `timeout=`, missing `follow_redirects=`, `@retry()` no-args, `retry_if_result`, before_sleep hooks, nested tqdm) is found.

Do NOT proceed past a stop condition without an explicit user instruction.

═══ START NOW ═══

Begin with the pre-flight check.
````

---

## What the prompt does internally (for human review)

The prompt's flow:

1. **Pre-flight check** — one shell pipeline confirming stages 1-2 were done. Fails closed: if env state doesn't match expectations, the prompt instructs Claude to stop rather than guess.
2. **Phase 1 (requests → httpx)** — inventory call sites with `rg`; apply the substitution and exception-map tables; flag behavior-delta patterns (`.ok`, streaming, default `timeout`, default redirects) for user resolution; verify with `pre-commit` + `pytest`; commit.
3. **Phase 2 (tenacity → stamina)** — same shape: inventory, substitute, flag (`@retry()` no-args, `retry_if_result`, hook patterns), verify, commit.
4. **Phase 3 (tqdm → rich.progress)** — same shape: inventory, substitute (with the structural manual-progress and mid-loop-update patterns), flag nested tqdm, verify, commit.
5. **Final verification** — `pixi run pre-commit run --all-files && pixi run test --cov` (the only `--cov` run; per-phase runs use plain `pixi run test` for speed).
6. **Out-of-scope guardrails** — the prompt explicitly lists what NOT to do (no pixi edits, no new tests, no branching, no amending).
7. **Stop-condition recap** — duplicated near the end so the LLM doesn't lose them under context pressure.

## Acceptance criteria for this plan

- [ ] The plan file exists at `docs/superpowers/plans/2026-06-22-requests-tenacity-tqdm-migration-plan.md` and is co-located with its tasks JSON.
- [ ] The "Paste-ready prompt" section contains a self-contained prompt that, when extracted from the surrounding markdown, can be pasted into Claude Code without further editing.
- [ ] The prompt's pre-flight check matches the spec's: `pixi list | rg -q 'httpx|stamina' && ! pixi list | rg -q '^(requests|tenacity|tqdm)\s'`.
- [ ] The prompt's three commit messages match the spec's Conventional Commits formulation.
- [ ] The prompt's verification command matches the project's CLAUDE.md scaffolded-project convention: `pixi run pre-commit run --all-files && pixi run test` per phase, `pixi run test --cov` at end.
- [ ] All FLAG-TO-USER patterns from the spec's Section 4 tables appear in the prompt with explicit stop-and-ask instructions.
- [ ] All OUT-OF-SCOPE items from the spec's "Stage 3 source-code migration prompt structure" section appear in the prompt's DO-NOT-DO list.

## How to verify

The plan is the artifact. To verify it:

1. Open this file in a text editor.
2. Locate the "Paste-ready prompt" section.
3. Confirm the section opens with `═══ PRE-FLIGHT CHECK ═══` (the prompt's own header) and ends with `═══ START NOW ═══`.
4. Cross-check the seven acceptance criteria above against the prompt body.
5. Optionally — and this is the real-world test — run stages 0-2 against the target project, then paste the prompt block (everything between the markdown code fence opener and closer in the "Paste-ready prompt" section) into a Claude Code session inside that project. The migration completes if all three commits land cleanly and `pixi run test --cov` is green.

There is no automated `pytest`-style verification for this plan because the deliverable is a paste artifact, not code that runs in this repo.
