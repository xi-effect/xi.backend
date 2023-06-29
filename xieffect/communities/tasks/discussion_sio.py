from __future__ import annotations

from flask_fullstack import EventSpace, DuplexEvent
from flask_socketio import join_room, leave_room
from pydantic import BaseModel

from common import EventController, User
from communities.base import check_participant
from communities.tasks.discussion_db import TaskDiscussionMessage, TaskDiscussion

controller = EventController()


@controller.route()
class TaskDiscussionsEventSpace(EventSpace):
    @classmethod
    def room_name(cls, discussion_id: int) -> str:
        return f"cs-task-discussions-{discussion_id}"

    class DiscussionIdModel(BaseModel):
        community_id: int
        discussion_id: int

    @controller.argument_parser(DiscussionIdModel)
    @check_participant(controller)
    @controller.force_ack()
    def open_task_discussion(self, discussion_id: int):
        join_room(self.room_name(discussion_id))

    @controller.argument_parser(DiscussionIdModel)
    @check_participant(controller)
    @controller.force_ack()
    def close_task_discussion(self, discussion_id: int):
        leave_room(self.room_name(discussion_id))

    class DiscussionCreateModel(BaseModel):
        community_id: int
        task_id: int
        student_id: int

    @controller.argument_parser(DiscussionCreateModel)
    @controller.mark_duplex(TaskDiscussion.IndexModel, use_event=True)
    @check_participant(controller, use_community=False)
    @controller.marshal_ack(TaskDiscussion.IndexModel)
    def new_task_discussion(
        self,
        event: DuplexEvent,
        task_id: int,
        student_id: int,
    ) -> TaskDiscussion:
        discussion: TaskDiscussion = TaskDiscussion.create(
            task_id=task_id,
            student_id=student_id,
        )
        event.emit_convert(discussion)
        return discussion

    class DiscussionMessageCreateModel(TaskDiscussionMessage.CreateModel):
        community_id: int
        files: list[int] = []

    @controller.argument_parser(DiscussionMessageCreateModel)
    @controller.mark_duplex(TaskDiscussionMessage.CreateModel, use_event=True)
    @check_participant(controller, use_community=False)
    @controller.marshal_ack(TaskDiscussionMessage.CreateModel)
    def new_task_discussion_message(
        self,
        event: DuplexEvent,
        discussion_id: int,
        sender_id: int,
        content: dict[str, str],
        files: list[int],
    ) -> TaskDiscussionMessage:
        message: TaskDiscussionMessage = TaskDiscussionMessage.create(
            content=content,
            sender_id=sender_id,
            discussion_id=discussion_id,
            files=files,
        )
        event.emit_convert(message, room=self.room_name(discussion_id))
        return message

    class DiscussionMessageUpdateModel(DiscussionIdModel):
        message_id: int
        content: dict[str, str]
        files: list[int]

    @controller.doc_abort(403, "Permission denied")
    @controller.argument_parser(DiscussionMessageUpdateModel)
    @controller.mark_duplex(TaskDiscussionMessage.CreateModel, use_event=True)
    @check_participant(controller, use_community=False, use_user=True)
    @controller.force_ack()
    def update_task_discussion_message(
        self,
        event: DuplexEvent,
        user: User,
        discussion_id: int,
        message_id: int,
        content: dict[str, str],
        files: list[int],
    ):
        message: TaskDiscussionMessage = TaskDiscussionMessage.find_by_id(message_id)

        if message.sender_id != user.id:
            controller.abort(403, "Permission denied")

        message.update(content=content, files=files)
        event.emit_convert(message, room=self.room_name(discussion_id))

    class TaskDiscussionMessagePinModel(DiscussionIdModel):
        message_id: int
        pinned: bool

    @controller.doc_abort(403, "Permission denied")
    @controller.argument_parser(TaskDiscussionMessagePinModel)
    @controller.mark_duplex(TaskDiscussionMessage.CreateModel, use_event=True)
    @check_participant(controller, use_community=False, use_user=True)
    @controller.force_ack()
    def pin_task_discussion_message(
        self,
        event: DuplexEvent,
        user: User,
        discussion_id: int,
        message_id: int,
        pinned: bool,
    ):
        message: TaskDiscussionMessage = TaskDiscussionMessage.find_by_id(message_id)

        if message.sender_id != user.id:
            controller.abort(403, "Permission denied")

        message.pinned = pinned
        event.emit_convert(message, room=self.room_name(discussion_id))
