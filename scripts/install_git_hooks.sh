#!/bin/sh
# Install the repo's git hooks into .git/hooks (owner pin 102a).
#
# .git/hooks is not versioned, so a fresh clone — or a rebuilt box — starts
# with NO post-commit hook and nothing says so. Run this after cloning.
set -e

root=$(git rev-parse --show-toplevel)
# Where git RUNS hooks: the common dir in a linked worktree (or core.hooksPath)
# — --git-dir/hooks there is a directory git never consults (hygiene).
hooks=$(git rev-parse --path-format=absolute --git-path hooks)
mkdir -p "$hooks"

for src in "$root"/scripts/git_hooks/*; do
    name=$(basename "$src")
    ln -sf "$src" "$hooks/$name"
    chmod +x "$src"
    echo "installed: $hooks/$name -> $src"
done
