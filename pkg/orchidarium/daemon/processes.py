"""
Supervise Orchidarium daemon processes.
"""


from __future__ import annotations

import logging

from collections.abc import Callable
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from setproctitle import setproctitle

from attrs import define

from orchidarium.logging import configure_logging


log = logging.getLogger(__name__)


@define(frozen=True)
class ProcessSpec:
    name: str
    target: Callable[[], int]


def metrics_process_target() -> int:
    """
    Run the metrics process target.

    Returns:
        int: process exit code.
    """
    from orchidarium.daemon.metrics import run_metrics_process as _run_metrics_process

    return _run_metrics_process()


def hardware_process_target() -> int:
    """
    Run the hardware process target.

    Returns:
        int: process exit code.
    """
    from orchidarium.daemon.hardware import run_hardware_process as _run_hardware_process

    return _run_hardware_process()


PROCESS_SPECS = (
    ProcessSpec(
        name='metrics',
        target=metrics_process_target
    ),
    ProcessSpec(
        name='hardware',
        target=hardware_process_target
    ),
)


def run() -> int:
    """
    Start and supervise Orchidarium child processes.

    Returns:
        int: 0 if successful, 1 or another exit code, otherwise.
    """
    configure_logging()
    setproctitle('orchidarium')

    if not PROCESS_SPECS:
        log.warning('No daemon processes configured')
        return 0

    futures: dict[Future[int], ProcessSpec] = {}
    executor = ProcessPoolExecutor(max_workers=len(PROCESS_SPECS))

    try:
        for process_spec in PROCESS_SPECS:
            futures[executor.submit(process_spec.target)] = process_spec
            log.info(f'Started daemon process "{process_spec.name}"')

        for future in as_completed(futures):
            process_spec = futures[future]

            try:
                exit_code = future.result()
            except Exception:
                log.exception(f'Daemon process "{process_spec.name}" failed')
                return 1

            if exit_code == 0:
                log.info(f'Daemon process "{process_spec.name}" exited cleanly')
            else:
                log.error(f'Daemon process "{process_spec.name}" exited with code {exit_code}')

            return exit_code
    except KeyboardInterrupt:
        log.info('Daemon interrupted; shutting down child processes')
        return 130
    finally:
        for future in futures:
            future.cancel()

        executor.shutdown(wait=False, cancel_futures=True)

    return 0
