from __future__ import annotations

from flask_fullstack import (
    Namespace as _Namespace,
    EventController as _EventController,
    PydanticModel,
)
from flask_socketio import ConnectionRefusedError, join_room

from common.authorization import ProxyAuthMixin


class Namespace(_Namespace):
    def mark_protected(self, protected: str | bool = False) -> None:
        if protected:

            @self.on_connect()
            def user_connect(*_):
                user_id: int | None = ProxyAuthMixin.get_user_id()
                if user_id is None:
                    raise ConnectionRefusedError(ProxyAuthMixin.auth_required_error[1])
                join_room(f"user-{user_id}")


class EventController(_EventController, ProxyAuthMixin):
    def __init__(self, *args, **kwargs) -> None:
        kwargs["use_kebab_case"] = kwargs.get("use_kebab_case", True)
        super().__init__(*args, **kwargs)


class EmptyBody(PydanticModel):
    pass
