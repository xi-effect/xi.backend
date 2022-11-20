from __future__ import annotations

from functools import wraps

from flask_fullstack import ResourceController, EventController, get_or_pop

from .base import ParticipantRole, Community, Participant
from common import User


def check_participant(
    controller: ResourceController | EventController,
    *,
    role: ParticipantRole = ParticipantRole.BASE,
    use_user: bool = False,
    use_participant: bool = False,
    use_community: bool = True,
):
    def check_participant_role_wrapper(function):
        @wraps(function)
        @controller.doc_abort(403, "Permission Denied")
        @controller.jwt_authorizer(User)
        @controller.database_searcher(Community)
        def check_participant_role_inner(*args, **kwargs):
            user = get_or_pop(kwargs, "user", use_user)
            community = get_or_pop(kwargs, "community", use_community)

            participant = Participant.find_by_ids(community.id, user.id)
            if participant is None:
                controller.abort(403, "Permission Denied: Participant not found")

            if participant.role.value < role.value:
                controller.abort(403, "Permission Denied: Low role")

            if use_participant:  # TODO pragma: no coverage
                kwargs["participant"] = participant

            return function(*args, **kwargs)

        return check_participant_role_inner

    return check_participant_role_wrapper
