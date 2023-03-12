from __future__ import annotations

from functools import wraps

from flask_fullstack import ResourceController, EventController, get_or_pop

from common import User
from .meta_db import Community, Participant
from .roles_db import PermissionType, ParticipantRole


def check_participant(
    controller: ResourceController | EventController,
    *,
    use_user: bool = False,
    use_participant: bool = False,
    use_participant_id: bool = False,
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

            if use_participant_id:
                kwargs["id_participant"] = participant.id

            return function(*args, **kwargs)

        return check_participant_role_inner

    return check_participant_role_wrapper


def check_permission(
    controller: ResourceController | EventController,
    permission_type: PermissionType,
    *,
    use_user: bool = False
):
    @controller.doc_abort(403, "Permission Denied")
    def check_permission_wrapper(function):
        @check_participant(
            controller,
            use_participant_id=True,
            use_user=use_user,
        )
        @wraps(function)
        def check_permission_inner(*args, **kwargs):
            result = ParticipantRole.has_permission(
                kwargs.pop("id_participant"), permission_type
            )
            if result is False:
                controller.abort(403, "Permission Denied: Not sufficient permissions")

            return function(*args, **kwargs)

        return check_permission_inner

    return check_permission_wrapper
