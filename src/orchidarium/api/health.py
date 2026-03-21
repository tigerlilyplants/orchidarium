"""
Serve a healthcheck endpoint when in daemon mode.
"""


from http import HTTPStatus
from flask import Response
from flask import Flask
from pathlib import Path
from orchidarium.lib.json import read_json
from orchidarium.support import sensor_count
from orchidarium import env

import logging


log = logging.getLogger(__name__)


__all__ = [
    'create_healthcheck_api'
]


_FAILED = Response(
    {
        'status': 'Failed'
    },
    status=HTTPStatus.SERVICE_UNAVAILABLE,
    mimetype='application/json'
)

_OK = Response(
    {
        'status': 'OK'
    },
    status=HTTPStatus.OK,
    mimetype='application/json'
)


def create_healthcheck_api(app: Flask) -> None:
    """
    Create a healthcheck API for a Flask app instance.

    Args:
        app (Flask): Flask app instance.
    """

    log.debug(f'Creating healthcheck API')

    @app.get('/health')
    def healthcheck() -> Response:
        """
        Quick unauthenticated healthcheck endpoint.

        Returns:
            Response: an object with schema like

            {
                "status": "OK"
            }
        """
        if len(list(Path(env['HEALTHCHECK_CACHE_PATH']).iterdir())) == sensor_count():
            for sensor_health_result_f in Path(env['HEALTHCHECK_CACHE_PATH']).iterdir():
                if not read_json(path=sensor_health_result_f)['healthcheck']['readout']:
                    return _FAILED
            else:
                if len(list(Path(env['HEALTHCHECK_CACHE_PATH']).iterdir())) != 0:
                    return _OK
                else:
                    return _FAILED
        else:
            return _FAILED

    @app.get('/ready')
    def readiness() -> Response:
        """
        Quick unauthenticated readiness endpoint.

        Returns:
            Response: an object with schema like

            {
                "status": "OK"
            }
        """
        if len(list(Path(env['HEALTHCHECK_CACHE_PATH']).iterdir())) == sensor_count():
            for sensor_health_result_f in Path(env['HEALTHCHECK_CACHE_PATH']).iterdir():
                if not ((_jsn := read_json(path=sensor_health_result_f))['healthcheck']['publish']) and not _jsn['healthcheck']['readout']:
                    return _FAILED
            else:
                if len(list(Path(env['HEALTHCHECK_CACHE_PATH']).iterdir())) != 0:
                    return _OK
                else:
                    return _FAILED
        else:
            return _FAILED