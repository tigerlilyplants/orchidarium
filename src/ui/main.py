# This Python file uses the following encoding: utf-8
import sys
from pathlib import Path

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)

    engine = QQmlApplicationEngine()
    engine.addImportPath(Path(__file__).parent)
    engine.loadFromModule("qml", "Main")

    if not engine.rootObjects():
        sys.exit(1)

    # Based on some value, we can trigger whether or not to fullscreen the window for the touch display.
    if __name__ == '__main__':
        engine.rootContext().setContextProperty("isFullscreen", False)

    sys.exit(app.exec())