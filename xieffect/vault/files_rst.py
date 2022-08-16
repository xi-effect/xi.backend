from __future__ import annotations

from os import remove

from flask import send_from_directory
from flask_restx import Resource
from flask_restx.reqparse import RequestParser
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import NotFound

from common import ResourceController, User, app
from .files_db import File

app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 4  # 4 MiB max file size
controller = ResourceController("files")


@controller.route("/")
class FileUploader(Resource):
    parser = RequestParser()
    parser.add_argument("file", location="files", dest="file_storage", type=FileStorage, required=True)

    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @controller.marshal_with(File.FullModel)
    def post(self, session, user: User, file_storage: FileStorage):
        file = File.create(session, user, file_storage.filename)
        file_storage.save(f"../files/{file.filename}")
        return file


@controller.route("/<filename>/")
class FileAccessor(Resource):
    @controller.with_begin
    def get(self, session, filename: str):
        try:
            return send_from_directory("../files", filename)
        except NotFound:
            file = File.find_by_filename(session, filename)
            if file is not None:
                file.delete(session)
            raise


@controller.route("/manager/<int:file_id>/")
class FileManager(Resource):
    @controller.doc_abort(403, "Not your file")
    @controller.jwt_authorizer(User)
    @controller.database_searcher(File, use_session=True)
    def delete(self, session, user: User, file: File):
        if file.uploader_id != user.id:
            controller.doc_abort(403, "Not your file")
        remove(f"../files/{file.filename}")
        file.delete(session)
