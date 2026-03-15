from controller.entrypoint import daemon
from environment.entrypoint import daemon
from concurrent.futures import ProcessPoolExecutor, as_completed


def cli() -> None:
    ...