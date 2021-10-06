from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restx import Resource

from main import versions


class Version(Resource):  # [GET] /<app_name>/version/
    def get(self, app_name: str):
        if app_name.upper() in versions.keys():
            return {"a": versions[app_name.upper()]}
        else:
            return {"a": "No such app"}, 400


class UploadAppUpdate(Resource):  # POST /<app_name>/
    @jwt_required()
    def post(self, app_name: str):
        if get_jwt_identity() != "admin@admin.admin":
            return {"a": "Access denied"}

        app_name = app_name.upper()
        if app_name == "OCT":
            with open("OlimpCheck.jar", "wb") as f:
                f.write(request.data)
            return {"a": "Success"}
        else:
            return {"a": "App update not supported"}
