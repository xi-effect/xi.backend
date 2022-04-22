from typing import Union

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import Namespace, counter_parser, unite_models, User
from .modules_db import Module, SortType, ModuleFilterSession, PreferenceOperation

education_namespace: Namespace = Namespace("modules", path="/")
modules_view_namespace: Namespace = Namespace("modules")

module_index_json = modules_view_namespace.model("IndexModule", unite_models(
    ModuleFilterSession.marshal_models["mfs-full"], Module.marshal_models["module-index"]))
module_view_json = modules_view_namespace.model("Module", unite_models(
    ModuleFilterSession.marshal_models["mfs-full"], Module.marshal_models["module-meta"]))

report_parser: RequestParser = RequestParser()
report_parser.add_argument("reason", required=True)
report_parser.add_argument("message", required=False)


@education_namespace.route("/filters/")
class FilterGetter(Resource):  # [GET] /filters/
    @education_namespace.jwt_authorizer(User, use_session=False)
    @education_namespace.a_response()
    def get(self, user: User) -> str:
        """ Gets user's saved global filter. Deprecated? """
        return user.get_filter_bind()


def filters(value):
    return dict(value)


filters.__schema__ = {
    "type": "object",
    "format": "filters",
    "example": '{"global": "pinned" | "starred" | "started", ' +
               ", ".join(f'"{key}": ""' for key in ["theme", "category", "difficulty"]) + '}'
}


@modules_view_namespace.route("/")
class ModuleLister(Resource):  # [POST] /modules/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("filters", type=filters, required=False, help="A dict of filters to be used")
    parser.add_argument("search", required=False, help="Search query (done with whoosh search)")
    parser.add_argument("sort", required=False, choices=SortType.get_all_field_names(), help="Defines item order")

    @modules_view_namespace.jwt_authorizer(User)
    @modules_view_namespace.argument_parser(parser)
    @modules_view_namespace.lister(12, module_index_json)
    def post(self, session, user: User, start: int, finish: int, filters: dict[str, str], search: str, sort: str):
        """ Lists index of modules with metadata & user's relation """
        try:
            sort: SortType = SortType.POPULARITY if sort is None else SortType(sort)
        except ValueError:
            modules_view_namespace.abort(400, f"Sorting '{sort}' is not supported")

        if filters is None:
            filters = {}
        elif any(not isinstance(value, str) for value in filters.values()):
            modules_view_namespace.abort(400, "Malformed filters parameter: use strings as values only")

        global_filter = filters.get("global", None)
        if global_filter not in ("pinned", "starred", "started", "", None):
            modules_view_namespace.abort(400, f"Global filter '{global_filter}' is not supported")
        user.filter_bind = global_filter

        return Module.get_module_list(session, filters, search, sort, user.id, start, finish - start)


@modules_view_namespace.route("/hidden/")
class HiddenModuleLister(Resource):  # [POST] /modules/hidden/
    @modules_view_namespace.jwt_authorizer(User)
    @modules_view_namespace.argument_parser(counter_parser)
    @modules_view_namespace.lister(12, Module.ShortModel)
    def post(self, session, user: User, start: int, finish: int) -> list:
        """ Lists short metadata for hidden modules """
        return Module.get_hidden_module_list(session, user.id, start, finish - start)


@modules_view_namespace.route("/<int:module_id>/")
class ModuleGetter(Resource):  # GET /modules/<int:module_id>/
    @modules_view_namespace.jwt_authorizer(User)
    @modules_view_namespace.database_searcher(Module, use_session=True, check_only=True)
    @modules_view_namespace.marshal_with(module_view_json, skip_none=True)
    def get(self, session, user: User, module_id: int):
        """ Returns module's full metadata & some user relation """
        ModuleFilterSession.find_or_create(session, user.id, module_id).visit_now()
        return Module.find_with_relation(session, module_id, user.id)


@modules_view_namespace.route("/<int:module_id>/preference/")
class ModulePreferences(Resource):  # [POST] /modules/<int:module_id>/preference/
    parser: RequestParser = RequestParser()
    parser.add_argument("a", required=True, dest="operation", choices=PreferenceOperation.get_all_field_names())

    @modules_view_namespace.jwt_authorizer(User)
    @modules_view_namespace.database_searcher(Module, check_only=True, use_session=True)
    @modules_view_namespace.argument_parser(parser)
    @modules_view_namespace.a_response()
    def post(self, session, module_id: int, user: User, operation: str) -> None:
        """ Changes user relation to some module """
        module: Union[ModuleFilterSession, None] = ModuleFilterSession.find_by_ids(session, user.id, module_id)
        if module is None:
            if operation.startswith("un"):
                return
            module = ModuleFilterSession.create(session, user.id, module_id)
        module.change_preference(session, PreferenceOperation.from_string(operation))


@modules_view_namespace.route("/<int:module_id>/report/")
class ModuleReporter(Resource):  # [POST] /modules/<int:module_id>/report/
    @modules_view_namespace.jwt_authorizer(User, check_only=True, use_session=False)
    @modules_view_namespace.database_searcher(Module)
    @modules_view_namespace.argument_parser(report_parser)
    @modules_view_namespace.a_response()
    def post(self, module: Module, reason: str, message: str) -> None:
        pass
