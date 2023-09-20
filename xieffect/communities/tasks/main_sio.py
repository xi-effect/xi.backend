from __future__ import annotations

from datetime import datetime
from typing import Any

from flask_fullstack import DuplexEvent, EventSpace
from flask_socketio import join_room, leave_room
from pydantic.v1 import BaseModel

from common import EventController, User
from communities.base import check_permission, PermissionType
from communities.base.meta_db import Community
from communities.tasks.main_db import Task, TaskEmbed
from vault import File

# Set Tasks behavior here
FILES_LIMIT: int = 10

controller = EventController()


def check_files(files: list[int]) -> set[int]:
    """
    - Delete duplicates from a list of file ids.
    - Check list length limit.
    - Check if all files exist.

    Return checked list with file ids.
    """
    files: set[int] = set(files)
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
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @controller.force_ack()
    def open_tasks(self, community: Community):
        join_room(self.room_name(community.id))  # TODO pragma: no cover | task

    @controller.argument_parser(CommunityIdModel)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @controller.force_ack()
    def close_tasks(self, community: Community):
        leave_room(self.room_name(community.id))  # TODO pragma: no cover | task

    class CreationModel(Task.CreateModel, CommunityIdModel):
        files: list[int] = []

    @controller.argument_parser(CreationModel)
    @controller.mark_duplex(Task.FullModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_TASKS, use_user=True)
    @controller.marshal_ack(Task.FullModel)
    def new_task(
        self,
        event: DuplexEvent,
        community: Community,
        user: User,
        page_id: int,
        name: str,
        files: list[int],
        description: str | None,
        opened: datetime | None,
        closed: datetime | None,
    ):
        checked_files: set[int] = check_files(files)
        task: Task = Task.create(
            user.id, community.id, page_id, name, description, opened, closed
        )

        TaskEmbed.add_files(checked_files, task_id=task.id)
        event.emit_convert(task, self.room_name(community.id))
        return task

    class UpdateModel(BaseModel):
        page_id: int = None
        name: str = None
        files: list[int] = None
        description: str = None
        opened: datetime = None
        closed: datetime = None

        # Override dict method of BaseModel to set "exclude_none" argument on True
        def dict(self, *args, **kwargs) -> dict[str, Any]:  # noqa: A003
            kwargs["exclude_none"] = True
            return super().dict(*args, **kwargs)

    class UpdateTaskModel(UpdateModel, CommunityIdModel, TaskIdModel):
        pass

    @controller.argument_parser(UpdateTaskModel)
    @controller.mark_duplex(Task.FullModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @controller.database_searcher(Task)
    @controller.marshal_ack(Task.FullModel)
    def update_task(
        self,
        event: DuplexEvent,
        community: Community,
        task: Task,
        **kwargs,
    ):
        if task.community_id != community.id:
            controller.abort(404, Task.not_found_text)

        files: list[int] | None = kwargs.pop("files", None)
        if files is not None:
            new_files: set[int] = check_files(files)
            old_files: set[int] = set(TaskEmbed.get_file_ids(task_id=task.id))
            TaskEmbed.delete_files(old_files - new_files, task_id=task.id)
            TaskEmbed.add_files(new_files - old_files, task_id=task.id)

        task.update(**kwargs)
        event.emit_convert(task, room=self.room_name(community.id))
        return task

    class DeleteModel(CommunityIdModel, TaskIdModel):
        pass

    @controller.argument_parser(DeleteModel)
    @controller.mark_duplex(DeleteModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @controller.database_searcher(Task)
    @controller.force_ack()
    def delete_task(self, event: DuplexEvent, community: Community, task: Task):
        if task.community_id != community.id:
            controller.abort(404, Task.not_found_text)
        task.soft_delete()
        event.emit_convert(
            room=self.room_name(community.id),
            community_id=community.id,
            task_id=task.id,
        )
