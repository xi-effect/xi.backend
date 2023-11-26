from __future__ import annotations

from datetime import datetime

from flask_fullstack import DuplexEvent, EventSpace
from flask_socketio import join_room, leave_room
from pydantic import BaseModel

from common import EventController
from common.utils import check_files
from communities.base.meta_db import Community
from communities.base.roles_db import PermissionType
from communities.base.utils import check_permission
from communities.tasks.tasks_db import Task, TaskEmbed
from users.users_db import User

controller: EventController = EventController()


@controller.route()
class TasksEventSpace(EventSpace):
    @classmethod
    def room_name(cls, community_id: int) -> str:
        return f"cs-tasks-{community_id}"

    class CommunityIdModel(BaseModel):
        community_id: int

    class TaskIdsModel(CommunityIdModel):
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
        checked_files: set[int] = check_files(controller, files)
        task: Task = Task.create(
            user.id, community.id, page_id, name, description, opened, closed
        )

        TaskEmbed.add_files(checked_files, task_id=task.id)
        event.emit_convert(task, self.room_name(community.id))
        return task

    class UpdateModel(Task.UpdateModel, BaseModel):
        files: list[int] | None = None

    class UpdateTaskModel(UpdateModel, TaskIdsModel):
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
            TaskEmbed.update_files(check_files(controller, files), task_id=task.id)

        task.update(**kwargs)
        event.emit_convert(task, room=self.room_name(community.id))
        return task

    @controller.argument_parser(TaskIdsModel)
    @controller.mark_duplex(TaskIdsModel, use_event=True)
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
