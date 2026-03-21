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
    from orchidarium.publishers import Publisher


log = logging.getLogger(__name__)


class SoilSensor(Sensor):

    def collect(self) -> bool:
        self._collection = False

        return False

    def publish(self, publisher: Publisher) -> bool:
        ...
        self._publication = True
        return True