from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import Namespace, ResponseDoc
from main import versions
from users import User

basic_namespace: Namespace = Namespace("basic", path="/")


@basic_namespace.route("/")
class HelloWorld(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("test")

    def get(self):
        return {"hello": "word"}

    @basic_namespace.jwt_authorizer(User, use_session=False)
    @basic_namespace.argument_parser(parser)
    def post(self, test: str, user: User):
        print(f"Got {test} in the field 'test', said hello")
        print(f"User, who asked was {user.email}")
        return {"hello": test}


@basic_namespace.route("/status/")
class ServerMessenger(Resource):
    @basic_namespace.doc_responses(ResponseDoc(description="Message about server status"))
    def get(self):
        """ Want a secret?. [I managed to insert this cool link here!](https://autopilottonowhere.com) """
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
