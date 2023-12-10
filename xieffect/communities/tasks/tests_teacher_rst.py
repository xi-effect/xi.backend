from __future__ import annotations

from flask_fullstack import counter_parser, RequestParser
from flask_restx import Resource

from common import ResourceController
from communities.base.meta_db import Community, PermissionType
from communities.base.utils import check_permission
from communities.tasks.tasks_db import TaskFilter, TaskOrder, TASKS_PER_PAGE
from communities.tasks.tests_db import Test
from communities.tasks.utils import test_finder
from users.users_db import User

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
        dest="test_order",
    )

    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @controller.lister(TASKS_PER_PAGE, Test.IndexModel)
    def get(
        self,
        community: Community,
        start: int,
        finish: int,
        test_order: TaskOrder,
        test_filter: TaskFilter,
    ):
        return Test.get_paginated(
            start,
            finish - start,
            test_filter,
            test_order,
            community_id=community.id,
            deleted=None,
        )


@controller.route("/<int:test_id>/")
class TeacherTestGet(Resource):
    @controller.jwt_authorizer(User)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @test_finder(controller)
    @controller.marshal_with(Test.FullModel)
    def get(self, test: Test):
        return test
