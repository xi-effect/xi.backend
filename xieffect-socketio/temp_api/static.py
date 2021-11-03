from flask import send_file
from flask_restx import Resource, Namespace

static_namespace = Namespace("static", path="/test/")


@static_namespace.route("/")
class TempIndexPage(Resource):
    def get(self):
        return send_file("index.html")
