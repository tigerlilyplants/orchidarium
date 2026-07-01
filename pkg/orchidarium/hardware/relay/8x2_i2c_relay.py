"""
Control an 8x2 I2C relay board.
"""


from __future__ import annotations

import logging

from collections.abc import Iterator
from contextlib import AbstractContextManager
from datetime import datetime, timedelta
from random import random
from threading import Lock
from time import sleep
from typing import Any, Final

from smbus2 import SMBus

from ._base import BaseRelay, BaseSwitch


__all__ = [
    'I2CRelay',
    'I2CSwitch',
]


log = logging.getLogger(__name__)


DEFAULT_ADDRESS = 0x20
INPUT_0 = 0x00
INPUT_1 = 0x01
OUTPUT_0 = 0x02
OUTPUT_1 = 0x03
CONFIGURATION_0 = 0x06
CONFIGURATION_1 = 0x07


class I2CRelay(BaseRelay, AbstractContextManager['I2CRelay']):
    """
    Relay interface for an 8x2 I2C relay board.
    """

    def __init__(
        self,
        size: int = 16,
        bus: int = 1,
        address: int = DEFAULT_ADDRESS,
        readonly: bool = False,
        switch_bounce_delay: float = 0.25
    ) -> None:
        if not 1 <= size <= 16:
            raise ValueError('I2CRelay size must be between 1 and 16')

        if switch_bounce_delay <= 0:
            raise ValueError('switch_bounce_delay must be positive')

        self.size: Final[int] = size
        self.bus: Final[int] = bus
        self.address: Final[int] = address
        self.readonly: Final[bool] = readonly
        self.switch_bounce_delay: Final[float] = switch_bounce_delay

        self._switches: list[I2CSwitch] = []
        self._smbus: SMBus | None = None
        self._state: int = 0x00
        self._lock = Lock()

    def __getitem__(self, key: int) -> I2CSwitch:
        return self._switches[key]

    def __iter__(self) -> Iterator[I2CSwitch]:
        return iter(self._switches)

    def __enter__(self) -> I2CRelay:
        if self.open():
            return self

        raise OSError('Could not open connection to relay')

    def __exit__(self, *args: Any) -> None:
        self.close()

    def state(self) -> int:
        """
        Return the cached relay state.

        Returns:
            int: 16-bit relay state mask.
        """
        with self._lock:
            return self._state

    def refresh_state(self) -> int:
        """
        Read and cache the relay state from the board.

        Returns:
            int: 16-bit relay state mask.
        """
        with self._lock:
            self._state = self._read_state()
            return self._state

    def state_map(self) -> dict[int, bool]:
        """
        Return each switch's state.

        Returns:
            dict[int, bool]: map of switch index to on/off state.
        """
        relay_state = self.refresh_state()
        return {
            index: bool(relay_state & (1 << index))
            for index in range(self.size)
        }

    def open(self) -> bool:
        """
        Open the relay bus and initialize switches.

        Returns:
            bool: True when the relay bus is open.
        """
        if self._smbus is None:
            self._smbus = SMBus(self.bus)

        self._switches = [
            I2CSwitch(
                relay=self,
                number=index,
                switch_bounce_delay=self.switch_bounce_delay,
                readonly=self.readonly,
            )
            for index in range(self.size)
        ]

        self._initialize_relay()
        return True

    def close(self) -> None:
        """
        Close the relay bus.
        """
        if self._smbus is not None:
            self._smbus.close()
            self._smbus = None

    def reset(self) -> None:
        """
        Turn all switches off.
        """
        self._write_state(0)

    def on(self) -> None:
        """
        Turn all switches on.
        """
        self._write_state(self._relay_mask)

    def toggle(self, count: int = 1, delay: float = 0.0) -> None:
        """
        Toggle all switches.

        Args:
            count (int): number of times to toggle the relay.
            delay (float): delay between toggles.
        """
        for index in range(count):
            self._write_state(self.state() ^ self._relay_mask)

            if count > 1 and index < count - 1 and delay > 0:
                sleep(delay)

    @property
    def _relay_mask(self) -> int:
        return (1 << self.size) - 1

    def _initialize_relay(self) -> None:
        if self._smbus is None:
            raise OSError('Open connection to relay prior to initialization')

        if not self.readonly:
            self._smbus.write_byte_data(self.address, CONFIGURATION_0, 0x00)
            self._smbus.write_byte_data(self.address, CONFIGURATION_1, 0x00)

        self.refresh_state()

        if self._state and not self.readonly:
            self.reset()

    def _get_switch(self, number: int) -> bool:
        with self._lock:
            self._state = self._read_state()
            return bool(self._state & (1 << number))

    def _set_switch(self, number: int, state: bool) -> bool:
        if self.readonly:
            log.warning('Skipping relay switch %s update because relay is readonly', number + 1)
            return False

        with self._lock:
            mask = 1 << number

            if state:
                relay_state = self._state | mask
            else:
                relay_state = self._state & ~mask

            self._write_state_unlocked(relay_state)
            self._state = relay_state
            return True

    def _read_state(self) -> int:
        if self._smbus is None:
            raise OSError('Relay bus is not open')

        low = self._smbus.read_byte_data(self.address, INPUT_0)
        high = self._smbus.read_byte_data(self.address, INPUT_1)
        return (low | (high << 8)) & self._relay_mask

    def _write_state(self, relay_state: int) -> None:
        if self.readonly:
            log.warning('Skipping relay update because relay is readonly')
            return

        with self._lock:
            self._write_state_unlocked(relay_state & self._relay_mask)
            self._state = relay_state & self._relay_mask

    def _write_state_unlocked(self, relay_state: int) -> None:
        if self._smbus is None:
            raise OSError('Relay bus is not open')

        self._smbus.write_byte_data(self.address, OUTPUT_0, relay_state & 0xFF)
        self._smbus.write_byte_data(self.address, OUTPUT_1, (relay_state >> 8) & 0xFF)


