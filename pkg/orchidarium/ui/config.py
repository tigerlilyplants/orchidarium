from PySide6.QtCore import QObject, Property, Signal, Slot


class Config(QObject):
    relayNamesChanged = Signal()
    fullscreenChanged = Signal()
    relayCountChanged = Signal()

    def __init__(self, fullscreen: bool = False, relay_count: int = 4, relay_names: dict | None = None):
        super().__init__()
        self._fullscreen = fullscreen
        self._relay_count = relay_count

        if relay_names is None:
            self._relay_names = {}
        else:
            self._relay_names = relay_names

    @Property(bool, notify=fullscreenChanged)
    def fullscreen(self):
        return self._fullscreen

    @Property(int, notify=relayCountChanged)
    def relayCount(self):
        return self._relay_count

    @Slot(int, result=str)
    def relayName(self, index):
        return self._relay_names.get(index, f"Relay {index + 1}")

    @Slot(int, str)
    def setRelayName(self, index, name):
        self._relay_names[index] = name
        self.relayNamesChanged.emit()
