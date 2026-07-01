"""
Define a soil sensor type that encapsulates the logic for interacting with our soil sensor.
"""


from __future__ import annotations

import logging
import re

from orchidarium.sensors import Sensor
from orchidarium.lib.bus import InterfaceClaim, read
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orchidarium.data.queue import MetricQueueSink


log = logging.getLogger(__name__)


class SoilSensor(Sensor):
    enabled = False

    def collect(self) -> bool:
        self._collection = False

        return False

    def publish(self, data_queue: MetricQueueSink) -> bool:
        ...
        self._publication = True
        return True
