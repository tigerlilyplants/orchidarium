"""
Define a mock sensor for tests and local development.
"""


from __future__ import annotations

from random import uniform
from typing import TYPE_CHECKING

from orchidarium.data.queue import MetricDatum
from orchidarium.sensors import Sensor

if TYPE_CHECKING:
    from orchidarium.data.queue import DataQueue


class MockSensor(Sensor):
    enabled = True

    MIN_VALUE = 60.0
    MAX_VALUE = 80.0

    def __init__(self) -> None:
        super().__init__()
        self._value = 0.0

    @property
    def value(self) -> float:
        return self._value

    def collect(self) -> bool:
        self._value = uniform(self.MIN_VALUE, self.MAX_VALUE)
        self._collection = True
        return True

    def publish(self, data_queue: DataQueue) -> bool:
        data_queue.append(
            MetricDatum(
                measurement='environment',
                tags={
                    'sensor': self.__class__.__name__.lower().removesuffix('sensor'),
                },
                fields={
                    'mock_value': self._value,
                }
            )
        )
        self._publication = True
        return True
