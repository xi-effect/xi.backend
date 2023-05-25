from __future__ import annotations

from flask_fullstack import counter_parser, RequestParser
from flask_restx import Resource

from common import ResourceController, User
from communities.base.meta_db import Community, ParticipantRole, Participant
from communities.tasks.main_db import TaskFilter, TaskOrder, TASKS_PER_PAGE
from communities.tasks.tests_db import Test
from communities.utils import check_participant

controller = ResourceController(
    "cs-teacher-tests", path="/communities/<int:community_id>/tests/"
)


@controller.route("/")
class TeacherTests(Resource):
    parser: RequestParser = counter_parser.copy()
    parser.add_argument(
        "filter",
        type=TaskFilter.as_input(),
        required=True,
        dest="test_filter",
    )
    parser.add_argument(
        "order",
        type=TaskOrder.as_input(),
        required=True,
        dest="test_filter",
    )

    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @check_participant(controller, role=ParticipantRole.OWNER, use_participant=True)
    @controller.lister(TASKS_PER_PAGE, Test.IndexModel)
    def get(
        self,
        community: Community,
        start: int,
        finish: int,
        participant: Participant,
        task_order: TaskOrder,
        task_filter: TaskFilter,
    ):
        return Test.get_paginated_tasks(
            start,
            finish - start,
            participant,
            task_filter,
            task_order,
            community_id=community.id,
            deleted=None,
        )


@controller.route("/<int:test_id>/")
class TeacherTestGet(Resource):
    @controller.jwt_authorizer(User)
    @check_participant(controller, role=ParticipantRole.OWNER)
    @controller.database_searcher(Test)
    @controller.marshal_with(Test.FullModel)
    def get(self, community: Community, test: Test):
        if test.community_id != community.id:
            controller.abort(404, Test.not_found_text)
        return test
