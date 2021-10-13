from functools import wraps
from json import load
from typing import Type

from flask import request  # , send_from_directory
from flask_restx import Resource, Model
from flask_restx.fields import Integer

from authorship import Author
from componets import Namespace, counter_parser, ResponseDoc
from education import Page, Module
from .keeper import JSONFile, WIPModule, WIPPage


wip_json_file_namespace: Namespace = Namespace("wip-files", path="/wip/<file_type>/")
wip_index_namespace: Namespace = Namespace("wip-files", path="/wip/")
wip_short_page_json = wip_index_namespace.model("WIPPageShort", WIPPage.marshal_models["wip-page"])
wip_short_module_json = wip_index_namespace.model("WIPModuleShort", WIPModule.marshal_models["wip-module"])


@wip_index_namespace.route("/modules/index/")
class WIPModuleLister(Resource):  # [POST] /wip/modules/index/
    @wip_index_namespace.jwt_authorizer(Author)
    @wip_index_namespace.argument_parser(counter_parser)
    @wip_index_namespace.lister(50, wip_short_module_json, skip_none=False)
    def post(self, session, author: Author, start: int, finish: int):
        return WIPModule.find_by_owner(session, author, start, finish - start)


@wip_index_namespace.route("/pages/index/")
class WIPPageLister(Resource):  # [POST] /wip/pages/index/
    @wip_index_namespace.jwt_authorizer(Author)
    @wip_index_namespace.argument_parser(counter_parser)
    @wip_index_namespace.lister(50, wip_short_page_json, skip_none=False)
    def post(self, session, author: Author, start: int, finish: int):
        return WIPPage.find_by_owner(session, author, start, finish - start)


def file_getter(type_only: bool = True, use_session: bool = True, use_author: bool = False):
    def file_getter_wrapper(function):
        @wraps(function)
        @wip_json_file_namespace.jwt_authorizer(Author)
        def get_file_or_type(*args, **kwargs):
            session = kwargs.pop("session")
            result: Type[JSONFile]
            file_type: str = kwargs.pop("file_type")
            if file_type == "modules":
                result = WIPModule
            elif file_type == "pages":
                result = WIPPage
            else:
                return {"a": f"File type '{file_type}' is not supported"}, 400

            if "file_id" in kwargs.keys():
                file: result = result.find_by_id(session, kwargs["file_id"] if type_only else kwargs.pop("file_id"))
                if file is None:
                    return {"a": "File not found"}, 404
                if file.owner != (kwargs["author"] if use_author else kwargs.pop("author")).id:
                    return {"a": "Access denied"}, 403
                if not type_only:
                    if use_session:
                        return function(file=file, session=session, *args, **kwargs)
                    else:
                        return function(file=file, *args, **kwargs)
            if use_session:
                return function(file_type=result, session=session, *args, **kwargs)
            else:
                return function(file_type=result, *args, **kwargs)

        return get_file_or_type

    return file_getter_wrapper


@wip_json_file_namespace.route("/")
class FileCreator(Resource):  # [POST] /wip/<file_type>/
    @wip_json_file_namespace.doc_file_param("json")
    @wip_json_file_namespace.doc_responses(ResponseDoc(model=Model("ID Response", {"id": Integer})))
    @file_getter()
    def post(self, session, author: Author, file_type: Type[JSONFile]):
        result: file_type = file_type.create_from_json(session, author, request.get_json())
        # for CATFile  result: file_type = file_type.create_with_file(author, request.get_data())
        return {"id": result.id}


@wip_json_file_namespace.route("/<int:file_id>/")
class FileProcessor(Resource):  # [GET|PUT|DELETE] /wip/<file_type>/<int:file_id>/
    @wip_json_file_namespace.response(200, "JSON-file of the file type")
    @file_getter(type_only=False, use_session=False)
    def get(self, file: JSONFile):
        with open(file.get_link(), "rb") as f:
            result = load(f)
        return result

    # @file_getter()  # PermissionError(13)
    # def get(self, file_type: Type[CATFile], file_id: int):
    #     return send_from_directory("../" + file_type.directory, f"{file_id}.{file_type.mimetype}")

    @wip_json_file_namespace.doc_file_param("json")
    @wip_json_file_namespace.a_response()
    @file_getter(type_only=False)
    def put(self, session, file: JSONFile) -> None:
        file.update_json(session, request.get_json())
        # file.update(request.get_data())

    @wip_json_file_namespace.doc_file_param("json")
    @wip_json_file_namespace.a_response()
    @file_getter(type_only=False)
    def delete(self, session, file: JSONFile) -> None:
        file.delete(session)


@wip_json_file_namespace.route("/<int:file_id>/publication/")
class FilePublisher(Resource):  # POST /wip/<file_type>/<int:file_id>/publication/
    @wip_json_file_namespace.a_response()
    @file_getter(type_only=False, use_session=True, use_author=True)
    def post(self, session, file: JSONFile, author: Author) -> str:
        with open(file.get_link(), "rb") as f:
            content: dict = load(f)
            content["id"] = file.id  # just making sure
            result: bool = (Page if type(file) == WIPPage else Module).create(session, content, author) is None
        return "File already exists" if result else "Success"
