"""Hygiene item 50: what ``src/sverdrup`` imports, the package declares.

The 2026-10-18 audit found the pipeline's import path needing packages that
``pyproject.toml`` declared nowhere — not in ``[project] dependencies``, not
in any extra (``scikit-sparse`` already in the published v0.2.0, plus
``pydantic``/``python-dotenv`` since). ``pip install 'sverdrup[all]'`` could
not run the pipeline, and the release workflow never install-smokes the
wheel, so nothing would ever say so.

Expected values come from the source tree and the manifest, read
independently — never from the code under test.
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

# Import name -> distribution name, where the two differ.
_DIST_FOR_IMPORT = {
    "dotenv": "python-dotenv",
    "sksparse": "scikit-sparse",
    "distributed": "dask",  # declared as dask[distributed]
}
# ``src`` is the vendored challenge code (a git submodule imported as
# ``src.*``), not a distribution.
_NOT_A_DISTRIBUTION = {"sverdrup", "src", "__future__"}


def _third_party_imports() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for path in (_ROOT / "src" / "sverdrup").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules = [node.module]
            else:
                continue
            for module in modules:
                top = module.split(".")[0]
                if top in sys.stdlib_module_names or top in _NOT_A_DISTRIBUTION:
                    continue
                found.setdefault(top, set()).add(path.name)
    return found


def _declared_distributions() -> set[str]:
    project = tomllib.loads((_ROOT / "pyproject.toml").read_text())["project"]
    requirements = list(project["dependencies"])
    for extra in project.get("optional-dependencies", {}).values():
        requirements.extend(extra)
    names = set()
    for req in requirements:
        name = re.split(r"[\[<>=!~;\s]", req, maxsplit=1)[0]
        names.add(name.lower().replace("_", "-"))
    return names


def test_every_third_party_import_is_a_declared_dependency() -> None:
    """Bug caught: an import the manifest does not declare (ImportError on a
    clean install, invisible in the pixi env that happens to have it)."""
    declared = _declared_distributions()
    missing = sorted(
        f"{_DIST_FOR_IMPORT.get(top, top)} (imported by {', '.join(sorted(files))})"
        for top, files in _third_party_imports().items()
        if _DIST_FOR_IMPORT.get(top, top).lower() not in declared
    )
    assert missing == []


_BLOCK_SKSPARSE = (
    "import sys; sys.modules['sksparse'] = None; "
    "sys.modules['sksparse.cholmod'] = None; "
)


def _run(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed interpreter, fixed code
        [sys.executable, "-c", _BLOCK_SKSPARSE + code],
        capture_output=True,
        text=True,
        check=False,
        cwd=_ROOT,
    )


def test_the_method_registry_imports_without_scikit_sparse() -> None:
    """Bug caught: ``gmrf_linalg`` importing sksparse at module level, which
    made ``sverdrup.methods.registry`` — every method, OI and MIOST included
    — unimportable without the SuiteSparse-backed extra."""
    done = _run("import sverdrup.methods.registry; print('ok')")
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "ok"


def test_using_gmrf_without_scikit_sparse_names_the_extra() -> None:
    """Bug caught: a lazy import that fails with a bare ModuleNotFoundError
    instead of telling the user which extra to install."""
    done = _run(
        "import scipy.sparse as sp; "
        "from sverdrup.methods.gmrf_linalg import GMRFFactor; "
        "GMRFFactor(sp.identity(3, format='csc'))"
    )
    assert done.returncode != 0
    assert "ImportError" in done.stderr
    assert "sverdrup[gmrf]" in done.stderr
