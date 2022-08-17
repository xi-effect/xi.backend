from __future__ import annotations

from pydantic import BaseModel, Field

from common import EventController, EventSpace, ServerEvent, DuplexEvent, User

controller = EventController()


@controller.route()
class SOMESpace(EventSpace):
    pass
