# This Python file uses the following encoding: utf-8
import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from ui.config import Config


def run() -> None:
    app = QGuiApplication(sys.argv)

    engine = QQmlApplicationEngine()
    engine.addImportPath(Path(__file__).parent)
    engine.loadFromModule("qml", "Main")

    if not engine.rootObjects():
        sys.exit(1)

    config = Config(
        fullscreen=__name__ != '__main__',
        relay_count=8,
        relay_names={
            2: 'rain'
        }
    )
    engine.rootContext().setContextProperty("config", config)

    # Based on some value, we can trigger whether or not to fullscreen the window for the touch display, or other display-related settings, here.
    # engine.rootContext().setContextProperty("config", {
    #     "fullscreen": __name__ != '__main__',
    #     "relayCount": 8,
    #     "relays": [
    #         {"index": 0, "name": "Pump"},
    #         {"index": 1, "name": "Fan"},
    #         {"index": 2, "name": "Light"},
    #         {"index": 3, "name": "Mist"},
    #     ]
    # })

    sys.exit(app.exec())


if __name__ == "__main__":
    run()