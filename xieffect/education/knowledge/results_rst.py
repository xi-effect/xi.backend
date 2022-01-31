from flask_restx import Resource, fields, Model

from common import Namespace, User, counter_parser, ResponseDoc
from .results_db import TestResult

result_namespace: Namespace = Namespace("result", path="/modules/<int:module_id>/result/")
result_dict = {
    "right-answers": fields.Integer,
    "total-answers": fields.Integer,
    "page-id": fields.Integer,
    "point-id": fields.Integer,
    "answers": fields.Raw
}
# result_dict["percent"] = (result_dict["total-answers"] / 100) * result_dict["right-answers"]
result_model = Model("ResultModel", {
    "module-name": fields.String,
    "author-name": fields.String,
    "author-id": fields.Integer,
    "result": fields.List(fields.Nested(result_dict))
})


@result_namespace.route("/")
class PagesResult(Resource):
    @result_namespace.doc_responses(ResponseDoc(200, "", result_model))
    @result_namespace.jwt_authorizer(User)
    @result_namespace.argument_parser(counter_parser)
    @result_namespace.lister(50, result_model)
    def post(self, session, module_id: int, user: User, start: int, finish: int):
        return TestResult.find_by_module(session, user.id, module_id, start, finish - start)


@result_namespace.route("/<int:result_id>/")
class Result(Resource):
    @result_namespace.doc_responses(ResponseDoc(200, "", result_model))
    @result_namespace.jwt_authorizer(User, use_session=True)
    def get(self, session, result_id, user: User, module_id: int):
        entry: TestResult = TestResult.find_by_id(session, result_id)
        return entry.result

    @result_namespace.jwt_authorizer(User, use_session=True)
    @result_namespace.a_response()
    def delete(self, session, result_id, user: User, module_id: int) -> None:
        entry: TestResult = TestResult.find_by_id(session, result_id)
        session.delete(entry)
