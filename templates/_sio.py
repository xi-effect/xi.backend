from __future__ import annotations

from flask_fullstack import EventSpace, ServerEvent, DuplexEvent
from pydantic import BaseModel, Field

from common import EventController
from users.users_db import User

controller = EventController()


@controller.route()
class SOMESpace(EventSpace):
    pass
