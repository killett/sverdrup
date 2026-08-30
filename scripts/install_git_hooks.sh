#!/bin/sh
# Install the repo's git hooks into .git/hooks (owner pin 102a).
#
# .git/hooks is not versioned, so a fresh clone — or a rebuilt box — starts
# with NO post-commit hook and nothing says so. Run this after cloning.
set -e

root=$(git rev-parse --show-toplevel)
hooks=$(git rev-parse --git-dir)/hooks
mkdir -p "$hooks"

for src in "$root"/scripts/git_hooks/*; do
    name=$(basename "$src")
    ln -sf "$src" "$hooks/$name"
    chmod +x "$src"
    echo "installed: $hooks/$name -> $src"
done
