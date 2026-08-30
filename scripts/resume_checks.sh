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

root=$(git rev-parse --show-toplevel 2>/dev/null) || {
    echo "resume-checks: not a git repository" >&2
    exit 1
}
git_dir=$(git rev-parse --git-dir)
branch=$(git rev-parse --abbrev-ref HEAD)
status=0

printf '== resume checks (%s) ==\n' "$branch"

# 1. hook presence
if [ -x "$git_dir/hooks/post-commit" ]; then
    printf 'post-commit hook : INSTALLED (-> %s)\n' \
        "$(readlink "$git_dir/hooks/post-commit" 2>/dev/null || echo "$git_dir/hooks/post-commit")"
else
    printf 'post-commit hook : *** MISSING *** — run: sh %s/scripts/install_git_hooks.sh\n' "$root"
    status=1
fi

# 2. marker from a previous failed push
if [ -f "$git_dir/UNPUSHED_COMMITS" ]; then
    printf 'unpushed marker  : *** PRESENT *** — %s\n' "$git_dir/UNPUSHED_COMMITS"
    sed 's/^/                   /' "$git_dir/UNPUSHED_COMMITS"
    status=1
else
    printf 'unpushed marker  : none\n'
fi

# 3. remote truth (pin 102b: ls-remote, never rev-parse alone)
local_sha=$(git rev-parse HEAD)
remote_sha=$(git ls-remote origin "refs/heads/$branch" 2>/dev/null | cut -f1)
if [ -z "$remote_sha" ]; then
    printf 'origin/%-10s: *** ABSENT *** (local %s)\n' "$branch" "$local_sha"
    status=1
elif [ "$remote_sha" != "$local_sha" ]; then
    printf 'origin/%-10s: *** BEHIND/DIVERGED ***\n  local  %s\n  remote %s\n' \
        "$branch" "$local_sha" "$remote_sha"
    status=1
else
    printf 'origin/%-10s: in step at %s (ls-remote)\n' "$branch" "$local_sha"
fi

# 4. working tree
if [ -n "$(git status --porcelain)" ]; then
    printf 'working tree     : DIRTY\n'
    git status --short | sed 's/^/                   /'
else
    printf 'working tree     : clean\n'
fi

exit $status
