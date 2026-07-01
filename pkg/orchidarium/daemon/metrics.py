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
from attrs import define
from cattrs import unstructure
from orchidarium.data import metric_queues
from orchidarium.logging import configure_logging
from orchidarium.publishers.influxdb import InfluxDBPublisher
from orchidarium.runtime.health import mark_thread_pool_failed, mark_thread_pool_healthy, mark_thread_pool_started
from orchidarium.runtime.state import update_runtime_state
from orchidarium.sensors import sensor_count, sensor_generator

if TYPE_CHECKING:
    from collections.abc import Callable
    from concurrent.futures import Future
    from orchidarium.publishers import Publisher


log = logging.getLogger(__name__)


@define(frozen=True)
class PublisherSpec:
    name: str
    publisher: Callable[[], Publisher]


PUBLISHER_SPECS = (
    PublisherSpec(
        name='influxdb',
        publisher=InfluxDBPublisher
    ),
)


for publisher_spec in PUBLISHER_SPECS:
    metric_queues.register(publisher_spec.name)


def _publish_queue_summary() -> None:
    """
    Publish the current queue summary for the API process.
    """
    update_runtime_state(queue=unstructure(metric_queues.activity_summary()))


def _publish_to_backend(publisher_spec: PublisherSpec) -> tuple[str, int]:
    """
    Drain one publisher-specific queue into its backend.

    Args:
        publisher_spec (PublisherSpec): publisher backend metadata.

    Returns:
        tuple[str, int]: publisher name and number of metrics published.
    """
    data_queue = metric_queues.queue(publisher_spec.name)

    with publisher_spec.publisher() as publisher:
        return publisher_spec.name, publisher.publish(data_queue)


def _publish_ready_queues() -> list[str]:
    """
    Publish all publisher queues that currently have backlog.

    Returns:
        list[str]: publisher failure details.
    """
    ready_publishers = []
    failures: list[str] = []

    for publisher_spec in PUBLISHER_SPECS:
        data_queue = metric_queues.queue(publisher_spec.name)

        if data_queue.empty:
            log.debug(f'Skipping publisher "{publisher_spec.name}" because its queue is empty')
            continue

        ready_publishers.append(publisher_spec)

    if not ready_publishers:
        log.debug('No publisher queues have backlog; skipping publisher threads')
        return failures

    with ThreadPoolExecutor(max_workers=len(ready_publishers), thread_name_prefix='publisher') as pool:
        publisher_threads: dict[Future[tuple[str, int]], str] = {
            pool.submit(_publish_to_backend, publisher_spec): publisher_spec.name
            for publisher_spec in ready_publishers
        }

        for thread in as_completed(publisher_threads):
            publisher_name = publisher_threads[thread]

            try:
                _, published_metrics = thread.result()
            except Exception as e:
                log.exception(f'Publisher "{publisher_name}" failed')
                failures.append(f'{publisher_name}: {e}')
            else:
                log.debug(f'Published {published_metrics} metrics to "{publisher_name}"')

    return failures


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
            with ThreadPoolExecutor(max_workers=_worker_count, thread_name_prefix='sensor') as pool:
                log.debug(f'Started {_worker_count} sensor threads')

                # Build a list of thread futures.
                threads: dict[Future[None], str] = {}
                sensor_failures: list[str] = []

                for sensor in sensor_generator():
                    sensor_name = sensor.__name__
                    threads[
                        pool.submit(
                            partial(
                                sensor(),
                                metric_queues
                            )
                        )
                    ] = sensor_name

                for thread in as_completed(threads):
                    try:
                        thread.result()
                    except Exception as e:
                        log.exception(f'Sensor "{threads[thread]}" failed')
                        sensor_failures.append(f'{threads[thread]}: {e}')
            _publish_queue_summary()
            publisher_failures = _publish_ready_queues()
            _publish_queue_summary()

            if sensor_failures or publisher_failures:
                mark_thread_pool_failed(
                    completed_workers=len(threads) - len(sensor_failures),
                    failed_workers=len(sensor_failures),
                    error='\n'.join(sensor_failures + publisher_failures)
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
