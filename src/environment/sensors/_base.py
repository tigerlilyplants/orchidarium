from __future__ import annotations

import logging
import os

from pathlib import Path
from abc import abstractmethod, ABC
from typing import TYPE_CHECKING
from environment.lib.json import write_json
from environment import env

if TYPE_CHECKING:
    from environment.publishers._base import Publisher
    from typing import Literal


log = logging.getLogger(__name__)


class Sensor(ABC):

    def __init__(self, scale: Literal['F', 'C'] = 'F', default_temperature: float = 0.0) -> None:
        self.scale = scale
        self._col: bool = False
        self._pub: bool = False
        self._temperature = default_temperature
        self.cache()
        log.info(f'Instantiating thread for sensor "{self.__class__.__name__.lower().removesuffix("sensor")}"')

    @property
    def _collection(self) -> bool:
        return self._col

    @_collection.setter
    def _collection(self, value: bool) -> None:
        """
        Track whether or not a sensor has successfully collected its data.
        This property adds the side-effect of updating the cache on-disk.

        Args:
            value (bool): value to set the collection indicator to (True or False).
        """
        self._col = value
        self.cache()

    @property
    def _publication(self) -> bool:
        return self._pub

    @_publication.setter
    def _publication(self, value: bool) -> None:
        """
        Track whether or not a sensor has successfully collected its data.
        This property adds the side-effect of updating the cache on-disk.

        Args:
            value (bool): value to set the collection indicator to (True or False).
        """
        self._pub = value
        self.cache()

    @property
    def temperature(self) -> float:
        if self.scale == 'F':
            return self._temperature * 9 / 5 + 32.0
        elif self.scale == 'C':
            return self._temperature

    @temperature.setter
    def temperature(self, value: float) -> None:
        """
        Set the temperature (in Celsius).

        Args:
            value (float): temperature in Celsius.
        """
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
        self.collect()
        self.publish(publisher)

    def cache(self, file: Path = Path('healthcheck.json')) -> bool:
        """
        Write a cache to disk that healthchecks can pick up on to indicate the proper health.

        Args:
            file (Path): File to cache healthcheck results in. (default: Path('healthcheck.json'))

        Returns:
            bool: True if caching the result was successful; False otherwise.
        """
        return write_json(
            data={
                "healthcheck": {
                    "publish": self._publication,
                    "readout": self._collection
                }
            },
            path=Path(os.path.join(env['HEALTHCHECK_CACHE_PATH'], self.__class__.__name__.lower() + '_' + str(file)))
        )