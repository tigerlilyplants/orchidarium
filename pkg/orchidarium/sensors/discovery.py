from __future__ import annotations

import inspect

from collections.abc import Generator
from functools import lru_cache

from ._base import Sensor


def _sensor_types() -> Generator[type[Sensor]]:
    import orchidarium.sensors

    for _, obj in inspect.getmembers(orchidarium.sensors, inspect.isclass):
        if issubclass(obj, Sensor) and obj is not Sensor:
            yield obj


@lru_cache(maxsize=1)
def sensor_count() -> int:
    """
    Return the number of supported sensors.

    Returns:
        int: the number of supported sensors [0-inf).
    """
    return sum(1 for _ in _sensor_types())


def sensor_generator() -> Generator[type[Sensor]]:
    """
    Iterate over sensor types with this generator.

    Yields:
        type[Sensor]: A Sensor implementation callable.
    """
    yield from _sensor_types()
