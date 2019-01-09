
def aggregated_string_hash(*args, **kwargs):
    """Return a hash based on aggregated object strings"""
    _id = ''
    for arg in args:
        _id += u"{}".format(arg)
    
    if kwargs:
        keys = sorted(kwargs.keys())
        for k in keys:
            _id += u"{}:{}".format(k, kwargs[k])
    return hash(_id)