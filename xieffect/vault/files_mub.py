from __future__ import annotations

from os import remove

from flask_fullstack import counter_parser
from flask_restx import Resource

from common import absolute_path
from moderation import MUBController, permission_index
from vault import File

content_management = permission_index.add_section("content management")
manage_files = permission_index.add_permission(content_management, "manage files")
controller = MUBController("files")


@controller.route("/")
class MUBFileLister(Resource):
    @controller.require_permission(manage_files, use_moderator=False)
    @controller.argument_parser(counter_parser)
    @controller.lister(20, File.FullModel)
    def get(self, start: int, finish: int) -> list[File]:
        return File.get_for_mub(start, finish - start)


@controller.route("/index/")
class OldMUBFileLister(Resource):  # pragma: no coverage  # TODO remove
    @controller.require_permission(manage_files, use_moderator=False)
    @controller.argument_parser(counter_parser)
    @controller.lister(20, File.FullModel)
    def post(self, start: int, finish: int) -> list[File]:
        return File.get_for_mub(start, finish - start)


@controller.route("/<int:file_id>/")
class MUBFileManager(Resource):
    @controller.require_permission(manage_files, use_moderator=False)
    @controller.database_searcher(File)
    @controller.a_response()
    def delete(self, file: File) -> None:
        remove(absolute_path(f"files/vault/{file.filename}"))
        file.delete()
