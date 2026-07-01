"""
Publish and read runtime state snapshots.
"""


from __future__ import annotations

import json
import os
import tempfile

from datetime import datetime, timezone
from json import JSONDecodeError
from pathlib import Path
from threading import Lock
from typing import Any


_state_lock = Lock()
_state_path = Path(tempfile.gettempdir()) / 'orchidarium' / 'runtime-state.json'


def read_runtime_state() -> dict[str, Any]:
    """
    Read the latest runtime state snapshot.

    Returns:
        dict[str, Any]: runtime state fields.
    """
    try:
        with _state_path.open() as state_file:
            state = json.load(state_file)
    except (FileNotFoundError, JSONDecodeError, OSError):
        return {}

    if isinstance(state, dict):
        return state

    return {}


def update_runtime_state(**updates: dict[str, Any]) -> None:
    """
    Atomically update runtime state fields.

    Args:
        **updates (dict[str, Any]): state fields to replace.
    """
    with _state_lock:
        state = read_runtime_state()
        state.update(updates)
        state['updated_at'] = datetime.now(timezone.utc).isoformat()

        _state_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=_state_path.parent,
            prefix=f'.{_state_path.name}.',
            text=True
        )

        try:
            with os.fdopen(fd, 'w') as tmp_file:
                json.dump(state, tmp_file, sort_keys=True)

            Path(tmp_path).replace(_state_path)
        finally:
            try:
                Path(tmp_path).unlink()
            except FileNotFoundError:
                pass
