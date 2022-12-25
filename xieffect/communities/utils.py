from __future__ import annotations

from functools import wraps

from flask_fullstack import ResourceController, EventController, get_or_pop

from common import User
from .base.meta_db import Community, Participant
from .base.roles_db import ParticipantRole, PermissionType


def check_permission(participant: Participant, permission: PermissionType) -> bool:
    for per in ParticipantRole.get_permissions_by_participant(
        participant_id=participant.id
    ):
        if per is permission:
            return True
    return False


def check_participant(
    controller: ResourceController | EventController,
    *,
    permission: PermissionType = None,
    use_user: bool = False,
    use_participant: bool = False,
    use_community: bool = True,
):
    def check_participant_role_wrapper(function):
        @controller.doc_abort(403, "Permission Denied")
        @controller.jwt_authorizer(User)
        @controller.database_searcher(Community)
        @wraps(function)
        def check_participant_role_inner(*args, **kwargs):
            user = get_or_pop(kwargs, "user", use_user)
            community = get_or_pop(kwargs, "community", use_community)

            participant = Participant.find_by_ids(community.id, user.id)
            if participant is None:
                controller.abort(403, "Permission Denied: Participant not found")

            if use_participant:  # TODO pragma: no coverage
                kwargs["participant"] = participant

            if permission is not None:
                if check_permission(participant, permission):
                    return function(*args, **kwargs)
                controller.abort(
                    403, "Permission Denied: Participant doesn't have permission"
                )
            return function(*args, **kwargs)

        return check_participant_role_inner

    return check_participant_role_wrapper
