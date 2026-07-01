"""
Configure Orchidarium logging.
"""


from __future__ import annotations

import logging
import sys

from orchidarium import env


def configure_logging() -> None:
    """
    Configure process logging from the current environment.
    """
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG if env['DEBUG'] != '' else logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
