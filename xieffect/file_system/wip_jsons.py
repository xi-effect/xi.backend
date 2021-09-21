from typing import Type
from json import load

from flask import request  # , send_from_directory
from flask_restful import Resource

from authorship import Author
from componets import jwt_authorizer, lister, database_searcher, with_session
from education import Page
from .keeper import JSONFile, WIPModule, WIPPage


def file_getter(type_only: bool = True):
    def file_getter_wrapper(function):
        @with_session
        @jwt_authorizer(Author, "author")
        def get_file_or_type(session, *args, **kwargs):
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
                if file.owner != kwargs.pop("author").id:
                    return {"a": "Access denied"}, 403
                if not type_only:
                    return function(file=file, session=session, *args, **kwargs)
            return function(file_type=result, *args, **kwargs)

        return get_file_or_type

    return file_getter_wrapper


class FileLister(Resource):  # [POST] /wip/<file_type>/index/
    @file_getter()
    @lister(20)
    def post(self, session, file_type: Type[JSONFile], author: Author, start: int, finish: int):
        if WIPPage not in file_type.mro():
            return {"a": f"File type '{file_type}' is not supported"}, 400
        return [x.get_metadata() for x in file_type.find_by_owner(session, author, start, finish - start)]


class FileCreator(Resource):  # [POST] /wip/<file_type>/
    @file_getter()
    def post(self, session, author: Author, file_type: Type[JSONFile]):
        result: file_type = file_type.create_from_json(session, author, request.get_json())
        # for CATFile  result: file_type = file_type.create_with_file(author, request.get_data())
        return {"id": result.id}


class FileProcessor(Resource):  # [GET|PUT|DELETE] /wip/<file_type>/<int:file_id>/
    @file_getter(type_only=False)
    def get(self, file: JSONFile):
        with open(file.get_link(), "rb") as f:
            result = load(f)
        return result

    # @file_getter()  # PermissionError(13)
    # def get(self, file_type: Type[CATFile], file_id: int):
    #     return send_from_directory("../" + file_type.directory, f"{file_id}.{file_type.mimetype}")

    @file_getter(type_only=False)
    def put(self, session, file: JSONFile):
        file.update_json(session, request.get_json())
        # file.update(request.get_data())
        return {"a": True}

    @file_getter(type_only=False)
    def delete(self, session, file: JSONFile):
        file.delete(session)
        return {"a": True}


class PagePublisher(Resource):  # POST /wip/pages/<int:page_id>/publication/
    @jwt_authorizer(Author, "author")
    @database_searcher(WIPPage, "page_id", "wip_page")
    def post(self, session, author: Author, wip_page: WIPPage):
        if wip_page.owner != author.id:
            return {"a": "Access denied"}, 403

        with open(wip_page.get_link()) as f:
            result: bool = Page.create(session, load(f), author) is None
        return {"a": "Page already exists" if result else "Success"}
