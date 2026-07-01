"""
Run the Orchidarium UI process.
"""


from __future__ import annotations

import logging

from setproctitle import setproctitle

from orchidarium.logging import configure_logging


log = logging.getLogger(__name__)


def run_ui_process() -> int:
    """
    Run the Qt/QML UI process.

    Returns:
        int: 0 if successful, 1 or another exit code, otherwise.
    """
    configure_logging()
    setproctitle('orchidarium-ui')
    log.info('Started UI process')

    try:
        from orchidarium.ui.entrypoint import run

        run()
    except KeyboardInterrupt:
        log.info('UI process interrupted')
        return 130
    except SystemExit as e:
        if isinstance(e.code, int):
            return e.code

        return 1 if e.code else 0
    except Exception:
        log.exception('UI process failed')
        return 1

    return 0
