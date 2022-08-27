from __future__ import annotations

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController, counter_parser, User
from .pages_db import Page

controller = ResourceController("pages")

report_parser: RequestParser = RequestParser()
report_parser.add_argument("reason", required=True)
report_parser.add_argument("message", required=False)


@controller.route("/")
class PageLister(Resource):  # POST /pages/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument(
        "search", required=False, help="Search query (done with whoosh search)"
    )

    @controller.jwt_authorizer(User, check_only=True)
    @controller.argument_parser(parser)
    @controller.lister(50, Page.ShortModel)
    def post(self, session, search: str | None, start: int, finish: int) -> list:
        """Lists index of pages with metadata only"""
        return Page.search(session, search, start, finish - start)


@controller.route("/<int:page_id>/")
class PageGetter(Resource):  # GET /pages/<int:page_id>/
    @controller.jwt_authorizer(User, check_only=True, use_session=False)
    @controller.database_searcher(Page)
    @controller.marshal_with(Page.MainModel)
    def get(self, page: Page):  # add some access checks
        """Returns module's full metadata & content"""
        page.view()
        return page


@controller.route("/<int:page_id>/report/")
class PageReporter(Resource):
    @controller.jwt_authorizer(User, check_only=True, use_session=False)
    @controller.argument_parser(report_parser)
    @controller.database_searcher(Page)
    @controller.a_response()
    def post(self, page: Page, reason: str, message: str) -> None:
        pass
