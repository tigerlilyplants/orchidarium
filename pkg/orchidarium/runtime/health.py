"""
Track metrics thread-pool health across processes.
"""


from __future__ import annotations

import traceback

from threading import Lock
from typing import Any, Literal

from attrs import define, field
from cattrs import unstructure

from orchidarium.runtime.state import read_runtime_state, update_runtime_state


__all__ = [
    'get_thread_pool_health',
    'is_thread_pool_healthy',
    'is_thread_pool_ready',
    'mark_thread_pool_failed',
    'mark_thread_pool_healthy',
    'mark_thread_pool_started'
]


_PoolStatus = Literal['starting', 'running', 'healthy', 'failed']


@define
class _ThreadPoolHealthSnapshot:
    status: _PoolStatus
    expected_workers: int
    completed_workers: int
    failed_workers: int
    last_run_successful: bool
    successful_runs: int
    last_error: str | None


@define
class _ThreadPoolHealth:
    status: _PoolStatus = 'starting'
    expected_workers: int = 0
    completed_workers: int = 0
    failed_workers: int = 0
    last_run_successful: bool = False
    successful_runs: int = 0
    last_error: str | None = None
    _lock: Lock = field(factory=Lock, init=False, repr=False)

    def snapshot(self) -> dict[str, Any]:
        """
        Return this process's current thread-pool health.

        Returns:
            dict[str, Any]: thread-pool health fields.
        """
        with self._lock:
            return unstructure(
                _ThreadPoolHealthSnapshot(
                    status=self.status,
                    expected_workers=self.expected_workers,
                    completed_workers=self.completed_workers,
                    failed_workers=self.failed_workers,
                    last_run_successful=self.last_run_successful,
                    successful_runs=self.successful_runs,
                    last_error=self.last_error
                )
            )

    def started(self, expected_workers: int) -> None:
        """
        Mark the pool as running.

        Args:
            expected_workers (int): number of submitted sensor workers.
        """
        with self._lock:
            self.status = 'running'
            self.expected_workers = expected_workers
            self.completed_workers = 0
            self.failed_workers = 0
            self.last_error = None

    def healthy(self, completed_workers: int) -> None:
        """
        Mark the pool as healthy.

        Args:
            completed_workers (int): number of completed sensor workers.
        """
        with self._lock:
            self.status = 'healthy'
            self.completed_workers = completed_workers
            self.failed_workers = 0
            self.last_run_successful = True
            self.successful_runs += 1
            self.last_error = None

    def failed(self, completed_workers: int, failed_workers: int, error: BaseException | str | None = None) -> None:
        """
        Mark the pool as failed.

        Args:
            completed_workers (int): number of completed sensor workers.
            failed_workers (int): number of failed sensor workers.
            error (BaseException | str | None): optional failure detail.
        """
        with self._lock:
            self.status = 'failed'
            self.completed_workers = completed_workers
            self.failed_workers = failed_workers
            self.last_run_successful = False
            self.last_error = ''.join(traceback.format_exception(error)) if isinstance(error, BaseException) else error


_thread_pool_health = _ThreadPoolHealth()


def _published_thread_pool_health() -> dict[str, Any] | None:
    thread_pool = read_runtime_state().get('thread_pool')

    if isinstance(thread_pool, dict):
        return thread_pool

    return None


def _publish_thread_pool_health() -> None:
    update_runtime_state(thread_pool=_thread_pool_health.snapshot())


def _expected_workers(snapshot: dict[str, Any]) -> int:
    expected_workers = snapshot.get('expected_workers')

    if isinstance(expected_workers, int):
        return expected_workers

    return 0


def _failed_workers(snapshot: dict[str, Any]) -> int:
    failed_workers = snapshot.get('failed_workers')

    if isinstance(failed_workers, int):
        return failed_workers

    return 0


def get_thread_pool_health() -> dict[str, Any]:
    """
    Return the latest metrics thread-pool health snapshot.

    Returns:
        dict[str, Any]: thread-pool health fields suitable for JSON serialization.
    """
    return _published_thread_pool_health() or _thread_pool_health.snapshot()


def is_thread_pool_healthy() -> bool:
    """
    Return whether the latest metrics thread-pool snapshot is healthy.

    Returns:
        bool: True when the metrics thread pool is running or healthy.
    """
    snapshot = get_thread_pool_health()
    return (
        snapshot.get('status') in {'running', 'healthy'}
        and _expected_workers(snapshot) > 0
        and _failed_workers(snapshot) == 0
    )


def is_thread_pool_ready() -> bool:
    """
    Return whether the latest metrics thread-pool snapshot is ready.

    Returns:
        bool: True when metrics have completed successfully or are running after a successful run.
    """
    snapshot = get_thread_pool_health()
    return (
        (
            snapshot.get('status') == 'healthy'
            or (
                snapshot.get('status') == 'running'
                and snapshot.get('last_run_successful') is True
            )
        )
        and _expected_workers(snapshot) > 0
        and _failed_workers(snapshot) == 0
    )


def mark_thread_pool_started(expected_workers: int) -> None:
    """
    Mark the sensor thread pool as started.

    Args:
        expected_workers (int): number of sensor worker futures submitted.
    """
    _thread_pool_health.started(expected_workers)
    _publish_thread_pool_health()


def mark_thread_pool_healthy(completed_workers: int) -> None:
    """
    Mark the sensor thread pool as healthy after a completed run.

    Args:
        completed_workers (int): number of sensor worker futures that completed.
    """
    _thread_pool_health.healthy(completed_workers)
    _publish_thread_pool_health()


def mark_thread_pool_failed(completed_workers: int = 0, failed_workers: int = 1, error: BaseException | str | None = None) -> None:
    """
    Mark the sensor thread pool as failed.

    Args:
        completed_workers (int): number of sensor worker futures that completed.
        failed_workers (int): number of failed sensor worker futures.
        error (BaseException | str | None): optional failure detail.
    """
    _thread_pool_health.failed(completed_workers, failed_workers, error)
    _publish_thread_pool_health()
