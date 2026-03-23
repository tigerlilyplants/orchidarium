from __future__ import annotations

import logging

from functools import wraps
from smbus import SMBus
from time import sleep
from contextlib import AbstractContextManager
from collections.abc import Iterable
from datetime import datetime, timedelta
from random import random
from threading import Lock
from cachetools import LRUCache
from orchidarium import env
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import (
        List,
        Final,
        Callable,
        Any,
        Dict
    )


__all__ = [
    'Relay',
    'Switch'
]

log = logging.getLogger(__name__)

# Registers - for 16/i2c relay, there are 2xins and 2xouts, as well as two codes to reset the relays, and then an i2c address.
ADDR = 0x20
IN0  = 0x00
IN1  = 0x01
OUT0 = 0x02
OUT1 = 0x03
CFG0 = 0x06
CFG1 = 0x07


def _hardware_retry(retries: int = 3) -> Callable[[bool], bool]:
    """
    Check the state against the expected state

    Args:
        retries (int): number of attempts to make to switch the state of the relay switch.

    Returns:
        Callable[[bool], bool]: The wrapped function.
    """
    def retry(f: Callable[[bool], bool]) -> Callable[[bool], bool]:
        @wraps(f)
        def new_f(state: bool) -> bool:
            for _ in range(retries):
                try:
                    if (res := f(state)):
                        return res
                    else:
                        log.error(f'Function "{f.__name__}" returned a negative result, retrying')
                except IOError as e:
                    log.error(e)
            else:
                log.error(f'Attempt {retries} / {retries}: failed to set state of relay')
                return False
        return new_f
    return retry


class Relay(AbstractContextManager, Iterable):

    def __init__(self, size: int = 16, bus: int = 1, ro: bool = False) -> None:
        assert size <= 16
        self.size: Final[int] = size
        self.bus: Final[int] = bus
        self._smbus: SMBus | None = None
        self._switches: List[Switch] = []
        self._state: int = 0xFFFF
        self._lock: Lock = Lock()
        self.ro = ro

    def __iter__(self):
        return iter(self._switches)

    def __enter__(self) -> Relay:
        if self.open():
            if not self.ro:
                self._initialize_relay()
            return self

    def state(self, as_int: bool = True) -> Dict[int, bool] | int:
        """
        Get the current state of the whole switch.

        Args:
            as_int (bool): convert the return value to an integer bitmask.

        Returns:
            Dict[int, bool] | int: if as_int is False, return a dictionary. Otherwise, return an integer representing the state.
        """
        if as_int:
            mask = 0
            for i, relay in enumerate(self):
                if relay.get():
                    mask |= (1 << i)
            return mask
        else:
            return {i: relay.get() for i, relay in enumerate(self)}

    def open(self) -> bool:
        if self._smbus is None:
            self._smbus = SMBus(self.bus)
        self._switches = [
            Switch(
                self.bus,
                i,
                self._lock,
            ) for i in range(self.size)
        ]
        return True

    def close(self) -> None:
        self._smbus.close()
        self._smbus = None

    def __exit__(self, *args):
        self.close()

    def _initialize_relay(self) -> None:
        """
        Initialize a relay once when a connection is established.
        """
        self.bus.write_byte_data(self.ADDR, self.CFG0, 0x00)
        self.bus.write_byte_data(self.ADDR, self.CFG1, 0x00)

        if any(relay.get() for relay in self):
            for i, relay in enumerate(self):
                if not self.ro:
                    relay.reset(self.state())
                else:
                    log.warning(f'Skipping resetting relay switch {i + 1} due to relay connection being RO')


class Switch:

    def __init__(self, bus: SMBus, number: int, lock: Lock, switch_bounce_delay: float = 0.25, ro: bool = False):
        self.number = number
        assert switch_bounce_delay > 0
        self.switch_bounce_delay = timedelta(seconds=switch_bounce_delay)
        self._last_state_change = datetime.now()
        self._bus: SMBus = bus
        self._lock: Lock = lock
        self.ro: bool = ro

    def block(self) -> None:
        """
        Public interface call that blocks until this Switch's state can be changed again.
        """
        if (_difference := datetime.now() - self.switch_bounce_delay) > self._last_state_change:
            sleep(_difference + self.switch_bounce_delay / 10)

    def _state_change_block(self) -> None:
        """
        Adds a small, random interval of time to each switch to avoid any resonance in the case.
        """
        if (_difference := datetime.now() - self.switch_bounce_delay) > self._last_state_change:
            sleep(_difference + round(random() % self.switch_bounce_delay / 10, 4))

    @property
    @LRUCache(maxsize=1)
    def ro_register(self) -> int:
        """
        Get the proper read-only register number.

        Returns:
            int: number of the register.
        """
        if self.number < 8:
            return IN0
        else:
            return IN1

    @property
    @LRUCache(maxsize=1)
    def rw_register(self) -> int:
        """
        Get the proper read/write-register over which to write bits.

        Returns:
            int: number of the register.
        """
        if self.number < 8:
            return OUT0
        else:
            return OUT1

    @_hardware_retry()
    def get(self) -> bool:
        """
        Get the current state of the relay (whether it's on or off).

        Returns:
            bool: True if on, False otherwise.
        """
        with self._lock:
            val = self._bus.read_byte_data(ADDR, self.ro_register)

        return ((val >> self.number) & 1 if self.number < 8 else (val >> (self.number - 8)) & 1) == 1

    def toggle(self, relay_state: int, count: int = 1, delay: float = 0.0) -> None:
        """
        Get current state of the relay and switch it to the other state.
        """
        for i in range(count):
            if self.get():
                self.reset(relay_state=relay_state)
            else:
                self.on(relay_state=relay_state)

            if count > 1 and i < count - 1 and delay > 0:
                sleep(delay)

    def on(self, relay_state: int) -> None:
        """
        Turn the relay on.
        """
        self._state_change_block()
        self._set(state=True, relay_state=relay_state)

    def reset(self, relay_state: Dict[int, bool]) -> None:
        """
        Turn off the relay.
        """
        self._state_change_block()
        self._set(state=False, relay_state=relay_state)

    @_hardware_retry()
    def _set(self, state: bool, relay_state: int) -> bool:
        """
        Set the state of the relay to be either on (True) or off (False).

        Args:
            state (bool): State to set the relay to.
            relay_state (int): Full 16-bit relay state mask.

        Returns:
            bool: True if setting the value was successful, False otherwise.
        """
        if self.ro:
            log.warning(f'Skipping relay switch {self.number + 1} update due to relay connection being RO')
            return None

        with self._lock:
            mask = 1 << self.number

            if state:
                relay_state |= mask
            else:
                relay_state &= ~mask

            state0 = relay_state & 0xFF
            state1 = (relay_state >> 8) & 0xFF

            if self.number < 8:
                self._bus.write_byte_data(ADDR, OUT0, state0)
            else:
                self._bus.write_byte_data(ADDR, OUT1, state1)

            return True


if __name__ == '__main__':
    relay = Relay()
    for switch in relay:
        for _ in range(2):
            switch.toggle()
    relay[0].toggle()