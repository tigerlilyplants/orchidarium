# This Python file uses the following encoding: utf-8
from __future__ import annotations

import sys

from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from orchidarium.ui.config import Config


def run() -> None:
    """
    Run the Qt/QML UI.
    """
    app = QGuiApplication(sys.argv)

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(Path(__file__).parent))

    config = Config(
        fullscreen=__name__ != '__main__',
        relay_count=8,
        relay_names={
            2: 'rain'
        }
    )
    engine.rootContext().setContextProperty("config", config)
    engine.loadFromModule("qml", "Main")

    if not engine.rootObjects():
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
