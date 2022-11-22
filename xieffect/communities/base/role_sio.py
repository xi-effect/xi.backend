from __future__ import annotations

from flask_fullstack import EventSpace

from common import EventController

controller = EventController()


@controller.route()
class RolesEventSpace(EventSpace):
    pass
