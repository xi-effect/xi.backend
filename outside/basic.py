from flask_restful import Resource
from flask_restful.reqparse import RequestParser

from base.checkers import jwt_authorizer, argument_parser
from users import User
from main import versions


class HelloWorld(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("test")

    def get(self):
        return {"hello": "word"}

    @jwt_authorizer(User)
    @argument_parser(parser, "test")
    def post(self, test: str, user: User):
        print(f"Got {test} in the field 'test', said hello")
        print(f"User, who asked was {user.email}")
        return {"hello": test}


class ServerMessenger(Resource):
    def get(self):
        return {"type": 2, "text": "Version: " + versions["API"]}


"""
import requests

position = requests.get('http://api.open-notify.org/iss-now.json').json()["iss_position"]
position = list(map(lambda x: float(x), position.values()))
try:
    return {"type": 2, "text": f"ISS coordinates: {position}."}
except KeyError:
    return {"type": 2, "text": "Couldn't track the ISS"}
"""
