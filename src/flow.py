import asyncio
import logging
import multiprocessing
from threading import Lock as TLock
from threading import Thread


def dedicated(f):
    def wrapper(*args, **kwargs):
        t = Thread(target=f, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()
        return t

    return wrapper


def dedicate(func, *args, **kwargs):
    t = Thread(target=func, args=args, kwargs=kwargs)
    t.daemon = True
    t.start()
    return t


def adedicate(func):
    asyncio.run(func)


class Mutex:
    def __init__(self):
        self.tlock = TLock()

    def lock(self):
        self.tlock.acquire(True)

    def unlock(self):
        self.tlock.release()

    def sync(self):
        self.lock()
        self.unlock()


def pdedicate(func):
    def wrapper(*args, **kwargs):
        p = multiprocessing.Process(target=func, args=args, kwargs=kwargs)
        p.daemon = True
        p.start()
        return p

    return wrapper


__logged_level = 0


def logged(func):
    def wrapper(*args, **kwargs):
        global __logged_level
        logging.debug(' ' * 4 * __logged_level + f'Running {func.__name__}')
        __logged_level += 1
        r = func(*args, **kwargs)
        __logged_level -= 1
        logging.debug(' ' * 4 * __logged_level + f'Finished {func.__name__}')
        return r

    return wrapper
