from __future__ import annotations

from flask_fullstack import EventSpace, ServerEvent, DuplexEvent
from pydantic import BaseModel, Field

from common import User, EventController

controller = EventController()


@controller.route()
class SOMESpace(EventSpace):
    pass
