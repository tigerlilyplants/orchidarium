"""
Run the Orchidarium API process.
"""


from __future__ import annotations

import logging

from flask import cli
from setproctitle import setproctitle

from orchidarium import env
from orchidarium.api import app
from orchidarium.logging import configure_logging


log = logging.getLogger(__name__)


def run_api_process() -> int:
    """
    Run the Flask API process.

    Returns:
        int: 0 if successful, 1 or another exit code, otherwise.
    """
    configure_logging()
    setproctitle('orchidarium-api')
    log.info('Started API process')

    try:
        cli.show_server_banner = lambda *args: None

        app.run(
            port=int(env['HEALTHCHECK_PORT']),
            debug=False,
            use_debugger=False,
            use_reloader=False
        )
    except KeyboardInterrupt:
        log.info('API process interrupted')
        return 130
    except Exception:
        log.exception('API process failed')
        return 1

    return 0
