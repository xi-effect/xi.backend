from __future__ import annotations

from pydantic import BaseModel, Field

from common import EventController, EventSpace, ServerEvent, DuplexEvent, User
from .invitations_db import Invitation
from .meta_db import Community, Participant, ParticipantRole

controller = EventController()


@controller.route()
class InvitationsEventSpace(EventSpace):
    pass
