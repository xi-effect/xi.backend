def remove_none(data: dict, **kwargs):
    return {key: value for key, value in dict(data, **kwargs).items() if value is not None}
