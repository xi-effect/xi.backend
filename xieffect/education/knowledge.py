from typing import List, Dict, Optional

from flask_restful import Resource
from flask_restful.reqparse import RequestParser

from componets import jwt_authorizer, database_searcher, argument_parser, lister, counter_parser
from education.elements import Module, Page, SortType
from education.sessions import ModuleFilterSession
from users import User
from webhooks import send_discord_message, WebhookURLs


class FilterGetter(Resource):  # [GET] /filters/
    @jwt_authorizer(User, use_session=False)
    def get(self, user: User):
        return {"a": user.get_filter_bind()}


report_parser: RequestParser = RequestParser()
report_parser.add_argument("reason", required=True)
report_parser.add_argument("message", required=False)


class ModuleLister(Resource):  # [POST] /modules/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("filters", type=dict, required=False)
    parser.add_argument("search", required=False)
    parser.add_argument("sort", required=False)

    @jwt_authorizer(User)
    @lister(12, argument_parser(parser, "counter", "filters", "sort", "search"))
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

        # if sort == SortType.POPULARITY:
        #     result.sort(key=lambda x: x.popularity, reverse=True)
        # elif sort == SortType.VISIT_DATE:
        #     result.sort(key=lambda x: (ModuleFilterSession.find_visit_date(session, user_id, x.id),
        #                                x.popularity), reverse=True)
        # elif sort == SortType.CREATION_DATE:
        #     result.sort(key=lambda x: (x.creation_date.timestamp(), x.popularity), reverse=True)

        return [x.to_json(session) for x in result]


class HiddenModuleLister(Resource):  # [POST] /modules/hidden/
    @jwt_authorizer(User)
    @lister(-12)
    def post(self, session, user: User, start: int, finish: int) -> list:
        result = list()
        for module_id in ModuleFilterSession.filter_ids_by_user(user.id, start, finish - start):
            module: Module = Module.find_by_id(session, module_id)
            result.append(module.to_short_json())
        return result


class ModulePreferences(Resource):  # [POST] /modules/<int:module_id>/preference/
    parser: RequestParser = RequestParser()
    parser.add_argument("a", required=True)

    @jwt_authorizer(User)
    @database_searcher(Module, "module_id", check_only=True, use_session=True)
    @argument_parser(parser, ("a", "operation"))
    def post(self, session, module_id: int, user: User, operation: str):
        module: ModuleFilterSession = ModuleFilterSession.find_or_create(session, user.id, module_id)
        module.change_preference(session, operation)
        return {"a": True}


class ModuleReporter(Resource):  # [POST] /modules/<int:module_id>/report/
    @jwt_authorizer(User, None, use_session=False)
    @database_searcher(Module, "module_id", "module")
    @argument_parser(report_parser, "reason", "message")
    def post(self, module: Module, reason: str, message: str):
        send_discord_message(
            WebhookURLs.COMPLAINER,
            f"Появилась новая жалоба на модуль #{module.id} ({module.name})\n"
            f"Причина: {reason}" + f"\nСообщение: {message}" if message is not None else ""
        )
        return {"a": True}


class PageLister(Resource):  # POST /pages/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("search", required=False)

    @jwt_authorizer(User, None)
    @lister(50, argument_parser(parser, "search", "counter"))
    def post(self, session, search: Optional[str], start: int, finish: int) -> list:
        return [page.to_json() for page in Page.search(session, search, start, finish - start)]


class PageReporter(Resource):  # POST /pages/<int:page_id>/report/
    @jwt_authorizer(User, None, use_session=False)
    @database_searcher(Page, "page_id", "page")
    @argument_parser(report_parser, "reason", "message")
    def post(self, page: Page, reason: str, message: str):
        pass


class ShowAll(Resource):  # test
    @jwt_authorizer(User, use_session=False)
    def get(self, user: User):
        ModuleFilterSession.change_by_user(user.id, "show")
        return {"a": True}
