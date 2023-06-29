from __future__ import annotations

from flask_fullstack import ResourceController, counter_parser
from flask_restx import Resource

from communities.base import check_participant
from communities.tasks.discussion_db import TaskDiscussionMessage

controller = ResourceController(
    "cs-task-discussion",
    path="/communities/<int:community_id>/tasks/<int:task_id>/discussion/"
    "<int:discussion_id>/",
)

MESSAGES_PER_REQUEST: int = 20


@controller.route("/")
class TaskDiscussionMessageLister(Resource):
    @check_participant(controller)
    @controller.argument_parser(counter_parser)
    @controller.lister(MESSAGES_PER_REQUEST, TaskDiscussionMessage.IndexModel)
    def get(
        self,
        discussion_id: int,
        start: int,
        finish: int,
    ) -> list[TaskDiscussionMessage]:
        return TaskDiscussionMessage.find_paginated(
            offset=start,
            limit=finish - start,
            discussion_id=discussion_id,
        )
