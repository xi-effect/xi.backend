from __future__ import annotations

from flask_fullstack import counter_parser, RequestParser
from flask_restx import Resource

from common import ResourceController, User
from .main_db import Task, TaskFilter, TaskOrder, TASKS_PER_PAGE
from ..base import Community, Participant, PermissionType, check_permission

controller = ResourceController(
    "cs-teacher-tasks", path="/communities/<int:community_id>/tasks/"
)


@controller.route("/")
class TeacherTasks(Resource):
    parser: RequestParser = counter_parser.copy()
    parser.add_argument(
        "filter",
        type=TaskFilter.as_input(),
        required=True,
        dest="task_filter",
    )
    parser.add_argument(
        "order",
        type=TaskOrder.as_input(),
        required=True,
        dest="task_order",
    )

    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @check_permission(controller, PermissionType.MANAGE_TASKS, use_participant=True)
    @controller.lister(TASKS_PER_PAGE, Task.IndexModel)
    def get(
        self,
        community: Community,
        start: int,
        finish: int,
        participant: Participant,
        task_order: TaskOrder,
        task_filter: TaskFilter,
    ):
        return Task.get_paginated_tasks(
            start,
            finish - start,
            participant,
            task_filter,
            task_order,
            community_id=community.id,
            deleted=None,
        )


@controller.route("/<int:task_id>/")
class TeacherTaskGet(Resource):
    @controller.jwt_authorizer(User)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @controller.database_searcher(Task)
    @controller.marshal_with(Task.FullModel)
    def get(self, community: Community, task: Task):
        if task.community_id != community.id:
            controller.abort(404, Task.not_found_text)
        return task
