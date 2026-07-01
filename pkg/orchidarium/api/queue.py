"""
Serve data queue metadata endpoints when in daemon mode.
"""


from http import HTTPStatus

import logging

from flask import Flask
from flask.typing import ResponseReturnValue

from orchidarium.runtime.queue import get_queue_summary

log = logging.getLogger(__name__)


__all__ = [
    'create_queue_api',
]


def create_queue_api(app: Flask) -> None:
    """
    Create queue metadata endpoints for a Flask app instance.

    Args:
        app (Flask): Flask app instance.
    """

    log.debug(f'Creating queue API')

    @app.get('/queue/backlog')
    def queue_backlog() -> ResponseReturnValue:
        """
        Return queue backlog and rolling activity summary.

        Returns:
            ResponseReturnValue: an object with queue backlog metadata.
        """
        return (
            get_queue_summary(),
            HTTPStatus.OK
        )
