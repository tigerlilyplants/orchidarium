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
from orchidarium.data.queue import MetricDatum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


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
        self._write_api: Any = None

    def connect(self) -> bool:
        # Guard against re-opening the connection.
        log.info(f'Opening connection to InfluxDB host at "{env["INFLUXDB_HOST"]}"')

        if not self._client:
            for i in range(3):
                try:
                    self._client = InfluxDBClient(
                        url=self._url,
                        org=env['INFLUXDB_ORG'],
                        token=env['INFLUXDB_TOKEN']
                    )
                    self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
                    break
                except ApiException as e:
                    log.warning(f'Connection attempt {i + 1} / 3 to InfluxDB host "{env["INFLUXDB_HOST"]}" failed: {e}')
                    sleep(1)
            else:
                log.error(f'Could not connect to InfluxDB host "{env["INFLUXDB_HOST"]}" after 3 attempts')
                return False

            log.info(f'Successfully opened connection to InfluxDB host "{env["INFLUXDB_HOST"]}"')
        else:
            log.warning(f'Connection to InfluxDB host {env["INFLUXDB_HOST"]} is already open')

        return bool(self._client)

    def __enter__(self) -> InfluxDBPublisher:
        self.connect()
        return self

    def __exit__(self, *args: Any) -> Any:
        if self._write_api:
            self._write_api.close()

        if self._client:
            self._client.close()

    @property
    def _url(self) -> str:
        if '://' in env['INFLUXDB_HOST']:
            return env['INFLUXDB_HOST']

        return f'http://{env["INFLUXDB_HOST"]}'

    def submit(self, datum: MetricDatum) -> bool:
        """
        Submit one metric datum to InfluxDB.

        Args:
            datum (MetricDatum): metric datum to submit.

        Returns:
            bool: True when the write was accepted by the InfluxDB client.
        """
        if not self._write_api and not self.connect():
            return False

        assert self._write_api is not None

        self._write_api.write(
            bucket=env['INFLUXDB_DATABASE'],
            org=env['INFLUXDB_ORG'],
            record=self._to_point(datum)
        )
        return True

    def _to_point(self, datum: MetricDatum) -> Point:
        point = Point(datum.measurement)

        for key, tag_value in datum.tags.items():
            point.tag(key, tag_value)

        for key, field_value in datum.fields.items():
            point.field(key, field_value)

        point.time(datum.timestamp)
        return point
