"""
Start the Orchidarium command-line interface.
"""


from __future__ import annotations

import sys

from orchidarium.daemon import run


def cli() -> None:
    sys.exit(
        run()
    )


if __name__ == '__main__':
    cli()
