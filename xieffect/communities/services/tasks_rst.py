from __future__ import annotations

from flask_fullstack import counter_parser
from flask_restx import Resource

from common import ResourceController, User
from .tasks_db import Task
from ..base import Community, ParticipantRole
from ..utils import check_participant

# Set Tasks behavior here
TASKS_PER_PAGE = 48

controller = ResourceController(
    "communities-tasks", path="/communities/<int:community_id>/tasks/"
)


@controller.route("/")
class Tasks(Resource):
    @controller.jwt_authorizer(User)
    @controller.argument_parser(counter_parser)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.lister(TASKS_PER_PAGE, Task.IndexModel)
    def get(self, community: Community, start: int, finish: int):
        return Task.find_paginated_by_kwargs(
            start,
            finish - start,
            Task.updated,
            community_id=community.id,
            deleted=False,
        )


@controller.route("/<int:task_id>/")
class TaskGet(Resource):
    @controller.jwt_authorizer(User)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.database_searcher(Task, error_code="404 ")
    @controller.marshal_with(Task.FullModel)
    def get(self, community: Community, task: Task):
        if task.community_id != community.id:  # TODO pragma: no cover | func
            controller.abort(404, Task.not_found_text)
        return task
