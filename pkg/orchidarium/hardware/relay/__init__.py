from importlib import import_module
from typing import Any

from ._base import BaseRelay, BaseSwitch


_i2c_relay_module: Any = import_module(f'{__name__}.8x2_i2c_relay')
I2CRelay = _i2c_relay_module.I2CRelay
I2CSwitch = _i2c_relay_module.I2CSwitch


Relay = I2CRelay
Switch = I2CSwitch


__all__ = [
    'BaseRelay',
    'BaseSwitch',
    'I2CRelay',
    'I2CSwitch',
    'Relay',
    'Switch',
]
