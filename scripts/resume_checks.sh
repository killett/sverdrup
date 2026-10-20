#!/bin/sh
# Resume-time repo state report (owner pin 104b).
#
# Run this EARLY in any resumed session — before committing anything.
# The finding it exists for: there was never a post-commit hook, and
# absence looked exactly like success for a whole stage. So absence is
# now a REPORTED state, not a silent one.
#
# Reports, in order:
#   1. post-commit hook installed?  (.git/hooks is NOT versioned — every
#      clone and every box rebuild starts without it)
#   2. any unpushed-commit marker left by the hook
#   3. local HEAD vs the REMOTE, read with ls-remote — never the local ref
#      (unreachable / absent / in step / origin ahead / local ahead /
#      diverged / remote commits not yet fetched)
#   4. working tree state
# Exits non-zero on anything but: hook installed, no marker, in step, clean.

root=$(git rev-parse --show-toplevel 2>/dev/null) || {
    echo "resume-checks: not a git repository" >&2
    exit 1
}
# Hooks live where git RUNS them (the common dir in a linked worktree, or
# core.hooksPath) and the push marker in the COMMON dir, shared by every
# worktree — --git-dir is .git/worktrees/<name> there, which has neither
# (hygiene). --path-format needs git >= 2.31.
hooks_dir=$(git rev-parse --path-format=absolute --git-path hooks)
common_dir=$(git rev-parse --path-format=absolute --git-common-dir)
branch=$(git rev-parse --abbrev-ref HEAD)
status=0

printf '== resume checks (%s) ==\n' "$branch"

# 1. hook presence
if [ -x "$hooks_dir/post-commit" ]; then
    printf 'post-commit hook : INSTALLED (-> %s)\n' \
        "$(readlink "$hooks_dir/post-commit" 2>/dev/null || echo "$hooks_dir/post-commit")"
else
    printf 'post-commit hook : *** MISSING *** — run: sh %s/scripts/install_git_hooks.sh\n' "$root"
    status=1
fi

# 2. marker from a previous failed push
marker="$common_dir/UNPUSHED_COMMITS"
if [ -f "$marker" ]; then
    printf 'unpushed marker  : *** PRESENT *** — %s\n' "$marker"
    sed 's/^/                   /' "$marker"
    status=1
else
    printf 'unpushed marker  : none\n'
fi

# 3. remote truth (pin 102b: ls-remote, never rev-parse alone). A FAILED
#    ls-remote is not an absent branch, and "differs" splits into the
#    cases that need different actions (pin 191: origin ahead = someone
#    else pushed; pull before writing).
local_sha=$(git rev-parse HEAD)
if ! remote_line=$(git ls-remote origin "refs/heads/$branch" 2>/dev/null); then
    printf 'origin/%-10s: *** UNREACHABLE *** — ls-remote failed; remote state UNKNOWN\n' "$branch"
    status=1
else
    remote_sha=$(printf '%s\n' "$remote_line" | head -n 1 | cut -f1)
    if [ -z "$remote_sha" ]; then
        printf 'origin/%-10s: *** ABSENT *** (local %s)\n' "$branch" "$local_sha"
        status=1
    elif [ "$remote_sha" = "$local_sha" ]; then
        printf 'origin/%-10s: in step at %s (ls-remote)\n' "$branch" "$local_sha"
    else
        if ! git cat-file -e "$remote_sha^{commit}" 2>/dev/null; then
            verdict='*** origin has commits not in this clone *** — git fetch, then re-run (origin AHEAD or DIVERGED)'
        elif git merge-base --is-ancestor "$local_sha" "$remote_sha"; then
            verdict='*** origin AHEAD *** — someone else pushed (pin 191): pull before writing'
        elif git merge-base --is-ancestor "$remote_sha" "$local_sha"; then
            verdict="*** local AHEAD *** — unpushed commits: git push origin $branch"
        else
            verdict='*** DIVERGED *** — both sides have commits the other lacks'
        fi
        printf 'origin/%-10s: %s\n  local  %s\n  remote %s\n' \
            "$branch" "$verdict" "$local_sha" "$remote_sha"
        status=1
    fi
fi

# 4. working tree (CLAUDE.md step 0: tree state is one of the non-zero exits)
if [ -n "$(git status --porcelain)" ]; then
    printf 'working tree     : *** DIRTY ***\n'
    git status --short | sed 's/^/                   /'
    status=1
else
    printf 'working tree     : clean\n'
fi

exit $status
