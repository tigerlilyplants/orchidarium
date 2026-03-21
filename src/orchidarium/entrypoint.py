"""
Read temperature and humidity data from USB sensor in my Orchidarium.
"""


from __future__ import annotations

import logging
import sys
import traceback

from typing import TYPE_CHECKING
from time import sleep
from functools import partial
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
from orchidarium.publishers.influxdb import InfluxDBPublisher
from orchidarium.api import app
from orchidarium.support import sensor_count, sensor_generator
from orchidarium import env

if TYPE_CHECKING:
    from typing import List
    from concurrent.futures import Future


log = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG if env['DEBUG'] != '' else logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)


## Main


def daemon() -> int:
    """
    Daemon loop.

    Returns:
        int: 0 if successful, 1 or another exit code, otherwise.
    """
    _ret_code = 0

    # Start the healthcheck and other APIs in a separate thread off our main process as a daemon thread.
    _main_process_daemon_threads: List[Thread] = [
        # This needs to be rewritten ~
        # https://oneuptime.com/blog/post/2025-01-06-python-health-checks-kubernetes/view
        # Thread(
        #     target=partial(
        #         app.run,
        #         port=int(env['HEALTHCHECK_PORT']),
        #         debug=bool(env['DEBUG']),
        #         use_reloader=False
        #     ),
        #     # Do not block upon start().
        #     daemon=True,
        #     name='healthcheck'
        # ),
    ]

    for _dthread in _main_process_daemon_threads:
        _dthread.start()
        log.debug(f'Started thread "{_dthread.name}": {_dthread.is_alive()}')

    try:
        while True:
            # Start as many threads as there are sensors.
            with ThreadPoolExecutor(max_workers=sensor_count(), thread_name_prefix='sensor') as pool, InfluxDBPublisher() as publisher:
                log.debug(f'Started {sensor_count()} threads and opened a connection to a publisher')

                # Build a list of thread futures.
                threads: List[Future] = []

                for sensor in sensor_generator():
                    threads.append(
                        pool.submit(
                            partial(
                                sensor(),
                                publisher
                            )
                        )
                    )

                for thread in as_completed(threads):
                    try:
                        thread.result()
                    except Exception:
                        log.error(f'Thread {thread} failed. Full traceback: {traceback.format_exc()}')

                        for _thread in threads:
                            if _thread is not thread:
                                log.debug(f'Terminating thread "{_thread}"')
                                _thread.cancel()
                                log.debug(f'Thread "{_thread}" terminated successfully')

                        _ret_code = 1
                        break
                else:
                    _ret_code = 0

            sleep(int(env['INTERVAL']))
    except Exception as e:
        _ret_code = 1
        log.error(e)

    for _dthread in _main_process_daemon_threads:
        _dthread.join(timeout=5)

    return _ret_code


def cli() -> None:
    sys.exit(
        daemon()
    )


if __name__ == '__main__':
    cli()