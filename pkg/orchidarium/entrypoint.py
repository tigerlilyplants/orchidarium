"""
Start the Orchidarium command-line interface.
"""


from __future__ import annotations

import sys

from orchidarium.daemon import daemon


def cli() -> None:
    sys.exit(
        daemon()
    )


if __name__ == '__main__':
    cli()
