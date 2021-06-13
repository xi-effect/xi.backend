from typing import Type

from flask_restful import Resource

from api_resources.base.checkers import jwt_authorizer, argument_parser
from api_resources.base.parsers import counter_parser
from database import Author, CATFile, CATCourse, Page


def file_getter(function):
    @jwt_authorizer(Author, "author")
    def get_file_or_type(file_type: str, *args, **kwargs):
        if file_type == "courses":
            result = CATCourse
        elif file_type == "pages":
            result = Page
        else:
            return {"a": f"File type '{file_type}' is not supported"}, 406

        if "file_id" in kwargs.keys():
            result = result.find_by_id(kwargs.pop("file_id"))
            return function(file=result, *args, **kwargs)
        else:
            return function(file_type=result, *args, **kwargs)

    return get_file_or_type


class FileLister(Resource):  # [POST] /wip/<file_type>/index/
    @file_getter
    @argument_parser(counter_parser, "counter")
    def post(self, file_type: Type[CATFile], author: Author, counter: int):
        pass


class FileProcessor(Resource):  # [GET|PUT|DELETE] /wip/<file_type>/<int:file_id>/
    @file_getter
    def get(self, author: Author, file: CATFile):
        pass

    @file_getter
    def put(self, author: Author, file: CATFile):
        pass

    @file_getter
    def delete(self, author: Author, file: CATFile):
        pass


class FileCreator(Resource):  # [POST] /wip/<file_type>/
    @file_getter
    def post(self, author: Author, file_type: Type[CATFile]):
        pass
