"""
Serve data queue metadata endpoints when in daemon mode.
"""


from http import HTTPStatus

import logging

from cattrs import unstructure
from flask import Flask
from flask.typing import ResponseReturnValue

from orchidarium.data import metric_queue
from orchidarium.runtime.state import read_runtime_state

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
        queue_summary = read_runtime_state().get('queue')

        if not isinstance(queue_summary, dict):
            queue_summary = unstructure(metric_queue.activity_summary())

        return (
            queue_summary,
            HTTPStatus.OK
        )
