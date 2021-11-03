from requests import Session
from flask import jsonify
from flask_restx import Resource, Namespace
from flask_restx.reqparse import RequestParser
from jwt import decode

from setup import app, auth_store

reglog_namespace: Namespace = Namespace("reglog", path="/")


def get_identity(jwt_cookie: str) -> int:
    jwt: str = jwt_cookie.partition("access_token_cookie=")[2].partition(";")[0]
    return decode(jwt, key=app.config["JWT_SECRET_KEY"], algorithms="HS256")["sub"]


@reglog_namespace.route("/auth/")
class UserLogin(Resource):  # [POST] /auth/
    parser: RequestParser = RequestParser()
    parser.add_argument("email", required=True, help="User's email")
    parser.add_argument("password", required=True, help="User's password")

    @reglog_namespace.expect(parser)
    def post(self):
        """ Tries to log in with credentials given """
        session = Session()
        response = session.post("https://xieffect.pythonanywhere.com/auth/", json=self.parser.parse_args())
        if response.status_code == 200 and response.json() == {"a": "Success"}:
            auth_store[get_identity((header := response.headers["Set-Cookie"]))] = session
            response = jsonify({"a": True})
            response.headers.add("Set-Cookie", header)
            return response
        return {"a": False}
