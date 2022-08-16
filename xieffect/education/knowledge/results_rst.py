from flask_restx import Resource

from common import ResourceController, User, counter_parser
from .results_db import TestResult

controller = ResourceController("result", path="/results/")


@controller.route("/modules/<int:module_id>/")
class PagesResult(Resource):
    @controller.jwt_authorizer(User)
    @controller.argument_parser(counter_parser)
    # TODO @result_namespace.database_searcher(Module, use_session=True)  # deleted modules?
    @controller.lister(50, TestResult.ShortModel)
    def post(self, session, module_id: int, user: User, start: int, finish: int):
        return TestResult.find_by_module(session, user.id, module_id, start, finish - start)


@controller.route("/<int:testresult_id>/")
class Result(Resource):
    @controller.jwt_authorizer(User, check_only=True)
    @controller.database_searcher(TestResult)
    @controller.marshal_with(TestResult.FullModel)
    def get(self, testresult: TestResult):
        return testresult

    @controller.jwt_authorizer(User, check_only=True)
    @controller.database_searcher(TestResult, use_session=True)
    @controller.a_response()
    def delete(self, session, testresult: TestResult) -> None:
        testresult.delete(session)
