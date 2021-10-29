from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restx import Resource

from main import versions
from componets import Namespace


application_namespace: Namespace = Namespace("app", path="/<app_name>/")


@application_namespace.route("/version/")
class Version(Resource):  # [GET] /<app_name>/version/
    @application_namespace.a_response()
    def get(self, app_name: str) -> str:
        if app_name.upper() in versions.keys():
            return versions[app_name.upper()]
        else:
            return "No such app"


@application_namespace.route("/")
class UploadAppUpdate(Resource):  # DEPRECATED
    @jwt_required()
    @application_namespace.a_response()
    def post(self, app_name: str) -> str:
        if get_jwt_identity() != "admin@admin.admin":  # doesn't work anymore
            return "Access denied"

        app_name = app_name.upper()
        if app_name == "OCT":
            with open("OlimpCheck.jar", "wb") as f:
                f.write(request.data)
            return "Success"
        else:
            return "App update not supported"
