from __future__ import annotations

from flask_fullstack import counter_parser, RequestParser
from flask_restx import Resource

from common import ResourceController
from vault import File
from .meta_db import Community, Participant
from .roles_db import PermissionType
from .utils import check_participant, check_permission

controller = ResourceController(
    "communities-meta",
    path="/communities/<int:community_id>/",
)


@controller.route("/")
class CommunityReader(Resource):
    @check_participant(controller, use_participant=True, use_community=False)
    @controller.marshal_with(Participant.IndexModel)
    def get(self, participant: Participant) -> Participant:
        return participant


@controller.route("/avatar/")
class CommunityAvatar(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument(
        "avatar-id",
        dest="avatar_id",
        required=False,
        type=int,
    )

    @check_permission(controller, PermissionType.MANAGE_COMMUNITY)
    @controller.argument_parser(parser)
    @controller.database_searcher(File, input_field_name="avatar_id")
    @controller.a_response()
    def post(self, community: Community, file: File) -> None:
        community.avatar_id = file.id

    @check_permission(controller, PermissionType.MANAGE_COMMUNITY)
    @controller.a_response()
    def delete(self, community: Community) -> None:
        community.avatar.delete()


@controller.route("/participants/")
class ParticipantSearcher(Resource):
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("search", type=str, required=False)

    @check_participant(controller)
    @controller.argument_parser(parser)
    @controller.lister(10, Participant.FullModel)
    def get(self, search: str | None, community: Community, start: int, finish: int):
        return Participant.search_by_username(
            search, community.id, start, finish - start
        )
