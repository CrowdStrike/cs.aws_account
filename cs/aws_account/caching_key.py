"""Helpers for creating a caching key."""


def aggregated_string_hash(*args, **kwargs):
    """Return a hash based on aggregated object strings."""
    _id = ""
    for arg in args:
        _id += str(arg)

    if kwargs:
        keys = sorted(kwargs.keys())
        for k in keys:
            _id += f"{k}:{kwargs[k]}"
    return hash(_id)
