from flask_restful import Resource

from componets import lister, jwt_authorizer, with_session
from authorship import Author
from file_system.keeper import WIPPage  # , WIPModule


class OwnedModulesLister(Resource):  # POST /modules/owned/
    @lister(50)
    @jwt_authorizer(Author, "author", use_session=False)
    def post(self, author: Author):
        pass


class OwnedPagesLister(Resource):  # POST /pages/owned/
    @lister(50)
    @jwt_authorizer(Author, "author")
    def post(self, session, author: Author, start: int, finish: int):
        return [x.get_metadata(session) for x in WIPPage.find_by_owner(session, author, start, finish - start)]
