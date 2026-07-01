from ._base import BaseRelay, BaseSwitch
from .i2c_board import I2CRelay, I2CSwitch


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
