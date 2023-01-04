from __future__ import annotations

from functools import wraps

from flask_fullstack import ResourceController, EventController, get_or_pop

from common import User
from .meta_db import Community, Participant
from .roles_db import PermissionType, ParticipantRole


def check_permission(participant_id: int, permission: PermissionType) -> bool:
    return any(
        per is permission
        for per in ParticipantRole.get_permissions_by_participant(participant_id)
    )


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

            checks = (
                check_permission(participant.id, permission) is False,
                permission is not None,
            )

            if all(checks):
                controller.abort(
                    403, "Permission Denied: Participant haven't permission"
                )

            return function(*args, **kwargs)

        return check_participant_role_inner

    return check_participant_role_wrapper
