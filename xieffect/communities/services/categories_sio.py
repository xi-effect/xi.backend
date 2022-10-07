from __future__ import annotations

from flask_socketio import join_room, leave_room
from pydantic import BaseModel

from common import DuplexEvent, EventController, EventSpace, db
from .channels_db import Category, MAX_CHANNELS, Channel
from ..base.meta_db import ParticipantRole, Community
from ..base.meta_utl import check_participant_role

controller = EventController()


@controller.route()
class ChannelCategoryEventSpace(EventSpace):
    @classmethod
    def room_name(cls, community_id: int):
        return f"community-{community_id}"

    class CommunityIdModel(BaseModel):
        community_id: int

    @controller.argument_parser(CommunityIdModel)
    @check_participant_role(controller, ParticipantRole.BASE)
    @controller.force_ack()
    def open_category(self, community: Community):
        join_room(self.room_name(community.id))

    @controller.argument_parser(CommunityIdModel)
    @check_participant_role(controller, ParticipantRole.BASE)
    @controller.force_ack()
    def close_category(self, community: Community):
        leave_room(self.room_name(community.id))

    class CreateModel(Category.CreateModel, CommunityIdModel):
        next_id: int = None

    @controller.doc_abort(409, "Over limit")
    @controller.argument_parser(CreateModel)
    @controller.mark_duplex(Category.IndexModel, use_event=True)
    @check_participant_role(controller, ParticipantRole.OWNER)
    @controller.marshal_ack(Category.IndexModel)
    def new_category(
        self,
        event: DuplexEvent,
        name: str,
        description: str,
        community: Community,
        next_id: int | None,
    ):
        # Check category limit
        if Channel.count_by_category(community.id) == MAX_CHANNELS:
            controller.abort(409, "Over limit: Too many categories")

        category = Category.add(
            next_id,
            name=name,
            description=description,
            prev_id=0,
            next_id=0,
            community_id=community.id,
        )

        db.session.commit()
        event.emit_convert(category, self.room_name(community.id))
        return category

    class UpdateModel(Category.CreateModel, CommunityIdModel):
        category_id: int

    @controller.argument_parser(UpdateModel)
    @controller.mark_duplex(Category.IndexModel, use_event=True)
    @check_participant_role(controller, ParticipantRole.OWNER)
    @controller.database_searcher(Category)
    @controller.marshal_ack(Category.IndexModel)
    def update_category(
        self,
        event: DuplexEvent,
        name: str | None,
        description: str | None,
        community: Community,
        category: Category,
    ):
        if name is not None:
            category.name = name
        if description is not None:
            category.description = description

        db.session.commit()
        event.emit_convert(category, self.room_name(community.id))
        return category

    class DeleteModel(CommunityIdModel):
        category_id: int

    @controller.argument_parser(DeleteModel)
    @controller.mark_duplex(Category.IndexModel, use_event=True)
    @check_participant_role(controller, ParticipantRole.OWNER)
    @controller.database_searcher(Category)
    @controller.force_ack()
    def delete_category(
        self,
        event: DuplexEvent,
        community: Community,
        category: Category,
    ):
        category.delete()
        db.session.commit()
        event.emit_convert(
            room=self.room_name(community_id=community.id),
            community_id=community.id,
            category_id=category.id,
        )

    class MoveModel(DeleteModel):
        next_id: int = None

    @controller.argument_parser(MoveModel)
    @controller.mark_duplex(Category.IndexModel, use_event=True)
    @check_participant_role(controller, ParticipantRole.OWNER)
    @controller.database_searcher(Category)
    @controller.marshal_ack(Category.IndexModel)
    def move_category(
        self,
        event: DuplexEvent,
        community: Community,
        category: Category,
        next_id: int | None,
    ):
        category.move(next_id)
        db.session.commit()
        event.emit_convert(category, self.room_name(community.id))
        return category
