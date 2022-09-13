from __future__ import annotations

from functools import wraps

from common import User, get_or_pop
from .meta_db import Community, ParticipantRole, Participant


def check_participant_role(
    controller,
    role: ParticipantRole | None = None,
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

            if role is not None and participant.role.value < role.value:
                controller.abort(403, "Permission Denied: Low role")

            if use_participant:
                kwargs["participant"] = participant

            return function(*args, **kwargs)

        return check_participant_role_inner

    return check_participant_role_wrapper
