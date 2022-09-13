from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy as _SQLAlchemy
from sqlalchemy.orm import scoped_session

try:
    from greenlet import getcurrent as _ident_func
except ImportError:
    from threading import get_ident as _ident_func

from __lib__.flask_fullstack.utils import Session


class ScopedSession(scoped_session, Session):
    pass


class SQLAlchemy(_SQLAlchemy):
    def create_scoped_session(self, options=None):
        if options is None:
            options = {}

        scopefunc = options.pop('scopefunc', _ident_func)
        options.setdefault('query_cls', self.Query)
        return ScopedSession(
            self.create_session(options), scopefunc=scopefunc
        )
