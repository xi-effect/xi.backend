# from abc import ABC


class Identifiable:
    not_found_text: str = ""

    def __init__(self, **kwargs):
        pass

    @classmethod
    def find_by_id(cls, entry_id: int):
        raise NotImplementedError


class UserRole:
    not_found_text: str = ""

    def __init__(self, **kwargs):
        pass

    @classmethod
    def find_by_id(cls, entry_id: int):
        raise NotImplementedError
