from flask_restx import Resource, fields, Model

from common import Namespace, User
from .results_db import TestResult

result_namespace: Namespace = Namespace("result", path='/modules/<int:module_id>/result/')
result_dict = {
    'right-answers': fields.Integer,
    'total-answers': fields.Integer,
    'percent': fields.Integer,
}
# result_dict['percent'] = (result_dict['total-answers'] / 100) * result_dict['right-answers']
result_model = Model('ResultModel', {
    'module-name': fields.String,
    'author-name': fields.String,
    'author-id': fields.Integer,
    'result': fields.List(fields.Nested(result_dict))
})


# TODO /modules/<module_id>/results/ -> пагинация, минимальная информация
# TODO использовать user из авторизации
# @result_namespace.route("/modules/<int:module_id>/result/")
# class PagesResult(Resource):
#     @result_namespace.lister(10):

# TODO /modules/<module_id>/results/<result_id>/ -> GET & DELETE
@result_namespace.route("/<int:result_id>/")
class Result(Resource):
    @result_namespace.jwt_authorizer(User, use_session=True)
    def get(self, session, result_id, user: User, module_id: int):
        entry: TestResult = TestResult.find_by_id(session, result_id)
        return entry.result

    @result_namespace.jwt_authorizer(User, use_session=True)
    @result_namespace.a_response()
    def delete(self, session, result_id, user: User, module_id: int) -> None:
        entry: TestResult = TestResult.find_by_id(session, result_id)
        session.delete(entry)


m
