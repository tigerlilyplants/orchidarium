"""
Run the Orchidarium hardware process.
"""


from __future__ import annotations

import logging

from setproctitle import setproctitle
from time import sleep

from orchidarium.logging import configure_logging
from orchidarium.runtime.health import mark_hardware_process_failed, mark_hardware_process_healthy, mark_hardware_process_started


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
    mark_hardware_process_started()
    log.info('Started hardware process')

    try:
        while True:
            mark_hardware_process_healthy()
            sleep(HARDWARE_IDLE_SLEEP_SECONDS)
    except KeyboardInterrupt:
        mark_hardware_process_failed(error='interrupted')
        log.info('Hardware process interrupted')
        return 130
    except Exception as e:
        mark_hardware_process_failed(error=e)
        log.exception('Hardware process failed')
        return 1
