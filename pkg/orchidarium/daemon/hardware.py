"""
Run the Orchidarium hardware process.
"""


from __future__ import annotations

import logging

from setproctitle import setproctitle
from time import sleep

from orchidarium.logging import configure_logging


log = logging.getLogger(__name__)


HARDWARE_IDLE_SLEEP_SECONDS = 1.0


def run_hardware_process() -> int:
    """
    Run the hardware control process.

    Returns:
        int: 0 if successful, 1 or another exit code, otherwise.
    """
    configure_logging()
    setproctitle('orchidarium-hardware')
    log.info('Started hardware process')

    try:
        while True:
            sleep(HARDWARE_IDLE_SLEEP_SECONDS)
    except KeyboardInterrupt:
        log.info('Hardware process interrupted')
        return 130
    except Exception:
        log.exception('Hardware process failed')
        return 1
