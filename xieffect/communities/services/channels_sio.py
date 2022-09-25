from __future__ import annotations

from flask_socketio import join_room, leave_room
from pydantic import BaseModel

from common import DuplexEvent, EventController, EventSpace, db
from .channels_db import ChannelCategory, MAX_CHANNELS
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

    class CreateModel(ChannelCategory.CreateModel, CommunityIdModel):
        next_id: int = None

    @controller.doc_abort(409, "Over limit")
    @controller.argument_parser(CreateModel)
    @controller.mark_duplex(ChannelCategory.IndexModel, use_event=True)
    @check_participant_role(controller, ParticipantRole.OWNER)
    @controller.marshal_ack(ChannelCategory.IndexModel)
    def new_category(
        self,
        event: DuplexEvent,
        name: str,
        description: str,
        community: Community,
        next_id: int | None,
    ):
        cat_list = community.categories

        # Check category limit
        if len(cat_list) == MAX_CHANNELS:
            controller.abort(409, "Over limit: Too many categories")

        # Create a category in empty list
        if len(cat_list) == 0:
            prev_cat = None
            next_cat = None
        else:
            next_cat = next_id

            # Add to end to list
            if next_id is None:
                old_cat = ChannelCategory.find_by_next_id(community.id, None)
                prev_cat = old_cat.id

            # Add to the list
            else:
                old_cat = ChannelCategory.find_by_id(next_id)
                prev_cat = old_cat.prev_category_id

        category = ChannelCategory.create(
            name,
            description,
            prev_cat,
            next_cat,
            community.id,
        )

        # Stitching
        if category.next_category_id is not None:
            category.next_category.prev_category_id = category.id
        if category.prev_category_id is not None:
            category.prev_category.next_category_id = category.id

        db.session.commit()
        event.emit_convert(category, self.room_name(community.id))
        return category

    class UpdateModel(ChannelCategory.CreateModel, CommunityIdModel):
        category_id: int

    @controller.argument_parser(UpdateModel)
    @controller.mark_duplex(ChannelCategory.IndexModel, use_event=True)
    @check_participant_role(controller, ParticipantRole.OWNER)
    @controller.database_searcher(
        ChannelCategory,
        input_field_name="category_id",
        result_field_name="category",
    )
    @controller.marshal_ack(ChannelCategory.IndexModel)
    def update_category(
        self,
        event: DuplexEvent,
        name: str | None,
        description: str | None,
        community: Community,
        category: ChannelCategory,
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
    @controller.mark_duplex(ChannelCategory.IndexModel, use_event=True)
    @check_participant_role(controller, ParticipantRole.OWNER)
    @controller.database_searcher(
        ChannelCategory,
        input_field_name="category_id",
        result_field_name="category",
    )
    @controller.force_ack()
    def delete_category(
        self,
        event: DuplexEvent,
        community: Community,
        category: ChannelCategory,
    ):
        # Cutting and stitching
        if category.next_category_id is not None:
            category.next_category.prev_category_id = category.prev_category_id
        if category.prev_category_id is not None:
            category.prev_category.next_category_id = category.next_category_id

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
    @controller.mark_duplex(ChannelCategory.IndexModel, use_event=True)
    @check_participant_role(controller, ParticipantRole.OWNER)
    @controller.database_searcher(
        ChannelCategory,
        input_field_name="category_id",
        result_field_name="category",
    )
    @controller.marshal_ack(ChannelCategory.IndexModel)
    def move_category(
        self,
        event: DuplexEvent,
        community: Community,
        category: ChannelCategory,
        next_id: int | None,
    ):
        # Cutting and stitching
        if category.next_category_id is not None:
            category.next_category.prev_category_id = category.prev_category_id
        if category.prev_category_id is not None:
            category.prev_category.next_category_id = category.next_category_id

        # Move to the end of the list
        if next_id is None:
            old_cat = ChannelCategory.find_by_next_id(community.id, None)
            old_cat.next_category_id = category.id
            category.prev_category_id = old_cat.id

        # Moving within a list
        else:
            old_cat = ChannelCategory.find_by_id(next_id)
            category.prev_category_id = old_cat.prev_category_id
            old_cat.prev_category.next_category_id = category.id
            old_cat.prev_category_id = category.id

        category.next_category_id = next_id
        db.session.commit()
        event.emit_convert(category, self.room_name(community.id))
        return category
