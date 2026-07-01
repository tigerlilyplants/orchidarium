"""
ABC that defines the API for publishing metrics.
"""


from __future__ import annotations

from abc import abstractmethod, ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class Publisher(ABC):

    @abstractmethod
    def connect(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def submit(self, datum: Any) -> bool:
        raise NotImplementedError