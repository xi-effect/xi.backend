from functools import wraps
from json import load
from typing import Type

from flask import request  # , send_from_directory
from flask_restx import Resource, Namespace, Model
from flask_restx.fields import Integer

from authorship import Author
from componets import jwt_authorizer, lister, argument_parser, counter_parser
from componets import doc_success_response, doc_message_response, doc_responses, ResponseDoc
from education import Page, Module
from .keeper import JSONFile, WIPModule, WIPPage


def file_getter(type_only: bool = True, use_session: bool = True, use_author: bool = False):
    def file_getter_wrapper(function):
        @wraps(function)
        @jwt_authorizer(Author, "author")
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


wip_json_file_namespace: Namespace = Namespace("wip-files", path="/wip/<file_type>/")


@wip_json_file_namespace.route("/index/")
class FileLister(Resource):  # [POST] /wip/<file_type>/index/
    @file_getter()
    @argument_parser(counter_parser, "counter", ns=wip_json_file_namespace)
    @lister(50)
    def post(self, session, file_type: Type[JSONFile], author: Author, start: int, finish: int):
        return [x.get_metadata(session) for x in file_type.find_by_owner(session, author, start, finish - start)]


@wip_json_file_namespace.route("/")
class FileCreator(Resource):  # [POST] /wip/<file_type>/
    @file_getter()
    @doc_responses(wip_json_file_namespace, ResponseDoc(model=Model("ID Response", {"id": Integer})))
    def post(self, session, author: Author, file_type: Type[JSONFile]):
        result: file_type = file_type.create_from_json(session, author, request.get_json())
        # for CATFile  result: file_type = file_type.create_with_file(author, request.get_data())
        return {"id": result.id}


@wip_json_file_namespace.route("/<int:file_id>/")
class FileProcessor(Resource):  # [GET|PUT|DELETE] /wip/<file_type>/<int:file_id>/
    @file_getter(type_only=False, use_session=False)
    def get(self, file: JSONFile):
        with open(file.get_link(), "rb") as f:
            result = load(f)
        return result

    # @file_getter()  # PermissionError(13)
    # def get(self, file_type: Type[CATFile], file_id: int):
    #     return send_from_directory("../" + file_type.directory, f"{file_id}.{file_type.mimetype}")

    @doc_success_response(wip_json_file_namespace)
    @file_getter(type_only=False)
    def put(self, session, file: JSONFile):
        file.update_json(session, request.get_json())
        # file.update(request.get_data())
        return {"a": True}

    @doc_success_response(wip_json_file_namespace)
    @file_getter(type_only=False)
    def delete(self, session, file: JSONFile):
        file.delete(session)
        return {"a": True}


@wip_json_file_namespace.route("/<int:file_id>/publication/")
class FilePublisher(Resource):  # POST /wip/<file_type>/<int:file_id>/publication/
    @doc_message_response(wip_json_file_namespace)
    @file_getter(type_only=False, use_session=True, use_author=True)
    def post(self, session, file: JSONFile, author: Author):
        with open(file.get_link(), "rb") as f:
            content: dict = load(f)
            content["id"] = file.id  # just making sure
            result: bool = (Page if type(file) == WIPPage else Module).create(session, content, author) is None
        return {"a": "File already exists" if result else "Success"}
