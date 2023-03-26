from __future__ import annotations

from flask_fullstack import EventController as _EventController, PydanticModel


class EventController(_EventController):
    def __init__(self, *args, **kwargs) -> None:
        kwargs["use_kebab_case"] = kwargs.get("use_kebab_case", True)
        super().__init__(*args, **kwargs)


class EmptyBody(PydanticModel):
    pass
