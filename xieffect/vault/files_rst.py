from __future__ import annotations

from contextlib import suppress

from flask import send_from_directory, Response
from flask_fullstack import RequestParser
from flask_restx import Resource
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import NotFound

from common import ResourceController, app
from users.users_db import User
from vault.files_db import File, FILES_PATH

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

    @controller.jwt_authorizer(User)  # relation only
    @controller.argument_parser(parser)
    @controller.marshal_with(File.FullModel)
    def post(self, user: User, file_storage: FileStorage) -> File:
        file = File.create(user.id, file_storage.filename)
        file_storage.save(FILES_PATH + file.filename)
        return file


@controller.route("/<filename>/")
class FileAccessor(Resource):
    def get(self, filename: str) -> Response:
        try:
            return send_from_directory(FILES_PATH, filename)
        except NotFound:  # TODO pragma: no coverage
            with suppress(ValueError):
                file = File.find_by_id(int(filename.partition("-")[0]))
                if file is not None:
                    file.delete()
            raise


@controller.route("/manager/<int:file_id>/")
class FileManager(Resource):
    @controller.doc_abort(403, "Not your file")
    @controller.jwt_authorizer(User)  # id only
    @controller.database_searcher(File)
    @controller.a_response()
    def delete(self, user: User, file: File) -> None:
        if file.uploader_id != user.id:
            controller.abort(403, "Not your file")
        file.soft_delete()
