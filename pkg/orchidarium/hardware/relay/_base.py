"""
Define relay interfaces.
"""


from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable


class BaseRelay(ABC, Iterable['BaseSwitch']):

    @abstractmethod
    def state(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def state_map(self) -> dict[int, bool]:
        raise NotImplementedError

    @abstractmethod
    def open(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def on(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def toggle(self, count: int = 1, delay: float = 0.0) -> None:
        raise NotImplementedError


class BaseSwitch(ABC):

    @abstractmethod
    def block(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def on(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def toggle(self, count: int = 1, delay: float = 0.0) -> None:
        raise NotImplementedError
