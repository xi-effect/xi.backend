from __future__ import annotations

from typing import Any

from flask_fullstack import DuplexEvent, EventSpace
from flask_socketio import join_room, leave_room
from pydantic import BaseModel

from common import EventController, User
from vault import File
from .tasks_db import Task, TaskEmbed
from ..base import Community, ParticipantRole
from ..utils import check_participant

# Set Tasks behavior here
FILES_LIMIT = 10

controller = EventController()


def check_files(files: list[int]) -> list[int]:
    """
    - Delete duplicates from a list of file ids.
    - Check list length limit.
    - Check if all files exist.

    Return checked list with file ids.
    """
    files = list(set(files))
    if len(files) > FILES_LIMIT:
        controller.abort(400, "Too many files")
    for file_id in files:
        if File.find_by_id(file_id) is None:
            controller.abort(404, File.not_found_text)
    return files


@controller.route()
class TasksEventSpace(EventSpace):
    @classmethod
    def room_name(cls, community_id: int) -> str:
        return f"cs-tasks-{community_id}"

    class CommunityIdModel(BaseModel):
        community_id: int

    class TaskIdModel(BaseModel):
        task_id: int

    @controller.argument_parser(CommunityIdModel)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.force_ack()
    def open_tasks(self, community: Community):
        join_room(self.room_name(community.id))  # TODO pragma: no cover | task

    @controller.argument_parser(CommunityIdModel)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.force_ack()
    def close_tasks(self, community: Community):
        leave_room(self.room_name(community.id))  # TODO pragma: no cover | task

    class CreationModel(Task.CreationBaseModel, CommunityIdModel):
        files: list[int] = []

    @controller.argument_parser(CreationModel)
    @controller.mark_duplex(Task.FullModel, use_event=True)
    @check_participant(controller, role=ParticipantRole.OWNER, use_user=True)
    @controller.marshal_ack(Task.FullModel)
    def new_task(
        self,
        event: DuplexEvent,
        community: Community,
        user: User,
        page_id: int,
        name: str,
        description: str | None,
        files: list[int],
    ):
        task = Task.create(user.id, community.id, page_id, name, description)
        if len(files) != 0:
            TaskEmbed.add_files(task.id, check_files(files))
        event.emit_convert(task, self.room_name(community.id))
        return task

    class UpdateModel(CommunityIdModel, TaskIdModel):
        page_id: int = None
        name: str = None
        description: str = None
        files: list[int] = None

        # Override dict method of BaseModel to set "exclude_none" argument on True
        def dict(self, *args, **kwargs) -> dict[str, Any]:  # noqa: A003
            kwargs["exclude_none"] = True
            return super().dict(*args, **kwargs)

    @controller.argument_parser(UpdateModel)
    @controller.mark_duplex(UpdateModel, use_event=True)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.database_searcher(Task)
    @controller.force_ack()
    def update_task(
        self,
        event: DuplexEvent,
        community: Community,
        task: Task,
        **kwargs,
    ):
        if task.community_id != community.id:  # TODO pragma: no cover | func
            controller.abort(404, Task.not_found_text)

        files = kwargs.pop("files", None)
        if files is not None:
            new_files = check_files(files)
            old_files = TaskEmbed.get_task_files(task.id)
            add_files = list(set(new_files).difference(old_files))
            remove_files = list(set(old_files).difference(new_files))
            TaskEmbed.delete_files(task.id, remove_files)
            TaskEmbed.add_files(task.id, add_files)

        Task.update(task.id, **kwargs)
        event.emit_convert(
            room=self.room_name(community.id),
            community_id=community.id,
            task_id=task.id,
        )

    class DeleteModel(CommunityIdModel, TaskIdModel):
        pass

    @controller.argument_parser(DeleteModel)
    @controller.mark_duplex(DeleteModel, use_event=True)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.database_searcher(Task)
    @controller.force_ack()
    def delete_task(self, event: DuplexEvent, community: Community, task: Task):
        if task.community_id != community.id:  # TODO pragma: no cover | func
            controller.abort(404, Task.not_found_text)
        task.deleted = True
        event.emit_convert(
            room=self.room_name(community.id),
            community_id=community.id,
            task_id=task.id,
        )
