"""Monkey patching for various botocore features."""
from threading import RLock

from botocore.loaders import Loader
# pylint: disable=global-variable-not-assigned, invalid-name


_cache = {}
_lock = RLock()


def global_cache(func):
    """Cache the result of a method globally.

    This is essentially a copy of botocore.loaders.Loader.instance_cache but
    with a synchronized global cache (vs instance-specific)
    """
    def _wrapper(self, *args, **kwargs):
        global _cache, _lock
        with _lock:
            key = (func.__name__,) + args
            for pair in sorted(kwargs.items()):
                key += pair
            if key in _cache:
                return _cache[key]
            data = func(self, *args, **kwargs)
            _cache[key] = data
            return data
    return _wrapper


Loader_init_orig = Loader.__init__


def Loader_init_monkey(*args, **kwargs):
    """Wrap and monkey patch the original botocore Loader."""
    Loader_init_orig(*args, **kwargs)
