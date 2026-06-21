"""Executor adapter: dask.distributed LocalCluster with a per-run BLAS/OpenMP knob (spec 5.9)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, cast

from regatta.application.solve import solve_unit
from regatta.application.uow import UnitOfWork
from regatta.core.product import Product


@dataclass(frozen=True)
class ExecutorConfig:
    """Executor sizing: processes, threads-per-process (BLAS cap), and scheduler seam."""

    n_processes: int = 4
    threads_per_process: int = 1
    scheduler_address: str | None = None  # None -> spin up a LocalCluster


def _thread_env(threads: int) -> dict[str, str]:
    """Return the BLAS/OpenMP thread-cap environment for one worker."""
    t = str(threads)
    return {"OMP_NUM_THREADS": t, "OPENBLAS_NUM_THREADS": t, "MKL_NUM_THREADS": t}


class DaskExecutor:
    """The sole Phase-1 executor adapter. Scaling out changes only scheduler_address."""

    def __init__(self, config: ExecutorConfig) -> None:
        """Store config; the cluster/client are created on context entry.

        Args:
            config: The executor configuration.
        """
        self.config = config
        self._cluster: Any = None
        self._client: Any = None

    def __enter__(self) -> DaskExecutor:
        """Start (or connect to) the cluster and open a client."""
        from distributed import Client, LocalCluster

        if self.config.scheduler_address:
            self._client = Client(self.config.scheduler_address)  # type: ignore[no-untyped-call]
        else:
            self._cluster = LocalCluster(  # type: ignore[no-untyped-call]
                n_workers=self.config.n_processes,
                threads_per_worker=1,
                processes=True,
                env=_thread_env(self.config.threads_per_process),
            )
            self._client = Client(self._cluster)  # type: ignore[no-untyped-call]
        return self

    def __exit__(self, *exc: object) -> None:
        """Tear down the client and cluster on context exit."""
        if self._client:
            self._client.close()
        if self._cluster:
            self._cluster.close()

    def worker_env_sample(self) -> dict[str, str]:
        """Return one worker's BLAS/OpenMP environment (proves the cap is applied)."""
        keys = _thread_env(self.config.threads_per_process)
        result = self._client.run(lambda: {k: os.environ.get(k, "") for k in keys})
        return cast(dict[str, str], result.popitem()[1])

    def submit(self, unit_of_work: UnitOfWork) -> Product:
        """Run ``solve_unit`` on a worker and return the resulting Product."""
        future = self._client.submit(solve_unit, unit_of_work, pure=False)
        return cast(Product, future.result())
