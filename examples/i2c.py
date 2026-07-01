from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import batched

from orchidarium.hardware.relay import Relay


if __name__ == '__main__':
    with Relay() as relay:
        for _ in range(2):
            for switch_group in batched(relay, 8, strict=False):
                with ThreadPoolExecutor(max_workers=8) as pool:
                    threads = [
                        pool.submit(switch.toggle)
                        for switch in switch_group
                    ]

                    for future in as_completed(threads):
                        future.result()

        for switch in relay:
            switch.reset()
