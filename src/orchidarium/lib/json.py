from __future__ import annotations

import json
import logging

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Dict


__all__ = [
    'write_json',
    'read_json',
    # 'cached_read_json'
]

log = logging.getLogger(__name__)


def write_json(data: dict, path: Path | str) -> bool:
    """
    Write a dictionary to a JSON file.

    Args:
        data (dict): the dictionary to write.
        path (Path | str): the path to write the file to.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        with open(path, 'w', encoding='utf-8') as f:
            log.debug(f'Writing JSON to file: {path}')
            json.dump(data, f)
            return True
    except (FileNotFoundError, PermissionError) as msg:
        log.error(f'Failed to write JSON file, received: {msg}')
    except OSError as msg:
        log.error(f'Failed to write JSON file {path}, received: {msg}. Check your path and permissions')

    return False


def read_json(path: Path | str) -> Dict:
    """
    Read a JSON file and return the data as a dictionary.

    Args:
        path (Path | str): the path to the JSON file.

    Returns:
        Dict: the data from the JSON file, or None if the file does not exist.
    """
    try:
        if Path(path).exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return dict()
    except (FileNotFoundError, PermissionError) as msg:
        log.error(f'Failed to read JSON file, received: {msg}')
        return dict()


# def cached_read_json(path: Path | str) -> Dict:
#     """
#     Same function as 'read_json', the reads from disk are cached for the interval, however.
#     """
#     try:
#         k = cache[str(path)]
#         log.debug(f'Cache key hit, using cached value for path "{path}" on disk')
#         return k
#     except KeyError:
#         log.debug(f'Cache miss, reading JSON cache "{path}" from disk')
#         _json = read_json(path)
#         cache[str(path)] = _json
#         return _json