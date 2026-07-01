"""
Serve healthcheck endpoints when in daemon mode.
"""


from http import HTTPStatus

import logging

from flask import Flask
from flask.typing import ResponseReturnValue

from orchidarium.runtime.health import get_thread_pool_health, is_thread_pool_healthy, is_thread_pool_ready


log = logging.getLogger(__name__)


__all__ = [
    'create_healthcheck_api'
]


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
        return _health_response(is_thread_pool_healthy())

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
        return _health_response(is_thread_pool_ready())
