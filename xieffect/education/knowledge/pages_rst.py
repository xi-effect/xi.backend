from typing import Union

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import Namespace, counter_parser, User
from .pages_db import Page

pages_view_namespace: Namespace = Namespace("pages")

report_parser: RequestParser = RequestParser()
report_parser.add_argument("reason", required=True)
report_parser.add_argument("message", required=False)


@pages_view_namespace.route("/")
class PageLister(Resource):  # POST /pages/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("search", required=False, help="Search query (done with whoosh search)")

    @pages_view_namespace.jwt_authorizer(User, check_only=True)
    @pages_view_namespace.argument_parser(parser)
    @pages_view_namespace.lister(50, Page.ShortModel)
    def post(self, session, search: Union[str, None], start: int, finish: int) -> list:
        """ Lists index of pages with metadata only """
        return Page.search(session, search, start, finish - start)


@pages_view_namespace.route("/<int:page_id>/")
class PageGetter(Resource):  # GET /pages/<int:page_id>/
    @pages_view_namespace.jwt_authorizer(User, check_only=True, use_session=False)
    @pages_view_namespace.database_searcher(Page)
    @pages_view_namespace.marshal_with(Page.MainModel, skip_none=True)
    def get(self, page: Page):  # add some access checks
        """ Returns module's full metadata & content """
        page.view()
        return page


@pages_view_namespace.route("/<int:page_id>/report/")
class PageReporter(Resource):
    @pages_view_namespace.jwt_authorizer(User, check_only=True, use_session=False)
    @pages_view_namespace.argument_parser(report_parser)
    @pages_view_namespace.database_searcher(Page)
    @pages_view_namespace.a_response()
    def post(self, page: Page, reason: str, message: str) -> None:
        pass
