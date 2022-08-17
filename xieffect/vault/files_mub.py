from __future__ import annotations

from os import remove

from flask_restx import Resource

from common import sessionmaker, counter_parser
from moderation import MUBController, permission_index
from .files_db import File

content_management = permission_index.add_section("content management")
manage_files = permission_index.add_permission(content_management, "manage files")
controller = MUBController("files", sessionmaker=sessionmaker)


@controller.route("/index/")
class MUBFileLister(Resource):
    @controller.require_permission(manage_files, use_moderator=False)
    @controller.argument_parser(counter_parser)
    @controller.lister(20, File.FullModel)
    def post(self, session, start: int, finish: int) -> list[File]:
        return File.get_for_mub(session, start, finish - start)


@controller.route("/<int:file_id>/")
class MUBFileManager(Resource):
    @controller.require_permission(manage_files, use_moderator=False)
    @controller.database_searcher(File, use_session=True)
    @controller.a_response()
    def delete(self, session, file: File) -> None:
        remove(f"../files/vault/{file.filename}")
        file.delete(session)
