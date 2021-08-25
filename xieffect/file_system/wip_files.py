from typing import Type

from flask import request, send_from_directory
from flask_restful import Resource

from authorship import Author
from componets import jwt_authorizer, lister
from .keeper import CATFile, JSONFile, WIPModule, WIPPage


def file_getter(type_only: bool = True):
    def file_getter_wrapper(function):
        @jwt_authorizer(Author, "author")
        def get_file_or_type(*args, **kwargs):
            result: Type[CATFile]
            file_type: str = kwargs.pop("file_type")
            if file_type == "modules":
                result = WIPModule
            elif file_type == "pages":
                result = WIPPage
            else:
                return {"a": f"File type '{file_type}' is not supported"}, 400

            if "file_id" in kwargs.keys():
                file: result = result.find_by_id(kwargs["file_id"] if type_only else kwargs.pop("file_id"))
                if file.owner != kwargs.pop("author").id:
                    return {"a": "Access denied"}, 403
                if not type_only:
                    return function(file=file, *args, **kwargs)
            return function(file_type=result, *args, **kwargs)

        return get_file_or_type

    return file_getter_wrapper


class FileLister(Resource):  # [POST] /wip/<file_type>/index/
    @file_getter()
    @lister(20)
    def post(self, file_type: Type[CATFile], author: Author, start: int, finish: int):
        if WIPPage not in file_type.mro():
            return {"a": f"File type '{file_type}' is not supported"}, 400
        return [x.get_metadata() for x in file_type.find_by_owner(author, start, finish - start)]


class FileCreator(Resource):  # [POST] /wip/<file_type>/
    @file_getter()
    def post(self, author: Author, file_type: Type[CATFile]):
        if JSONFile in file_type.mro():
            result: file_type = file_type.create_from_json(author, request.get_json())
        else:
            result: file_type = file_type.create_with_file(author, request.get_data())
        return {"id": result.id}


class FileProcessor(Resource):  # [GET|PUT|DELETE] /wip/<file_type>/<int:file_id>/
    @file_getter()
    def get(self, file_type: Type[CATFile], file_id: int):
        return send_from_directory("../" + file_type.directory, f"{file_id}.{file_type.mimetype}")

    @file_getter(type_only=False)
    def put(self, file: CATFile):
        if isinstance(file, JSONFile):
            file.update_json(request.get_json())
        else:
            file.update(request.get_data())
        return {"a": True}

    @file_getter(type_only=False)
    def delete(self, file: CATFile):
        file.delete()
        return {"a": True}
