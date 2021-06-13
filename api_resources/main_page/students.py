from flask_restful import Resource
from flask_restful.reqparse import RequestParser

from api_resources.base.checkers import jwt_authorizer
from database import User


class SchoolIntegration(Resource):
    @jwt_authorizer(User)
    def get(self, user: User):
        pass


class Activities(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("time", type=int)

    @jwt_authorizer(User)
    def get(self, user: User):
        pass


class Tasks(Resource):
    @jwt_authorizer(User)
    def post(self, task_id: int, user: User):
        pass

    @jwt_authorizer(User)
    def put(self, task_id: int, user: User):
        pass

    @jwt_authorizer(User)
    def delete(self, task_id: int, user: User):
        pass


class Notif(Resource):
    @jwt_authorizer(User)
    def delete(self, notification_id: int, user: User):
        pass
