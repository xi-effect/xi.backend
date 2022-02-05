from flask_restx import Resource

from common import Namespace, User, counter_parser
from .results_db import TestResult

result_namespace: Namespace = Namespace("result", path="/results/")
# result_dict["percent"] = (result_dict["total-answers"] / 100) * result_dict["right-answers"]
short_result_model = result_namespace.model("ShortResult", TestResult.marshal_models["short-result"])
full_result_model = result_namespace.model("FullResult", TestResult.marshal_models["full-result"])


@result_namespace.route("/modules/<int:module_id>/")
class PagesResult(Resource):
    @result_namespace.jwt_authorizer(User)
    @result_namespace.argument_parser(counter_parser)
    # TODO @result_namespace.database_searcher(Module, use_session=True)  # deleted modules?
    @result_namespace.lister(50, short_result_model)
    def post(self, session, module_id: int, user: User, start: int, finish: int):
        return TestResult.find_by_module(session, user.id, module_id, start, finish - start)


@result_namespace.route("/<int:testresult_id>/")
class Result(Resource):
    @result_namespace.jwt_authorizer(User, check_only=True)
    @result_namespace.database_searcher(TestResult)
    @result_namespace.marshal_with(full_result_model)
    def get(self, testresult: TestResult):
        return testresult

    @result_namespace.jwt_authorizer(User, check_only=True)
    @result_namespace.database_searcher(TestResult, use_session=True)
    @result_namespace.a_response()
    def delete(self, session, testresult: TestResult) -> None:
        testresult.delete(session)
