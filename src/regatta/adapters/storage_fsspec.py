"""Local fsspec result-sink writing the persisted Product bundle + provenance (spec 5.8)."""

from __future__ import annotations

import json
from typing import Any

import fsspec  # type: ignore[import-untyped]
import numpy as np
from fsspec import AbstractFileSystem

from regatta.core.grid import GridSpec
from regatta.core.product import PerTimeProduct, Product
from regatta.core.provenance import ProductProvenance, UncertaintyProvenance
from regatta.core.types import UncertaintyCapability
from regatta.distributions.persisted import PersistedDistribution, PersistedFields


def _prov_to_json(p: ProductProvenance) -> dict[str, Any]:
    """Serialise product provenance to a JSON-safe dict."""
    return {
        "method": p.method,
        "params_key": p.params_key,
        "seed": p.seed,
        "split_id": p.split_id,
        "code_version": p.code_version,
        "native_capability": p.uncertainty.native_capability.name,
    }


def _save_array(fs: AbstractFileSystem, path: str, arr: np.ndarray) -> None:
    """Write a numpy array to ``path`` on filesystem ``fs``."""
    with fs.open(path, "wb") as f:
        np.save(f, arr)


def _load_array(fs: AbstractFileSystem, path: str) -> np.ndarray:
    """Read a numpy array from ``path`` on filesystem ``fs``."""
    with fs.open(path, "rb") as f:
        return np.asarray(np.load(f))


class FsspecResultSink:
    """Persists a Product bundle to any fsspec URL as per-time arrays + a JSON manifest."""

    def write(self, product: Product, path: str) -> None:
        """Write ``product`` to ``path`` (an fsspec URL).

        Args:
            product: The persisted Product bundle.
            path: The destination fsspec URL (e.g. ``file://.../prod.zarr``).
        """
        fs, root = fsspec.core.url_to_fs(path)
        fs.makedirs(root, exist_ok=True)
        per_time_meta: list[dict[str, Any]] = []
        for i, pt in enumerate(product.per_time):
            base = pt.base
            grp = f"{root}/t{i}"
            fs.makedirs(grp, exist_ok=True)
            arrays = {
                "mean": base.fields.mean,
                "marginal_variance": base.fields.marginal_variance,
                "factor": base.fields.factor,
                "residual": base.fields.residual,
                "x": base.grid.x,
                "y": base.grid.y,
            }
            for name, arr in arrays.items():
                _save_array(fs, f"{grp}/{name}.npy", arr)
            per_time_meta.append(
                {
                    "time_days": pt.time_days,
                    "rank": base.fields.rank,
                    "captured_energy": base.fields.captured_energy,
                    "provenance": _prov_to_json(pt.provenance),
                }
            )
        manifest = {
            "times": product.times(),
            "run": product.run_manifest,
            "per_time": per_time_meta,
        }
        with fs.open(f"{root}/manifest.json", "w") as f:
            json.dump(manifest, f)


def read_product(path: str) -> Product:
    """Reconstruct a Product bundle previously written by ``FsspecResultSink``.

    Args:
        path: The fsspec URL the product was written to.

    Returns:
        The reconstructed Product (persisted representation, not sample maps).
    """
    fs, root = fsspec.core.url_to_fs(path)
    with fs.open(f"{root}/manifest.json") as f:
        manifest = json.load(f)
    per_time: list[PerTimeProduct] = []
    for i, meta in enumerate(manifest["per_time"]):
        grp = f"{root}/t{i}"
        prov_meta = meta["provenance"]
        fields = PersistedFields(
            mean=_load_array(fs, f"{grp}/mean.npy"),
            marginal_variance=_load_array(fs, f"{grp}/marginal_variance.npy"),
            factor=_load_array(fs, f"{grp}/factor.npy"),
            residual=_load_array(fs, f"{grp}/residual.npy"),
            rank=meta["rank"],
            seed=prov_meta["seed"],
            captured_energy=meta["captured_energy"],
        )
        grid = GridSpec.lonlat(
            _load_array(fs, f"{grp}/x.npy"), _load_array(fs, f"{grp}/y.npy")
        )
        prov = ProductProvenance(
            method=prov_meta["method"],
            params_key=prov_meta["params_key"],
            seed=prov_meta["seed"],
            split_id=prov_meta["split_id"],
            code_version=prov_meta["code_version"],
            input_manifest={},
            uncertainty=UncertaintyProvenance(
                UncertaintyCapability[prov_meta["native_capability"]], []
            ),
        )
        dist = PersistedDistribution(grid, fields, prov.uncertainty, meta["time_days"])
        per_time.append(PerTimeProduct(meta["time_days"], dist, {}, None, prov))
    return Product(per_time=per_time, run_manifest=manifest["run"])
