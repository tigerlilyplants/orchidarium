from gpiozero import DigitalOutputDevice
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import batched
from time import sleep


pins = [4, 5, 6, 7, 8, 9, 10, 11]

#_gpios = [f'GPIO{x}' for x in range(4, 11 + 1)]
# gpios = [LED(_g) for _g in _gpios]

batchsize = 3


def routine(pin: int | str) -> None:
    with DigitalOutputDevice(pin, active_high=False, initial_value=False) as _device:
        _device.on()
        _device.is_active
        sleep(1)
        _device.off()
        _device.is_active


def main() -> None:
    while True:
        for subpins in batched(pins, n=batchsize):
            with ThreadPoolExecutor(max_workers=batchsize) as tp:
                threads = []

                for pin in subpins:
                    threads.append(
                        tp.submit(
                            # Map this to 'routine' function above.
                            routine,
                            pin
                        )
                    )

                # Wait for both jobs to complete.
                for _ in as_completed(threads):
                    pass


if __name__ == '__main__':
    main()