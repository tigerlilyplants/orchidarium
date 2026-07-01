"""
This module is responsible for the healthcheck API.
"""


import logging

from flask import Flask
from flask_cors import CORS


# cli = sys.modules['flask.cli']
# cli.show_server_banner = lambda *x: None  # type: ignore

log = logging.getLogger(__name__)

wz_log = logging.getLogger('werkzeug')
wz_log.disabled = True

app = Flask(__name__)
CORS(app)

log.debug(f'Set up CORS on app')


__all__ = [
    'app'
]


from orchidarium.api.health import create_healthcheck_api


create_healthcheck_api(app)