class I2CSwitch(BaseSwitch):
    """
    Single switch on an I2C relay.
    """

    def __init__(
        self,
        relay: I2CRelay,
        number: int,
        switch_bounce_delay: float = 0.25,
        readonly: bool = False
    ) -> None:
        self._relay = relay
        self.number: Final[int] = number
        self.switch_bounce_delay: Final[timedelta] = timedelta(seconds=switch_bounce_delay)
        self.readonly: Final[bool] = readonly
        self._last_state_change = datetime.now()

        self.read_register: Final[int] = INPUT_0 if self.number < 8 else INPUT_1
        self.write_register: Final[int] = OUTPUT_0 if self.number < 8 else OUTPUT_1

    def block(self) -> None:
        """
        Block until this switch can safely change state again.
        """
        ready_at = self._last_state_change + self.switch_bounce_delay
        now = datetime.now()

        if now < ready_at:
            sleep((ready_at - now).total_seconds() + self._jitter)

    def get(self) -> bool:
        """
        Return this switch's current state.

        Returns:
            bool: True when the switch is on.
        """
        return self._relay._get_switch(self.number)

    def on(self) -> bool:
        """
        Turn this switch on.

        Returns:
            bool: True when the switch was updated.
        """
        return self._set(True)

    def reset(self) -> bool:
        """
        Turn this switch off.

        Returns:
            bool: True when the switch was updated.
        """
        return self._set(False)

    def toggle(self, count: int = 1, delay: float = 0.0) -> None:
        """
        Toggle this switch.

        Args:
            count (int): number of times to toggle this switch.
            delay (float): delay between toggles.
        """
        for index in range(count):
            if self.get():
                self.reset()
            else:
                self.on()

            if count > 1 and index < count - 1 and delay > 0:
                sleep(delay)

    @property
    def _jitter(self) -> float:
        return round(random() % (self.switch_bounce_delay.total_seconds() / 10), 4)

    def _set(self, state: bool) -> bool:
        self.block()

        if self.readonly:
            log.warning('Skipping relay switch %s update because switch is readonly', self.number + 1)
            return False

        updated = self._relay._set_switch(self.number, state)

        if updated:
            self._last_state_change = datetime.now()

        return updated
