from __future__ import annotations

import re
import logging

from usb.core import find
from orchidarium import env
from orchidarium.sensors import Sensor
from orchidarium.lib.bus import InterfaceClaim, read
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orchidarium.publishers import Publisher


log = logging.getLogger(__name__)


class HumiditySensor(Sensor):

    _TEMPERATURE_FAHRENHEIT: float = 0.0
    _HUMIDITY: float = 0.0

    def collect(self) -> bool:
        device = find(
            idVendor=int(
                '0x0487',
                base=16
            ),
            idProduct=int(
                '0x0007',
                base=16
            )
        )

        if device is None:
            # Exit early if the USB device is not available.
            log.error(f'USB device with idVendor "{env["USB_VENDOR_ID"]}" and idProduct "{env["USB_PRODUCT_ID"]}" not found, exiting.')

            self._collection = False

            return False
        else:
            log.debug(f'Successfully located humidity device:\n\n{device}\n')

        with InterfaceClaim(device, detach=True):
            _match: re.Pattern = re.compile(r'T: [0-9]+.[0-9]+, RH: [0-9]+.[0-9]+')
            _extract_temperature: re.Pattern = re.compile(r'(?<=T: )[0-9]+.?[0-9]*(?=,)')
            _extract_humidity: re.Pattern = re.compile(r'(?<=, RH: )[0-9+.?[0-9]*')

            for i in range(10):
                _res = read(device[0][(0,0)][0], device).decode('utf-8', errors='replace')
                log.debug(f'Raw sensor read {i + 1} / 10: {_res}')
                if re.match(_match, _res):

                    _search_temperature = re.search(_extract_temperature, _res)
                    _search_humidity = re.search(_extract_humidity, _res)

                    if _search_temperature and _search_humidity:
                        self._TEMPERATURE_FAHRENHEIT = float(_search_temperature.group(0))
                        self._HUMIDITY = float(_search_humidity.group(0))

                        log.debug(f'Collected temperature (F): {self._TEMPERATURE_FAHRENHEIT}. Collected (relative) humidity value: {self._HUMIDITY}')

                        self._collection = True
                        return True
                    else:
                        log.error(f'Could not retrieve temperature or humidity reading.')
                    break

        self._collection = False
        return False

    def publish(self, publisher: Publisher) -> bool:
        ...
        self._publication = True
        return True