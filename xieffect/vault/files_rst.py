from __future__ import annotations

from contextlib import suppress
from os import remove

from flask import send_from_directory
from flask_restx import Resource
from flask_restx.reqparse import RequestParser
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import NotFound

from common import ResourceController, User, app, absolute_path
from vault import File

app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 4  # 4 MiB max file size
controller = ResourceController("files")


@controller.route("/")
class FileUploader(Resource):
    parser = RequestParser()
    parser.add_argument(
        "file",
        location="files",
        dest="file_storage",
        type=FileStorage,
        required=True,
    )

    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @controller.marshal_with(File.FullModel)
    def post(self, user: User, file_storage: FileStorage):
        file = File.create(user, file_storage.filename)
        file_storage.save(absolute_path(f"files/vault/{file.filename}"))
        return file


@controller.route("/<filename>/")
class FileAccessor(Resource):
    def get(self, filename: str):
        try:
            return send_from_directory(absolute_path("files/vault/"), filename)
        except NotFound:  # TODO pragma: no coverage
            with suppress(ValueError):
                file = File.find_by_id(int(filename.partition("-")[0]))
                if file is not None:
                    file.delete()
            raise


@controller.route("/manager/<int:file_id>/")
class FileManager(Resource):
    @controller.doc_abort(403, "Not your file")
    @controller.jwt_authorizer(User)
    @controller.database_searcher(File)
    @controller.a_response()
    def delete(self, user: User, file: File) -> None:
        if file.uploader_id != user.id:
            controller.abort(403, "Not your file")
        remove(absolute_path(f"files/vault/{file.filename}"))
        file.delete()
