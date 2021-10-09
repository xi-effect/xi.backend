from typing import List, Dict, Optional

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import Namespace, counter_parser
from education.elements import Module, Page, SortType
from education.sessions import ModuleFilterSession
from users import User
from webhooks import send_discord_message, WebhookURLs


education_namespace: Namespace = Namespace("modules", path="/")
modules_view_namespace: Namespace = Namespace("modules")
pages_view_namespace: Namespace = Namespace("pages")

page_view_json = pages_view_namespace.model("Page", Page.marshal_models["page-main"])
short_page_json = pages_view_namespace.model("ShortPage", Page.marshal_models["page-short"])

module_view_json = None
short_module_json = modules_view_namespace.model("ShortModule", Module.marshal_models["short"])

report_parser: RequestParser = RequestParser()
report_parser.add_argument("reason", required=True)
report_parser.add_argument("message", required=False)


@education_namespace.route("/filters/")
class FilterGetter(Resource):  # [GET] /filters/
    @education_namespace.a_response()
    @education_namespace.jwt_authorizer(User, use_session=False)
    def get(self, user: User) -> str:
        return user.get_filter_bind()


@modules_view_namespace.route("/")
class ModuleLister(Resource):  # [POST] /modules/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("filters", type=dict, required=False)
    parser.add_argument("search", required=False)
    parser.add_argument("sort", required=False)

    @modules_view_namespace.jwt_authorizer(User)
    @modules_view_namespace.argument_parser(parser, "counter", "filters", "sort", "search")
    @modules_view_namespace.lister(12)
    def post(self, session, user: User, start: int, finish: int, filters: Dict[str, str], search: str, sort: str):
        try:
            sort: SortType = SortType.POPULARITY if sort is None else SortType(sort)
        except ValueError:
            return {"a": f"Sorting '{sort}' is not supported"}, 406

        if filters is not None and "global" in filters.keys():
            user.set_filter_bind(filters["global"])
        else:
            user.set_filter_bind()
        user_id: int = user.id

        result: List[Module] = Module.get_module_list(session, filters, search, sort, user_id, start, finish - start)

        return [x.to_json(session, user_id) for x in result]


@modules_view_namespace.route("/hidden/")
class HiddenModuleLister(Resource):  # [POST] /modules/hidden/
    @modules_view_namespace.jwt_authorizer(User)
    @modules_view_namespace.argument_parser(counter_parser, "counter")
    @modules_view_namespace.marshal_list_with(short_module_json, skip_none=True)
    @modules_view_namespace.lister(12)
    def post(self, session, user: User, start: int, finish: int) -> list:
        return Module.get_hidden_module_list(session, user.id, start, finish - start)


@modules_view_namespace.route("/<int:module_id>/")
class ModuleOpener(Resource):  # GET /modules/<int:module_id>/
    @modules_view_namespace.jwt_authorizer(User)
    @modules_view_namespace.database_searcher(Module, "module_id", "module", use_session=True)
    def get(self, session, user: User, module: Module):
        ModuleFilterSession.find_or_create(session, user.id, module.id).visit_now()
        return module.to_json(session, user.id)


@modules_view_namespace.route("/<int:module_id>/preference/")
class ModulePreferences(Resource):  # [POST] /modules/<int:module_id>/preference/
    parser: RequestParser = RequestParser()
    parser.add_argument("a", required=True)

    @modules_view_namespace.a_response()
    @modules_view_namespace.jwt_authorizer(User)
    @modules_view_namespace.database_searcher(Module, "module_id", check_only=True, use_session=True)
    @modules_view_namespace.argument_parser(parser, ("a", "operation"))
    def post(self, session, module_id: int, user: User, operation: str) -> None:
        module: ModuleFilterSession = ModuleFilterSession.find_or_create(session, user.id, module_id)
        module.change_preference(session, operation)


@modules_view_namespace.route("/<int:module_id>/report/")
class ModuleReporter(Resource):  # [POST] /modules/<int:module_id>/report/
    @modules_view_namespace.a_response()
    @modules_view_namespace.jwt_authorizer(User, None, use_session=False)
    @modules_view_namespace.database_searcher(Module, "module_id", "module")
    @modules_view_namespace.argument_parser(report_parser, "reason", "message")
    def post(self, module: Module, reason: str, message: str) -> None:
        send_discord_message(
            WebhookURLs.COMPLAINER,
            f"Появилась новая жалоба на модуль #{module.id} ({module.name})\n"
            f"Причина: {reason}" + f"\nСообщение: {message}" if message is not None else ""
        )


@pages_view_namespace.route("/")
class PageLister(Resource):  # POST /pages/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("search", required=False)

    @pages_view_namespace.jwt_authorizer(User, None)
    @pages_view_namespace.argument_parser(parser, "search", "counter")
    @pages_view_namespace.marshal_list_with(short_page_json, skip_none=True)
    @pages_view_namespace.lister(50)
    def post(self, session, search: Optional[str], start: int, finish: int) -> list:
        return Page.search(session, search, start, finish - start)


@pages_view_namespace.route("/<int:page_id>/")
class PageGetter(Resource):  # GET /pages/<int:page_id>/
    @pages_view_namespace.jwt_authorizer(User, None, use_session=False)
    @pages_view_namespace.database_searcher(Page, "page_id", "page")
    @pages_view_namespace.marshal_with(page_view_json, skip_none=True)
    def get(self, page: Page):  # add some access checks
        page.view()
        return page


@pages_view_namespace.route("/<int:page_id>/report/")
class PageReporter(Resource):  # POST /pages/<int:page_id>/report/
    @pages_view_namespace.jwt_authorizer(User, None, use_session=False)
    @pages_view_namespace.database_searcher(Page, "page_id", "page")
    @pages_view_namespace.argument_parser(report_parser, "reason", "message")
    def post(self, page: Page, reason: str, message: str):
        pass


@modules_view_namespace.route("/reset-hidden/")
class ShowAllModules(Resource):  # GET /modules/reset-hidden/
    @modules_view_namespace.a_response()
    @modules_view_namespace.jwt_authorizer(User)
    def get(self, session, user: User) -> None:
        ModuleFilterSession.change_preference_by_user(session, user.id, "show")
