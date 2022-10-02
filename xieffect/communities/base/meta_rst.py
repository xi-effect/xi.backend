from __future__ import annotations

from flask_restx import Resource

from common import ResourceController
from .meta_db import Community
from .meta_utl import check_participant_role
from ..services.channels_db import Category, Channel

controller = ResourceController("communities-meta", path="/communities/")


@controller.route("/<int:community_id>/")
class CommunityReader(Resource):
    class FullModel(Community.IndexModel):
        categories: list[Category.IndexModel]
        channels: list[Channel.IndexModel]

        @classmethod
        def callback_convert(
            cls,
            callback,
            orm_object: Community,
            **context,
        ) -> None:
            callback(
                categories=[
                    Category.IndexModel.convert(category, **context)
                    for category in Category.find_by_community(orm_object.id)
                ],
                channels=[
                    # Channel.IndexModel.convert(channel, **context)
                    # for channel in Channel.find_by_ids(orm_object.id, None)
                    Channel.IndexModel.convert(channel, **context)
                    for channel in orm_object.channels
                ]
            )

    @check_participant_role(controller)
    @controller.marshal_with(FullModel)
    def get(self, community: Community):
        return community
