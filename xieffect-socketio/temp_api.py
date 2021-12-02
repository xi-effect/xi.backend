from requests import post
from flask import jsonify
from flask_restx import Resource, Namespace
from flask_restx.reqparse import RequestParser

reglog_namespace: Namespace = Namespace("reglog", path="/")


@reglog_namespace.route("/auth/")
class UserLogin(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("email", required=True, help="User's email")
    parser.add_argument("password", required=True, help="User's password")

    @reglog_namespace.expect(parser)
    def post(self):
        """ Tries to log in with credentials given """
        response = post("https://xieffect.pythonanywhere.com/auth/", json=self.parser.parse_args())
        if response.status_code == 200 and response.json() == {"a": "Success"}:
            header = response.headers["Set-Cookie"]
            response = jsonify({"a": True})
            response.headers.add("Set-Cookie", header)
            return response
        return {"a": False}
