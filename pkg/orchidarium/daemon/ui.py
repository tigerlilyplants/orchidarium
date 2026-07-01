"""
Run the Orchidarium UI process.
"""


from __future__ import annotations

import logging
import os
import re
import socket

from pathlib import Path
from setproctitle import setproctitle

from orchidarium.logging import configure_logging


log = logging.getLogger(__name__)


class UIDisplayConfigurationError(RuntimeError):
    """
    Raised when the configured Qt display backend cannot be reached safely.
    """


def _qt_platform() -> str:
    """
    Return the configured Qt platform backend.

    Returns:
        str: normalized Qt platform backend name.
    """
    return os.getenv('QT_QPA_PLATFORM', '').strip().split(';', maxsplit=1)[0]


def _preflight_ui_display() -> None:
    """
    Validate display backends that can make Qt abort during initialization.
    """
    platform = _qt_platform()

    if platform == 'xcb':
        _preflight_xcb_display()
    elif platform.startswith('wayland'):
        _preflight_wayland_display()


def _preflight_wayland_display() -> None:
    """
    Validate that the configured Wayland socket exists.

    Raises:
        UIDisplayConfigurationError: if the Wayland socket cannot be found.
    """
    xdg_runtime_dir = os.getenv('XDG_RUNTIME_DIR', '')
    wayland_display = os.getenv('WAYLAND_DISPLAY', 'wayland-0')

    if not xdg_runtime_dir:
        raise UIDisplayConfigurationError('QT_QPA_PLATFORM=wayland requires XDG_RUNTIME_DIR to be set')

    wayland_socket = Path(xdg_runtime_dir) / wayland_display

    if not wayland_socket.is_socket():
        raise UIDisplayConfigurationError(
            f'QT_QPA_PLATFORM=wayland expected socket "{wayland_socket}" to exist; '
            'start Orchidarium from the desktop user that owns the Wayland session or use QT_QPA_PLATFORM=offscreen for local tests'
        )


def _preflight_xcb_display() -> None:
    """
    Validate that the configured X11 display can be reached.

    Raises:
        UIDisplayConfigurationError: if the X11 display cannot be reached.
    """
    display = os.getenv('DISPLAY', '')

    if not display:
        raise UIDisplayConfigurationError('QT_QPA_PLATFORM=xcb requires DISPLAY to be set')

    if display.startswith(':'):
        _preflight_x11_unix_socket(display)
        return

    _preflight_x11_tcp_display(display)


def _preflight_x11_unix_socket(display: str) -> None:
    """
    Validate an X11 Unix socket display.

    Args:
        display (str): X11 DISPLAY value.

    Raises:
        UIDisplayConfigurationError: if the expected X11 Unix socket cannot be found.
    """
    match = re.match(r'^:(?P<display_number>\d+)(?:\.\d+)?$', display)

    if not match:
        raise UIDisplayConfigurationError(f'Could not parse X11 DISPLAY value "{display}"')

    x11_socket = Path('/tmp/.X11-unix') / f'X{match.group("display_number")}'

    if not x11_socket.is_socket():
        raise UIDisplayConfigurationError(
            f'QT_QPA_PLATFORM=xcb expected X11 socket "{x11_socket}" to exist for DISPLAY={display}'
        )


def _preflight_x11_tcp_display(display: str) -> None:
    """
    Validate an X11 TCP display.

    Args:
        display (str): X11 DISPLAY value.

    Raises:
        UIDisplayConfigurationError: if the X11 TCP display cannot be reached.
    """
    match = re.match(r'^(?P<host>[^:]+):(?P<display_number>\d+)(?:\.\d+)?$', display)

    if not match:
        raise UIDisplayConfigurationError(f'Could not parse X11 DISPLAY value "{display}"')

    host = match.group('host')
    port = 6000 + int(match.group('display_number'))

    try:
        with socket.create_connection((host, port), timeout=1.0):
            return
    except OSError as e:
        raise UIDisplayConfigurationError(
            f'QT_QPA_PLATFORM=xcb could not connect to DISPLAY={display} at {host}:{port}; '
            'on macOS this usually means XQuartz is not running, "Allow connections from network clients" is disabled, '
            'XQuartz was not restarted after enabling it, or xhost has not allowed Docker clients'
        ) from e


def run_ui_process() -> int:
    """
    Run the Qt/QML UI process.

    Returns:
        int: 0 if successful, 1 or another exit code, otherwise.
    """
    configure_logging()
    setproctitle('orchidarium-ui')
    log.info('Started UI process')

    try:
        _preflight_ui_display()

        from orchidarium.ui.entrypoint import run

        run()
    except UIDisplayConfigurationError as e:
        log.error(e)
        return 1
    except KeyboardInterrupt:
        log.info('UI process interrupted')
        return 130
    except SystemExit as e:
        if isinstance(e.code, int):
            return e.code

        return 1 if e.code else 0
    except Exception:
        log.exception('UI process failed')
        return 1

    return 0
