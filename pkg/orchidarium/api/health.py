"""
Serve healthcheck endpoints when in daemon mode.
"""


from http import HTTPStatus

import logging

from flask import Flask
from flask.typing import ResponseReturnValue

from orchidarium.runtime.health import (
    get_hardware_process_health,
    get_thread_pool_health,
    is_hardware_process_healthy,
    is_thread_pool_healthy,
    is_thread_pool_ready
)
from orchidarium.runtime.queue import get_point_backlog_health, is_point_backlog_ready


log = logging.getLogger(__name__)


__all__ = [
    'create_healthcheck_api'
]


def _health_response(healthy: bool) -> ResponseReturnValue:
    return (
        {
            'status': 'OK' if healthy else 'Failed',
            'hardware_process': get_hardware_process_health(),
            'point_backlog': get_point_backlog_health(),
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
                "hardware_process": {},
                "point_backlog": {},
                "status": "OK",
                "thread_pool": {}
            }
        """
        return _health_response(
            is_thread_pool_healthy()
            and is_hardware_process_healthy()
        )

    @app.get('/ready')
    def readiness() -> ResponseReturnValue:
        """
        Quick unauthenticated readiness endpoint.

        Returns:
            ResponseReturnValue: an object with schema like

            {
                "hardware_process": {},
                "point_backlog": {},
                "status": "OK",
                "thread_pool": {}
            }
        """
        return _health_response(
            is_thread_pool_ready()
            and is_hardware_process_healthy()
            and is_point_backlog_ready()
        )
