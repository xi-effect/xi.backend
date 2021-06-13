from flask_restful import Resource
from flask_restful.reqparse import RequestParser

from api_resources.base.checkers import argument_parser, database_searcher, lister
from api_resources.base.parsers import counter_parser
from database import Author, AuthorTeam


class TeamLister(Resource):  # [POST] /cat/teams/
    @lister(Author, 24, "author")
    def post(self, author: Author, start: int, finish: int) -> list:
        return author.get_teams(start, finish)


class OwnedCourseLister(Resource):  # [POST] /cat/courses/owned/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("team", type=int, required=True)

    @lister(Author, 24, "author", argument_parser(parser, "counter", ("team", "team_id")))
    @database_searcher(AuthorTeam, "team_id", "team")
    def post(self, author: Author, start: int, finish: int, team: AuthorTeam):
        if author not in team.members:
            return {"a": "Not a member"}, 403
        return team.get_owned_courses(start, finish)


class OwnedPageLister(Resource):  # [POST] /cat/pages/owned/
    @lister(Author, 24, "author")
    def post(self, author: Author, start: int, finish: int) -> list:
        return author.get_owned_pages(start, finish)


class ReusablePageLister(Resource):  # [POST] /cat/pages/reusable/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("tags", required=True)

    @lister(Author, 24, "author", argument_parser(parser, "counter", "tags"))
    def post(self, author: Author, start: int, finish: int, tags: str):
        pass
