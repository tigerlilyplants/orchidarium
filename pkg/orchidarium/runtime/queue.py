"""
Read queue runtime state.
"""


from __future__ import annotations

from typing import Any

from cattrs import unstructure

from orchidarium import env
from orchidarium.data import metric_queue
from orchidarium.runtime.state import read_runtime_state


__all__ = [
    'get_point_backlog_health',
    'get_queue_summary',
    'is_point_backlog_ready',
    'max_point_backlog'
]


def max_point_backlog() -> int:
    """
    Return the configured maximum point backlog.

    Returns:
        int: maximum allowed point backlog before readiness fails.
    """
    return int(env['MAX_POINT_BACKLOG'])


def get_queue_summary() -> dict[str, Any]:
    """
    Return the latest queue summary published by the metrics process.

    Returns:
        dict[str, Any]: queue summary fields suitable for JSON serialization.
    """
    queue_summary = read_runtime_state().get('queue')

    if isinstance(queue_summary, dict):
        return queue_summary

    return unstructure(metric_queue.activity_summary())


def _current_point_backlog() -> int:
    current_backlog = get_queue_summary().get('current_backlog')

    if isinstance(current_backlog, int):
        return current_backlog

    return 0


def is_point_backlog_ready() -> bool:
    """
    Return whether the point backlog is below its configured maximum.

    Returns:
        bool: True when more work may be scheduled to this container.
    """
    return _current_point_backlog() < max_point_backlog()


def get_point_backlog_health() -> dict[str, int | bool]:
    """
    Return readiness fields for the point backlog.

    Returns:
        dict[str, int | bool]: point backlog readiness fields.
    """
    current_backlog = _current_point_backlog()
    configured_max = max_point_backlog()

    return {
        'current_backlog': current_backlog,
        'max_point_backlog': configured_max,
        'ready': current_backlog < configured_max
    }
