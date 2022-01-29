import json
from typing import Union

from flask import request, send_from_directory, redirect
from flask_restx import Resource, marshal
from flask_restx.reqparse import RequestParser

from common import Namespace, ResponseDoc, User, counter_parser
from .results_db import TestResult
from .interaction_db import TestModuleSession, TestPointSession

result_namespace: Namespace = Namespace("result", path='/modules/<int:module_id>/result/')


# TODO /modules/<module_id>/results/ -> пагинация, минимальная информация
# TODO использовать user из авторизации
# @result_namespace.route("/modules/<int:module_id>/result/")
# class PagesResult(Resource):
#     @result_namespace.lister(10):

# TODO /modules/<module_id>/results/<result_id>/ -> GET & DELETE
@result_namespace.route("/<int:result_id>/")
class Result(Resource):
    @result_namespace.jwt_authorizer(User, use_session=True)
    def get(self, session, result_id):
        entry: TestResult = TestResult.find_by_id(session, result_id)
        return entry.result

    @result_namespace.jwt_authorizer(User, use_session=True)
    def delete(self, session, result_id):
        entry: TestResult = TestResult.find_by_id(session, result_id)
        return session.delete(entry)
