"""
Provide an InfluxDB Publisher subclass to interact cleanly with the InfluxDB API to publish metrics.
"""


from __future__ import annotations

import logging

from time import sleep
from . import Publisher
from influxdb_client import InfluxDBClient, Point
from influxdb_client.rest import ApiException
from influxdb_client.client.write_api import SYNCHRONOUS
from orchidarium import env
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, List


__all__ = [
    'InfluxDBPublisher'
]

log = logging.getLogger(__name__)


class InfluxDBPublisher(Publisher):
    """
    An interface for managing connections to, as well as submitting data to, an InfluxDB instance.
    """

    def __init__(self):
        self._client: Any = None

    def connect(self) -> bool:
        # Guard against re-opening the connection.
        log.info(f'Opening connection to InfluxDB host at "{env["INFLUXDB_HOST"]}"')

        if not self._client:
            for i in range(3):
                try:
                    self._client = InfluxDBClient(
                        url=env['INFLUXDB_HOST'],
                        org=env['INFLUXDB_ORG'],
                        token=env['INFLUXDB_TOKEN'],
                        database=env['INFLUXDB_DATABASE']
                    )
                    break
                except ApiException as e:
                    log.warning(f'Connection attempt {i + 1} / 3 to InfluxDB host "{env["INFLUXDB_HOST"]}" failed: {e}')
                    sleep(1)
            else:
                log.error(f'Could not connect to InfluxDB host "{env["INFLUXDB_HOST"]}" after 3 attempts')

            log.info(f'Successfully opened connection to InfluxDB host "{env["INFLUXDB_HOST"]}"')
        else:
            log.warning(f'Connection to InfluxDB host {env["INFLUXDB_HOST"]} is already open')

        return bool(self._client)

    def __enter__(self) -> InfluxDBPublisher:
        self.connect()
        return self

    def __exit__(self, *args: Any) -> Any:
        self._client.close()

    def submit(self, datum: Any) -> bool:
        """


        Args:
            datum (Any): _description_

        Returns:
            bool: _description_
        """
        return True