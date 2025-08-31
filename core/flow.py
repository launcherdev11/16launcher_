import logging

__logged_level = 0


def logged(func):
    def wrapper(*args, **kwargs):
        global __logged_level
        logging.debug(" " * 4 * __logged_level + f"Running {func.__name__}")
        __logged_level += 1
        r = func(*args, **kwargs)
        __logged_level -= 1
        logging.debug(" " * 4 * __logged_level + f"Finished {func.__name__}")
        return r

    return wrapper
