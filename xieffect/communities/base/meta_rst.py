from __future__ import annotations

from flask_fullstack import RequestParser
from flask_restx import Resource

from common import ResourceController
from communities.base.meta_db import Community, ParticipantRole
from communities.utils import check_participant
from vault.files_db import File

controller = ResourceController(
    "communities-meta",
    path="/communities/<int:community_id>/",
)


@controller.route("/")
class CommunityReader(Resource):
    @controller.doc_abort(403, "Not a member")
    @check_participant(controller)
    @controller.marshal_with(Community.IndexModel)
    def get(self, community: Community):
        return community


@controller.route("/avatar/")
class CommunityAvatar(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument(
        "avatar-id",
        dest="avatar_id",
        required=False,
        type=int,
    )

    @controller.argument_parser(parser)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.database_searcher(File, input_field_name="avatar_id")
    @controller.a_response()
    def post(self, community: Community, file: File) -> None:
        community.avatar_id = file.id

    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.a_response()
    def delete(self, community: Community) -> None:
        community.avatar.delete()
