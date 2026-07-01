from __future__ import annotations

import logging

from abc import abstractmethod, ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orchidarium.publishers._base import Publisher
    from typing import Literal


log = logging.getLogger(__name__)


class Sensor(ABC):

    def __init__(self, scale: Literal['F', 'C'] = 'F', default_temperature: float = 0.0) -> None:
        self.scale = scale
        self._col: bool = False
        self._pub: bool = False
        self._temperature = default_temperature
        log.info(f'Instantiating thread for sensor "{self.__class__.__name__.lower().removesuffix("sensor")}"')

    @property
    def _collection(self) -> bool:
        return self._col

    @_collection.setter
    def _collection(self, value: bool) -> None:
        """
        Track whether or not a sensor has successfully collected its data.

        Args:
            value (bool): value to set the collection indicator to (True or False).
        """
        self._col = value

    @property
    def _publication(self) -> bool:
        return self._pub

    @_publication.setter
    def _publication(self, value: bool) -> None:
        """
        Track whether or not a sensor has successfully collected its data.

        Args:
            value (bool): value to set the collection indicator to (True or False).
        """
        self._pub = value

    @property
    def temperature(self) -> float:
        if self.scale == 'F':
            return self._temperature * 9 / 5 + 32.0
        elif self.scale == 'C':
            return self._temperature

    @temperature.setter
    def temperature(self, value: float) -> None:
        self._temperature = value

    @abstractmethod
    def collect(self) -> bool:
        """
        Collect data with the configured sensor.

        Raises:
            NotImplementedError: due to this being an abstract method.

        Returns:
            bool: True if the data collection was successful, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def publish(self, publisher: Publisher) -> bool:
        """
        Publish data to a Publisher.

        Args:
            publisher (Publisher): A Publisher that defines a 'publish_datapoint'-method.

        Raises:
            NotImplementedError: due to this being an abstract method.

        Returns:
            bool: True if data publication was successful, False otherwise.
        """
        raise NotImplementedError

    def __call__(self, publisher: Publisher) -> None:
        """
        Make Sensors callable, wherein data collection and publication is carried out.
        """
        if not self.collect():
            raise RuntimeError(f'Failed to collect data for sensor "{self.__class__.__name__}"')

        if not self.publish(publisher):
            raise RuntimeError(f'Failed to publish data for sensor "{self.__class__.__name__}"')
