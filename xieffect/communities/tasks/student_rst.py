from __future__ import annotations

from datetime import datetime

from flask_fullstack import counter_parser, RequestParser
from flask_restx import Resource

from common import ResourceController
from communities.base.meta_db import Community
from communities.base.utils import check_participant
from communities.tasks.tasks_db import Task, TaskFilter, TASKS_PER_PAGE
from users.users_db import User

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

    @controller.argument_parser(parser)
    @check_participant(controller)
    @controller.lister(TASKS_PER_PAGE, Task.IndexModel)
    def get(
        self,
        community: Community,
        start: int,
        finish: int,
        task_filter: TaskFilter,
    ):
        return Task.get_paginated(
            start,
            finish - start,
            task_filter,
            community_id=community.id,
            open_only=True,
            deleted=None,
        )


@controller.route("/<int:task_id>/")
class StudentTaskGet(Resource):
    @check_participant(controller)
    @controller.database_searcher(Task)
    @controller.marshal_with(Task.FullModel)
    def get(self, community: Community, task: Task):
        if task.community_id != community.id or task.opened > datetime.utcnow():
            controller.abort(404, Task.not_found_text)
        return task
