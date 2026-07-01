"""
Serve sensor metadata endpoints when in daemon mode.
"""


from http import HTTPStatus

import logging

from attrs import define
from cattrs import unstructure
from flask import Flask
from flask.typing import ResponseReturnValue

from orchidarium.sensors import sensor_count

log = logging.getLogger(__name__)


__all__ = [
    'create_sensor_api',
]


@define
class _ActiveSensorsResponse:
    active_sensors: int


def create_sensor_api(app: Flask) -> None:
    """
    Create sensor metadata endpoints for a Flask app instance.

    Args:
        app (Flask): Flask app instance.
    """

    log.debug(f'Creating sensor API')

    @app.get('/sensors/active')
    def active_sensors() -> ResponseReturnValue:
        """
        Return the number of active sensor types.

        Returns:
            ResponseReturnValue: an object with schema like

            {
                "active_sensors": 0
            }
        """
        return (
            unstructure(
                _ActiveSensorsResponse(
                    active_sensors=sensor_count()
                )
            ),
            HTTPStatus.OK
        )
