from flask_restful import Resource

from componets import lister, jwt_authorizer
from authorship import Author
from file_system.keeper import WIPPage  # , WIPModule


class OwnedModulesLister(Resource):  # POST /modules/owned/
    @jwt_authorizer(Author, "author")
    @lister(50)
    def post(self, author: Author):
        pass


class OwnedPagesLister(Resource):  # POST /pages/owned/
    @jwt_authorizer(Author, "author")
    @lister(50)
    def post(self, author: Author, start: int, finish: int):
        return [x.get_metadata() for x in WIPPage.find_by_owner(author, start, finish - start)]
