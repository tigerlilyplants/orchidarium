from functools import wraps
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Callable, TypeVar, Tuple
    T = TypeVar('T')


def now(f: Callable[..., T]) -> Callable[..., Tuple[T, datetime]]:
    """
    Bundle a function call with a datetime object representing the time the function exited.

    Args:
        f (Callable[..., T]): any function to pair with a timestamp.

    Returns:
        Callable[..., Tuple[T, datetime]]: ammend the return object of the encapsulated function with a timestamp.
    """
    @wraps(f)
    def _f(*args, **kwargs) -> Tuple[T, datetime]:
        return f(*args, **kwargs), datetime.now()
    return _f