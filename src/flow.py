from typing import Any, Callable


def logged(func: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args: tuple[Any, ...], **kwargs: dict[str, Any]) -> Any:
        return func(*args, **kwargs)

    return wrapper
