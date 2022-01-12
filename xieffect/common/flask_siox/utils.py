def remove_none(data: dict):
    return {key: value for key, value in data.items() if value is not None}
