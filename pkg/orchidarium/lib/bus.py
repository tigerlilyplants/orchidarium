"""
API for interacting with a USB device.
"""


from __future__ import annotations

import logging

from contextlib import AbstractContextManager
from functools import partial
from time import sleep
from usb.core import USBTimeoutError, USBError
from usb.util import claim_interface, release_interface
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from array import array
    from typing import (
        Callable,
        Any
    )


log = logging.getLogger(__name__)

__all__ = [
    'communicate',
    'InterfaceClaim',
    'read'
]


def communicate(f: Callable, delay: int = 1) -> array:
    """
    Retry api calls to the USB device until they go through.

    Args:
        f (Callable):
        delay (int):

    Returns:
        array:
    """
    while True:
        try:
            return f()
        except USBTimeoutError as e:
            log.warning(f'Timeout, sleeping for {delay}s before retrying connection: {e}')
            sleep(delay)
        except USBError as e:
            if 'Resource busy' in str(e):
                log.warning(f'Resource busy, retrying')
                sleep(delay)
                continue

            log.error(f'{e}')


class InterfaceClaim(AbstractContextManager):
    """
    Wrap setup and teardown while connecting to a USB interface in a context manager.
    """
    def __init__(self, device: Any, interface: int = 0, detach: bool = False) -> None:
        self.device = device
        self.interface = interface
        self.detach = detach
        # Indicate that a detachment of the kernel driver took place.
        self._detached: bool = False

    def __enter__(self) -> InterfaceClaim:
        if self.detach:
            # Detaching kernel driver if necessary (e.g., for direct communication)
            if self.device.is_kernel_driver_active(0): # Check if kernel driver is active on interface 0
                log.warning(f'Detaching kernel driver')
                communicate(
                    partial(
                        self.device.detach_kernel_driver,
                        self.interface
                    )
                )
                self._detached = True

        communicate(
            partial(
                claim_interface,
                self.device,
                self.interface
            )
        )

        return self

    def __exit__(self, *args: Any) -> None:
        communicate(
            partial(
                release_interface,
                self.device,
                self.interface
            )
        )

        if self.detach and self._detached:
            log.warning(f'Re-attaching kernel driver before exiting')
            # Detaching kernel driver if necessary (e.g., for direct communication)
            communicate(
                partial(
                    self.device.attach_kernel_driver,
                    self.interface
                )
            )


def read(endpoint: Any, device: Any) -> bytes:
    """
    Read data from a device.

    Args:
        endpoint (Any): _description_
        device (Any): _description_

    Returns:
        bytes: _description_
    """
    msg = communicate(
        partial(
            device.read,
            endpoint.bEndpointAddress,
            endpoint.wMaxPacketSize,
        )
    ).tobytes()

    log.debug(f'Message read from bus: "{msg.decode()}"')

    return msg