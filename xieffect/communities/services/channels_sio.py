from __future__ import annotations

from flask_socketio import join_room, leave_room
from pydantic import BaseModel

from common import DuplexEvent, EventController, EventSpace, db
from .channels_db import ChannelCategory, MAX_CHANNELS
from ..base.meta_utl import check_participant_role
from ..base.meta_db import ParticipantRole, Community

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
        position: int = None

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
        position: int,
    ):
        response = community.categories

        # Check category limit
        if len(response) == MAX_CHANNELS:
            controller.abort(409, "Over limit: Too many categories")

        # Create a category in empty list
        if len(response) == 0:
            prev_id = None
            next_id = None

        else:
            # Create a category at the end of the list
            if position is None:
                prev_cat = ChannelCategory.find_by_next_id(community.id, None)
                prev_id = prev_cat.id
                next_id = None

            # Create a category at the top of the list
            elif position == 0:
                prev_cat = ChannelCategory.find_by_prev_id(community.id, None)
                prev_id = None
                next_id = prev_cat.id

            else:
                prev_cat = ChannelCategory.find_by_id(position)
                # Checking if the previous category exists
                if prev_cat is None or prev_cat.community_id != community.id:
                    # Create a category at the end of the list
                    prev_cat = ChannelCategory.find_by_next_id(community.id, None)
                    prev_id = prev_cat.id
                    next_id = None
                else:
                    prev_id = prev_cat.id
                    next_id = prev_cat.next_category_id

        category = ChannelCategory.create(
            name,
            description,
            prev_id,
            next_id,
            community.id,
        )

        if len(response) > 0:
            if position is None:
                prev_cat.next_category_id = category.id
            elif position == 0:
                prev_cat.prev_category_id = category.id
            else:
                prev_cat.next_category.prev_category_id = category.id
                prev_cat.next_category_id = category.id

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

    class MoveModel(CommunityIdModel):
        category_id: int
        position: int

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
        position: int
    ):
        def cut_it(cat):
            """Cuts category and stitches side IDs"""
            if cat.prev_category_id is not None and cat.next_category_id is not None:
                cat.prev_category.next_category_id = cat.next_category_id
                cat.next_category.prev_category_id = cat.prev_category_id
            elif cat.prev_category_id is not None:
                cat.prev_category.next_category_id = None
                cat.next_category.prev_category_id = cat.prev_category_id
            else:
                cat.prev_category.next_category_id = cat.next_category_id
                cat.next_category.prev_category_id = None
            return cat

        def post_end(cat):
            """Inserts a category at the end of the list"""
            cut_it(cat)
            prev_cat = ChannelCategory.find_by_next_id(community.id, None)
            prev_cat.next_category_id = cat.id
            cat.prev_category_id = prev_cat.id
            cat.next_category_id = None
            return cat

        def post_top(cat):
            """Inserts a category at the top of the list"""
            cut_it(cat)
            next_cat = ChannelCategory.find_by_prev_id(community.id, None)
            next_cat.prev_category_id = cat.id
            cat.prev_category_id = None
            cat.next_category_id = next_cat.id
            return cat

        def post_middle(cat, pos):
            """Inserts a category at the list"""
            cut_it(cat)
            prev_cat = ChannelCategory.find_by_id(pos)
            cat.prev_category_id = prev_cat.id
            cat.next_category_id = prev_cat.next_category_id
            prev_cat.next_category.prev_category_id = cat.id
            prev_cat.next_category_id = cat.id
            return cat

        if position != category.prev_category_id:
            if position is None:
                if category.next_category_id is not None:
                    post_end(category)

            if position == 0:
                if category.prev_category_id is not None:
                    post_top(category)

            else:
                previous_cat = ChannelCategory.find_by_next_id(community.id, None)
                if position == previous_cat.id:
                    post_end(category)
                else:
                    post_middle(category, position)

        db.session.commit()
        event.emit_convert(category, self.room_name(community.id))
        return category
