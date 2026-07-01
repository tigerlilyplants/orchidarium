def run() -> None:
    """
    Run the Qt/QML UI.
    """
    from orchidarium.ui.main import run as _run

    _run()


__all__ = [
    'run'
]
