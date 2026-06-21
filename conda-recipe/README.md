# conda-forge recipe (reference copy)

`meta.yaml` here is the conda-forge recipe for `sverdrup`. It is a **reference copy**;
the live recipe lives in the conda-forge feedstock once the package is accepted.

## One-time: get onto conda-forge

1. Fork **https://github.com/conda-forge/staged-recipes**.
2. Copy `meta.yaml` to `recipes/sverdrup/meta.yaml` in your fork (path must be exactly that).
3. Open a PR to `conda-forge/staged-recipes`. conda-forge CI builds the recipe on all
   platforms; a maintainer reviews and merges.
4. On merge, conda-forge auto-creates the feedstock **`conda-forge/sverdrup-feedstock`**
   and publishes `sverdrup` to the `conda-forge` channel.

## Ongoing: updates track PyPI automatically

Once the feedstock exists you do **nothing manual** for conda releases. The conda-forge
**autotick bot** watches PyPI; within hours of a new PyPI release it opens a version-bump
PR on the feedstock (new `version` + `sha256`, `build.number` reset to 0). You just:

1. Check the bot's PR (CI green).
2. If runtime deps changed, edit `requirements/run` in the same PR.
3. Merge. conda-forge builds and publishes the new conda package.

So the steady-state release flow is: push a `vX.Y.Z` tag → PyPI publishes (GitHub Action)
→ conda-forge autotick bot opens a PR → you merge it.

## If a release changes dependencies

The bot only bumps version + hash. When you add/drop/repin a runtime dep, mirror the change
from `pyproject.toml` `[project] dependencies` into `requirements/run` here and in the
feedstock PR. Keep this reference copy in sync so future contributors see the truth.
