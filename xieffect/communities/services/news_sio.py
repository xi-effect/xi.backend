from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from flask_socketio import join_room, leave_room

from common import DuplexEvent, EventController, EventSpace, User
from .news_db import Post
from ..base.invitations_sio import check_participant_role
from ..base.meta_db import ParticipantRole, Community

controller = EventController()


@controller.route()
class PostEventSpace(EventSpace):
    @classmethod
    def room_name(cls, community_id: int):
        return f"cs-news-{community_id}"

    class CommunityIdModel(BaseModel):
        community_id: int

    @controller.argument_parser(CommunityIdModel)
    @check_participant_role(ParticipantRole.OWNER, use_session=False)
    @controller.database_searcher(Community, use_session=True)
    @controller.force_ack()
    def open_news(self, community: Community):
        join_room(self.room_name(community.id))

    @controller.argument_parser(CommunityIdModel)
    @check_participant_role(ParticipantRole.OWNER, use_session=False)
    @controller.database_searcher(Community, use_session=True)
    @controller.force_ack()
    def close_news(self, community: Community):
        leave_room(self.room_name(community.id))

    class CreateModel(Post.CreationBaseModel, CommunityIdModel):
        pass

    @controller.argument_parser(CreateModel)
    @controller.mark_duplex(Post.IndexModel, use_event=True)
    @check_participant_role(ParticipantRole.OWNER)
    @controller.jwt_authorizer(User)
    @controller.marshal_ack(Post.IndexModel)
    def new_post(
        self,
        event: DuplexEvent,
        session,
        title: str,
        description: str | None,
        user: User,
        community: Community,
    ):
        post = Post.create(session, title, description, user.id, community.id)
        event.emit_convert(post, self.room_name(community.id))
        return post

    class UpdateModel(Post.CreationBaseModel, CommunityIdModel):
        entry_id: int

    @controller.argument_parser(UpdateModel)
    @controller.mark_duplex(Post.IndexModel, use_event=True)
    @check_participant_role(ParticipantRole.OWNER)
    @controller.jwt_authorizer(User, check_only=True)
    @controller.marshal_ack(Post.IndexModel)
    def update_post(
        self,
        event: DuplexEvent,
        session,
        title: str | None,
        description: str | None,
        community: Community,
        entry_id: int,
    ):
        if (updated_post := Post.find_by_id(session, entry_id)) is None:
            controller.abort(404, "News not found")
        if title is not None:
            updated_post.title = title
        if description is not None:
            updated_post.description = description
        updated_post.changed = datetime.utcnow().replace()

        event.emit_convert(updated_post, self.room_name(community.id))
        return updated_post

    class DeleteModel(BaseModel):
        community_id: int
        entry_id: int

    @controller.argument_parser(DeleteModel)
    @controller.mark_duplex(Post.IndexModel, use_event=True)
    @check_participant_role(ParticipantRole.OWNER)
    @controller.jwt_authorizer(User, check_only=True)
    def delete_post(
        self,
        event: DuplexEvent,
        session,
        community: Community,
        entry_id: int,
    ):
        if (deleted_post := Post.find_by_id(session, entry_id)) is None:
            controller.abort(404, "News not found")
        deleted_post.deleted = True

        event.emit_convert(deleted_post, self.room_name(community.id))
        return {"a": "Post was successfully deleted"}, 200
