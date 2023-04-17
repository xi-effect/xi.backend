from __future__ import annotations

from datetime import datetime

from flask_fullstack import counter_parser, RequestParser
from flask_restx import Resource

from common import ResourceController, User
from communities.base.meta_db import Community, Participant
from communities.tasks.main_db import Task, TaskFilter, TASKS_PER_PAGE
from communities.utils import check_participant

controller = ResourceController(
    "cs-student-tasks", path="/communities/<int:community_id>/tasks/student/"
)


@controller.route("/")
class StudentTasks(Resource):
    parser: RequestParser = counter_parser.copy()
    parser.add_argument(
        "filter",
        type=TaskFilter.as_input(),
        required=True,
        dest="task_filter",
    )

    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @check_participant(controller, use_participant=True)
    @controller.lister(TASKS_PER_PAGE, Task.IndexModel)
    def get(
        self,
        community: Community,
        start: int,
        finish: int,
        participant: Participant,
        task_filter: TaskFilter,
    ):
        return Task.get_paginated_tasks(
            start,
            finish - start,
            participant,
            task_filter,
            community_id=community.id,
            deleted=None,
        )


@controller.route("/<int:task_id>/")
class StudentTaskGet(Resource):
    @controller.jwt_authorizer(User)
    @check_participant(controller)
    @controller.database_searcher(Task)
    @controller.marshal_with(Task.FullModel)
    def get(self, community: Community, task: Task):
        if task.community_id != community.id or task.opened > datetime.utcnow():
            controller.abort(404, Task.not_found_text)
        return task
