"""
Run the Orchidarium metrics process.
"""


from __future__ import annotations

import logging

from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from setproctitle import setproctitle
from time import sleep
from typing import TYPE_CHECKING

from orchidarium import env
from cattrs import unstructure
from orchidarium.data import metric_queue
from orchidarium.logging import configure_logging
from orchidarium.publishers.influxdb import InfluxDBPublisher
from orchidarium.runtime.health import mark_thread_pool_failed, mark_thread_pool_healthy, mark_thread_pool_started
from orchidarium.runtime.state import update_runtime_state
from orchidarium.sensors import sensor_count, sensor_generator

if TYPE_CHECKING:
    from concurrent.futures import Future


log = logging.getLogger(__name__)


def _publish_queue_summary() -> None:
    """
    Publish the current queue summary for the API process.
    """
    update_runtime_state(queue=unstructure(metric_queue.activity_summary()))


def run_metrics_process() -> int:
    """
    Run the metrics collection and publication process.

    Returns:
        int: 0 if successful, 1 or another exit code, otherwise.
    """
    configure_logging()
    _ret_code = 0

    setproctitle('orchidarium-metrics')
    _publish_queue_summary()

    try:
        while True:
            _worker_count = sensor_count()
            mark_thread_pool_started(expected_workers=_worker_count)
            _publish_queue_summary()

            if _worker_count < 1:
                mark_thread_pool_failed(error='No enabled sensors discovered')
                sleep(int(env['INTERVAL']))
                continue

            # Start as many threads as there are sensors.
            with ThreadPoolExecutor(max_workers=_worker_count, thread_name_prefix='sensor') as pool, InfluxDBPublisher() as publisher:
                log.debug(f'Started {_worker_count} threads and opened a connection to a publisher')

                # Build a list of thread futures.
                threads: dict[Future[None], str] = {}
                failures: list[str] = []

                for sensor in sensor_generator():
                    sensor_name = sensor.__name__
                    threads[
                        pool.submit(
                            partial(
                                sensor(),
                                metric_queue
                            )
                        )
                    ] = sensor_name

                for thread in as_completed(threads):
                    try:
                        thread.result()
                    except Exception as e:
                        log.exception(f'Sensor "{threads[thread]}" failed')
                        failures.append(f'{threads[thread]}: {e}')
                else:
                    _publish_queue_summary()
                    published_metrics = publisher.publish(metric_queue)
                    log.debug(f'Published {published_metrics} metrics to InfluxDB')
                    _publish_queue_summary()

                    if failures:
                        mark_thread_pool_failed(
                            completed_workers=len(threads) - len(failures),
                            failed_workers=len(failures),
                            error='\n'.join(failures)
                        )
                        _ret_code = 1
                    else:
                        mark_thread_pool_healthy(completed_workers=len(threads))
                        _ret_code = 0

            sleep(int(env['INTERVAL']))
    except Exception as e:
        _ret_code = 1
        mark_thread_pool_failed(error=e)
        _publish_queue_summary()
        log.error(e)

    return _ret_code
