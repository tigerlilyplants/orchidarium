from gpiozero import DigitalOutputDevice
from time import sleep


pins = [4, 5, 6, 7, 8, 9, 10, 11]

#_gpios = [f'GPIO{x}' for x in range(4, 11 + 1)]
# gpios = [LED(_g) for _g in _gpios]

while True:
    for pin in pins:
        with DigitalOutputDevice(pin, active_high=False, initial_value=False) as _device:
            _device.on()
            _device.is_active
            sleep(1)
            _device.off()
            _device.is_active

    for pin in reversed(pins):
        with DigitalOutputDevice(pin, active_high=False, initial_value=False) as _device:
            _device.on()
            _device.is_active
            sleep(1)
            _device.off()
            _device.is_active