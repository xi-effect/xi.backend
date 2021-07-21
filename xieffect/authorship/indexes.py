from flask_restful import Resource

from authorship.user_roles import Author
from componets import jwt_authorizer, lister


class OwnedModuleLister(Resource):  # [POST] /cat/modules/owned/
    @jwt_authorizer(Author, "author")
    @lister(24)
    def post(self, author: Author, start: int, finish: int):
        return author.get_owned_modules(start, finish)
