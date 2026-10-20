"""Hygiene: scripts/resume_checks.sh reports — and exits on — what CLAUDE.md
says it does, and the hook tooling works in a linked worktree.

Each test builds real throwaway repos (a bare "origin" + clones) with git's
global/system config isolated, and runs the script exactly as a session
does: ``sh scripts/resume_checks.sh`` from inside the checkout.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
_ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
}


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603
        ["git", *args], cwd=cwd, env=_ENV, check=True, capture_output=True, text=True
    ).stdout.strip()


def _commit(repo: Path, name: str) -> None:
    (repo / name).write_text(name)
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", name)


def _checks(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["sh", str(_SCRIPTS / "resume_checks.sh")],
        cwd=cwd,
        env=_ENV,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A clone of a bare origin, in step, clean, with a stand-in hook."""
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    a = tmp_path / "a"
    _git(tmp_path, "clone", "-q", str(origin), str(a))
    _git(a, "checkout", "-q", "-b", "main")
    _commit(a, "first")
    _git(a, "push", "-q", "origin", "main")
    hook = a / ".git" / "hooks" / "post-commit"
    hook.write_text("#!/bin/sh\nexit 0\n")
    hook.chmod(0o755)
    return a


def _rival_push(repo: Path, name: str) -> None:
    other = repo.parent / f"rival_{name}"
    _git(repo.parent, "clone", "-q", str(repo.parent / "origin.git"), str(other))
    _commit(other, name)
    _git(other, "push", "-q", "origin", "main")


def test_in_step_and_clean_exits_zero(repo: Path) -> None:
    """Control: the all-good state passes."""
    done = _checks(repo)
    assert done.returncode == 0, done.stdout
    assert "in step" in done.stdout


def test_a_dirty_tree_exits_non_zero(repo: Path) -> None:
    """Bug caught: DIRTY was printed but never set the exit status, though
    CLAUDE.md step 0 says the script exits non-zero on tree state."""
    (repo / "stray.txt").write_text("x")
    done = _checks(repo)
    assert "DIRTY" in done.stdout
    assert done.returncode != 0


def test_origin_ahead_is_named_as_such(repo: Path) -> None:
    """Bug caught (pin 191): BEHIND/DIVERGED could not say the OWNER pushed
    while this session worked — the one case that needs a pull, not a push."""
    _rival_push(repo, "owner_work")
    _git(repo, "fetch", "-q", "origin")
    done = _checks(repo)
    assert "origin AHEAD" in done.stdout
    assert done.returncode != 0


def test_origin_ahead_with_unfetched_commits_says_fetch(repo: Path) -> None:
    """The remote head is not in this clone: the relation is unknown until
    a fetch — said so, not guessed."""
    _rival_push(repo, "owner_work")
    done = _checks(repo)
    assert "not in this clone" in done.stdout
    assert done.returncode != 0


def test_local_ahead_and_diverged_are_distinguished(repo: Path) -> None:
    """Bug caught: one label for 'unpushed' and 'diverged'."""
    _commit(repo, "mine")
    done = _checks(repo)
    assert "local AHEAD" in done.stdout and done.returncode != 0
    _rival_push(repo, "theirs")
    _git(repo, "fetch", "-q", "origin")
    done = _checks(repo)
    assert "DIVERGED" in done.stdout and done.returncode != 0


def test_an_unreachable_origin_is_not_reported_absent(repo: Path) -> None:
    """Bug caught: ls-remote's failure was swallowed (2>/dev/null) and an
    unreachable origin read as 'branch ABSENT on origin'."""
    _git(repo, "remote", "set-url", "origin", str(repo.parent / "nowhere.git"))
    done = _checks(repo)
    assert "UNREACHABLE" in done.stdout
    assert "ABSENT" not in done.stdout
    assert done.returncode != 0


def test_a_branch_missing_on_a_reachable_origin_is_absent(repo: Path) -> None:
    """Control for the above: ABSENT still means absent."""
    _git(repo, "checkout", "-q", "-b", "side")
    done = _checks(repo)
    assert "ABSENT" in done.stdout
    assert done.returncode != 0


def test_a_linked_worktree_sees_the_common_hook_and_marker(repo: Path) -> None:
    """Bug caught: --git-dir in a linked worktree is .git/worktrees/<name>,
    which has no hooks/ (git runs the COMMON dir's hooks) — the installed
    hook read as MISSING there, and a marker written from one checkout was
    invisible from the other."""
    wt = repo.parent / "wt"
    _git(repo, "worktree", "add", "-q", "-b", "wtb", str(wt))
    _git(wt, "push", "-q", "origin", "wtb")
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    (common / "UNPUSHED_COMMITS").write_text("main deadbeef push failed\n")
    done = _checks(wt)
    assert "post-commit hook : INSTALLED" in done.stdout, done.stdout
    assert "PRESENT" in done.stdout


def test_install_in_a_linked_worktree_installs_where_git_runs_hooks(
    repo: Path,
) -> None:
    """Bug caught: install_git_hooks.sh in a worktree linked into
    .git/worktrees/<name>/hooks, which git never consults — a silent no-hook."""
    versioned = repo / "scripts" / "git_hooks" / "post-commit"
    versioned.parent.mkdir(parents=True)
    versioned.write_text("#!/bin/sh\nexit 0\n")
    _git(repo, "add", "scripts")
    _git(repo, "commit", "-q", "-m", "versioned hook")
    wt = repo.parent / "wt"
    _git(repo, "worktree", "add", "-q", "-b", "wtb", str(wt))
    (repo / ".git" / "hooks" / "post-commit").unlink()
    subprocess.run(  # noqa: S603
        ["sh", str(_SCRIPTS / "install_git_hooks.sh")],
        cwd=wt,
        env=_ENV,
        check=True,
        capture_output=True,
    )
    hooks = Path(_git(wt, "rev-parse", "--path-format=absolute", "--git-path", "hooks"))
    assert (hooks / "post-commit").exists()
    assert hooks == repo / ".git" / "hooks"


def test_the_hook_marks_a_failed_push_in_the_COMMON_dir(repo: Path) -> None:
    """Bug caught: the post-commit hook wrote UNPUSHED_COMMITS under
    --git-dir — per-worktree — so a failed push from a linked worktree left
    a marker the main checkout's resume check never saw. The REAL hook is
    installed; origin is made unreachable so its push fails."""
    hook = repo / ".git" / "hooks" / "post-commit"
    hook.write_text((_SCRIPTS / "git_hooks" / "post-commit").read_text())
    hook.chmod(0o755)
    wt = repo.parent / "wt"
    _git(repo, "worktree", "add", "-q", "-b", "wtb", str(wt))
    _git(repo, "remote", "set-url", "origin", str(repo.parent / "nowhere.git"))
    _commit(wt, "offline")  # the hook runs, the push fails, LOUDLY
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    assert (common / "UNPUSHED_COMMITS").exists()
    assert "PRESENT" in _checks(repo).stdout  # the MAIN checkout sees it
