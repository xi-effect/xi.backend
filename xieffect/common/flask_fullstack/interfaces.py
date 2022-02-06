from __future__ import annotations

from typing import Union


class Identifiable:
    """
    An interface to mark database classes that have an id and can be identified by it.

    Used in :ref:`.Namespace.database_searcher`
    """

    not_found_text: str = ""
    """ Customizable error message to be used for missing ids """

    def __init__(self, **kwargs):
        pass

    @classmethod
    def find_by_id(cls, session, entry_id: int) -> Union[Identifiable, None]:
        raise NotImplementedError


class UserRole(Identifiable):
    """
    An interface to mark database classes as user roles, that can be used for authorization.

    Used in :ref:`.Namespace.jwt_authorizer`
    """

    default_role: Union[UserRole, None] = None

    @classmethod
    def find_by_id(cls, session, entry_id: int) -> Union[UserRole, None]:
        raise NotImplementedError
