from __future__ import annotations

import logging

from smbus import SMBus
from time import sleep
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from collections.abc import Iterable
from datetime import datetime, timedelta
from random import random
from threading import Lock
# from orchidarium import env
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import (
        List,
        Final,
        Dict
    )


__all__ = [
    'Relay',
    'Switch',
    'IN0',
    'IN1',
    'OUT0',
    'OUT1',
    'CFG0',
    'CFG1'
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


class _Relay(ABC):

    @abstractmethod
    def state(self) -> int | Dict[int, bool]:
        raise NotImplementedError

    @abstractmethod
    def open(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

class _Switch(ABC):

    @abstractmethod
    def block(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def toggle(self, relay_state: int, count: int = 1, delay: float = 0.0) -> None:
        raise NotImplementedError

    @abstractmethod
    def reset(self, relay_state: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def _get(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def _set(self, state: bool, relay_state: int) -> bool:
        raise NotImplementedError


class Relay(_Relay, Iterable, AbstractContextManager):

    def __init__(self, size: int = 16, bus: int = 1, ro: bool = False) -> None:
        assert size <= 16
        self.size: Final[int] = size
        self.bus: Final[int] = bus
        self._smbus: SMBus | None = None
        self._switches: List[Switch] = []
        self._state: int = 0xFFFF
        self._lock: Lock = Lock()
        self.ro = ro

    def __getitem__(self, key: int) -> Switch:
        """
        Get a switch from an instance of this object.

        Args:
            key (int): the key-indexed item to retrieve.

        Returns:
            Switch: the switch object to retrieve.
        """
        return self._switches[key]

    def __iter__(self):
        return iter(self._switches)

    def __enter__(self) -> Relay:
        if self.open():
            return self
        else:
            raise IOError(f'Could not open connection to relay')

    def state(self) -> int:
        """
        Get the current state of the whole switch.

        Returns:
            int: the state of the switch is determined by an integer.
        """
        mask = 0
        for i, relay in enumerate(self):
            if relay.get():
                mask |= (1 << i)
        return mask

    def state_map(self) -> Dict[int, bool]:
        """
        Get a dictionary representing the state of all the relays.

        Returns:
            Dict[int, bool]: A map of indexed relays and their states (True or False for open / closed).
        """
        return {i: relay.get() for i, relay in enumerate(self)}

    def open(self) -> bool:
        if self._smbus is None:
            self._smbus = SMBus(self.bus)

        self._switches = [
            Switch(
                self._smbus,
                i,
                self._lock,
            ) for i in range(self.size)
        ]

        if not self.ro:
            self._initialize_relay()

        return True

    def close(self) -> None:
        if self._smbus is not None:
            self._smbus.close()
            self._smbus = None

    def __exit__(self, *args):
        self.close()

    def _initialize_relay(self) -> None:
        """
        Initialize a relay once when a connection is established.
        """
        if self._smbus is not None:
            self._smbus.write_byte_data(ADDR, CFG0, 0x00)
            self._smbus.write_byte_data(ADDR, CFG1, 0x00)

            if any(relay.get() for relay in self):
                for i, relay in enumerate(self):
                    if not self.ro:
                        relay.reset(self.state())
                    else:
                        log.warning(f'Skipping resetting relay switch {i + 1} due to relay connection being RO')
        else:
            log.error(f'Open connection to relay prior to initialization.')
            return


class Switch(_Switch):

    def __init__(self, bus: SMBus, number: int, lock: Lock, switch_bounce_delay: float = 0.25, ro: bool = False):
        self.number = number
        assert switch_bounce_delay > 0
        self.switch_bounce_delay = timedelta(seconds=switch_bounce_delay)
        self._last_state_change = datetime.now()
        self._smbus: SMBus = bus
        self._lock: Lock = lock
        self.ro: bool = ro

    def block(self) -> None:
        """
        Public interface call that blocks until this Switch's state can be changed again.
        """
        if (datetime.now() - self.switch_bounce_delay) > self._last_state_change:
            sleep((datetime.now() - self._last_state_change).seconds + self.switch_bounce_delay.seconds / 10)

    def _state_change_block(self) -> None:
        """
        Adds a small, random interval of time to each switch to avoid any resonance in the case.
        """
        if (datetime.now() - self.switch_bounce_delay) > self._last_state_change:
            sleep((datetime.now() - self._last_state_change).seconds + round(random() % (self.switch_bounce_delay.microseconds / 1e-6) / 10, 4))
        return None

    @property
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
    def wo_register(self) -> int:
        """
        Get the proper read/write-register over which to write bits.

        Returns:
            int: number of the register.
        """
        if self.number < 8:
            return OUT0
        else:
            return OUT1

    def get(self) -> bool:
        """
        Get the current state of the relay (whether it's on or off).

        Returns:
            bool: True if on, False otherwise.
        """
        return self._get()

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

    def reset(self, relay_state: int) -> None:
        """
        Turn off the relay.
        """
        self._state_change_block()
        self._set(state=False, relay_state=relay_state)

    def _get(self) -> bool:
        """
        Similar to '_set', get the value of this relay over this bus.

        Returns:
            bool: True if getting the
        """
        i = 2
        while True:
            try:
                # Attempt to acquire a lock with a timeout that loops with delays.
                self._lock.acquire(timeout=self.switch_bounce_delay.seconds)

                if self._lock.locked():
                    val = self._smbus.read_byte_data(ADDR, self.ro_register)

                    return ((val >> self.number) & 1 if self.number < 8 else (val >> (self.number - 8)) & 1) == 1
                else:
                    log.debug(f'Unable to acquire lock, retry {i} / ∞')
                    self._state_change_block()
                    i += 1
            finally:
                self._lock.release_lock()

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
            return False

        while True:
            try:
                with self._lock:
                    mask = 1 << self.number

                    if state:
                        relay_state |= mask
                    else:
                        relay_state &= ~mask

                    state0 = relay_state & 0xFF
                    state1 = (relay_state >> 8) & 0xFF

                    if self.number < 8:
                        self._smbus.write_byte_data(ADDR, OUT0, state0)
                    else:
                        self._smbus.write_byte_data(ADDR, OUT1, state1)

                    return True
            except IOError as e:
                log.error(e)


if __name__ == '__main__':
    with Relay() as relay:
        for switch in relay:
            for _ in range(2):
                switch.toggle(relay.state())
        relay[0].toggle(relay.state())