"""
Serve a healthcheck endpoint when in daemon mode.
"""


from http import HTTPStatus
from flask import Flask
from flask.typing import ResponseReturnValue

import logging
import traceback

from attrs import define, field
from cattrs import unstructure
from threading import Lock
from typing import Any, Literal

log = logging.getLogger(__name__)


__all__ = [
    'create_healthcheck_api',
    'get_thread_pool_health',
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
        with self._lock:
            self.status = 'running'
            self.expected_workers = expected_workers
            self.completed_workers = 0
            self.failed_workers = 0
            self.last_error = None

    def healthy(self, completed_workers: int) -> None:
        with self._lock:
            self.status = 'healthy'
            self.completed_workers = completed_workers
            self.failed_workers = 0
            self.last_run_successful = True
            self.successful_runs += 1
            self.last_error = None

    def failed(self, completed_workers: int, failed_workers: int, error: BaseException | str | None = None) -> None:
        with self._lock:
            self.status = 'failed'
            self.completed_workers = completed_workers
            self.failed_workers = failed_workers
            self.last_run_successful = False
            self.last_error = ''.join(traceback.format_exception(error)) if isinstance(error, BaseException) else error

    @property
    def is_healthy(self) -> bool:
        with self._lock:
            return self.status in {'running', 'healthy'} and self.expected_workers > 0 and self.failed_workers == 0

    @property
    def is_ready(self) -> bool:
        with self._lock:
            return (
                self.status == 'healthy'
                or (self.status == 'running' and self.last_run_successful)
            ) and self.expected_workers > 0 and self.failed_workers == 0


_thread_pool_health = _ThreadPoolHealth()


def get_thread_pool_health() -> dict[str, Any]:
    """
    Return the current in-process thread pool health snapshot.

    Returns:
        dict[str, Any]: thread pool health fields suitable for JSON serialization.
    """
    return _thread_pool_health.snapshot()


def mark_thread_pool_started(expected_workers: int) -> None:
    """
    Mark the sensor thread pool as started.

    Args:
        expected_workers (int): number of sensor worker futures submitted.
    """
    _thread_pool_health.started(expected_workers)


def mark_thread_pool_healthy(completed_workers: int) -> None:
    """
    Mark the sensor thread pool as healthy after a completed run.

    Args:
        completed_workers (int): number of sensor worker futures that completed.
    """
    _thread_pool_health.healthy(completed_workers)


def mark_thread_pool_failed(completed_workers: int = 0, failed_workers: int = 1, error: BaseException | str | None = None) -> None:
    """
    Mark the sensor thread pool as failed.

    Args:
        completed_workers (int): number of sensor worker futures that completed.
        failed_workers (int): number of failed sensor worker futures.
        error (BaseException | str | None): optional failure detail.
    """
    _thread_pool_health.failed(completed_workers, failed_workers, error)


def _health_response(healthy: bool) -> ResponseReturnValue:
    return (
        {
            'status': 'OK' if healthy else 'Failed',
            'thread_pool': get_thread_pool_health()
        },
        HTTPStatus.OK if healthy else HTTPStatus.SERVICE_UNAVAILABLE
    )


def create_healthcheck_api(app: Flask) -> None:
    """
    Create a healthcheck API for a Flask app instance.

    Args:
        app (Flask): Flask app instance.
    """

    log.debug(f'Creating healthcheck API')

    @app.get('/health')
    def healthcheck() -> ResponseReturnValue:
        """
        Quick unauthenticated healthcheck endpoint.

        Returns:
            ResponseReturnValue: an object with schema like

            {
                "status": "OK",
                "thread_pool": {}
            }
        """
        return _health_response(_thread_pool_health.is_healthy)

    @app.get('/ready')
    def readiness() -> ResponseReturnValue:
        """
        Quick unauthenticated readiness endpoint.

        Returns:
            ResponseReturnValue: an object with schema like

            {
                "status": "OK",
                "thread_pool": {}
            }
        """
        return _health_response(_thread_pool_health.is_ready)
