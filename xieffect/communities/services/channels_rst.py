from __future__ import annotations

from flask_socketio import join_room, leave_room
from pydantic import BaseModel

from common import DuplexEvent, EventController, EventSpace, db
from .channels_db import ChannelCategory, Channel, ChannelType, MAX_CHANNELS
from ..base.meta_db import ParticipantRole, Community
from ..base.meta_utl import check_participant_role

controller = EventController()


@controller.route()
class ChannelEventSpace(EventSpace):
    @classmethod
    def room_name(cls, community_id: int):
        return f"community-{community_id}"

    class CommunityIdModel(BaseModel):
        community_id: int

    @controller.argument_parser(CommunityIdModel)
    @check_participant_role(controller, ParticipantRole.BASE)
    @controller.force_ack()
    def open_channel(self, community: Community):
        join_room(self.room_name(community.id))

    @controller.argument_parser(CommunityIdModel)
    @check_participant_role(controller, ParticipantRole.BASE)
    @controller.force_ack()
    def close_channel(self, community: Community):
        leave_room(self.room_name(community.id))

    class CreateModel(Channel.CreateModel, CommunityIdModel):
        category_id: int = None
        next_id: int = None

    @controller.doc_abort(409, "Over limit")
    @controller.argument_parser(CreateModel)
    @controller.mark_duplex(Channel.IndexModel, use_event=True)
    @check_participant_role(controller, ParticipantRole.OWNER)
    @controller.database_searcher(
        ChannelCategory,
        input_field_name="category_id",
        result_field_name="category",
    )
    @controller.marshal_ack(Channel.IndexModel)
    def new_channel(
        self,
        event: DuplexEvent,
        name: str,
        channel_type: ChannelType,
        community: Community,
        category: ChannelCategory | None,
        next_id: int | None,
    ):
        channels_count = create_count = len(community.channels)
        # if category is not None:
        #     create_count = len(category.channels)
        #     channels_count += count_in_category

        # Check category limit
        if channels_count == MAX_CHANNELS:
            controller.abort(409, "Over limit: Too many channels")

        # Create a category in empty list
        if create_count == 0:
            prev_chan = None
            next_chan = None
        else:
            next_chan = next_id

            # Add to end to list
            if next_id is None:
                old_chan = Channel.find_by_next_id(community.id, None)
                prev_chan = old_chan.id

            # Add to the list
            else:
                old_chan = Channel.find_by_id(next_id)
                prev_chan = old_chan.prev_channel_id

        channel = Channel.create(
            name,
            channel_type,
            prev_chan,
            next_chan,
            community.id,
            category.id
        )

        # Stitching
        if channel.next_channel_id is not None:
            channel.next_channel.prev_channel_id = channel.id
        if category.prev_category_id is not None:
            channel.prev_channel.next_channel_id = channel.id

        db.session.commit()
        event.emit_convert(channel, self.room_name(community.id))
        return channel
