from __future__ import annotations

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController, counter_parser, unite_models, User
from .modules_db import Module, SortType, ModuleFilterSession, PreferenceOperation

education_namespace = ResourceController("modules", path="/")
controller = ResourceController("modules")

module_index_json = controller.model(
    "IndexModule",
    unite_models(
        ModuleFilterSession.marshal_models["mfs-full"],
        Module.marshal_models["module-index"],
    ),
)
module_view_json = controller.model(
    "Module",
    unite_models(
        ModuleFilterSession.marshal_models["mfs-full"],
        Module.marshal_models["module-meta"],
    ),
)

report_parser: RequestParser = RequestParser()
report_parser.add_argument("reason", required=True)
report_parser.add_argument("message", required=False)


@education_namespace.route("/filters/")
class FilterGetter(Resource):  # [GET] /filters/
    @education_namespace.jwt_authorizer(User, use_session=False)
    @education_namespace.a_response()
    def get(self, user: User) -> str:
        """Gets user's saved global filter. Deprecated?"""
        return user.get_filter_bind()


def filters(value):
    return dict(value)


filters.__schema__ = {
    "type": "object",
    "format": "filters",
    "example": '{"global": "pinned" | "starred" | "started", '
    + ", ".join(f'"{key}": ""' for key in ["theme", "category", "difficulty"])
    + "}",
}


@controller.route("/")
class ModuleLister(Resource):  # [POST] /modules/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument(
        "filters", type=filters, required=False, help="A dict of filters to be used"
    )
    parser.add_argument(
        "search", required=False, help="Search query (done with whoosh search)"
    )
    parser.add_argument(
        "sort",
        required=False,
        choices=SortType.get_all_field_names(),
        help="Defines item order",
    )

    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @controller.lister(12, module_index_json)
    def post(
        self,
        session,
        user: User,
        start: int,
        finish: int,
        filters: dict[str, str],
        search: str,
        sort: str,
    ):
        """Lists index of modules with metadata & user's relation"""
        try:
            sort: SortType = SortType.POPULARITY if sort is None else SortType(sort)
        except ValueError:
            controller.abort(400, f"Sorting '{sort}' is not supported")

        if filters is None:
            filters = {}
        elif any(not isinstance(value, str) for value in filters.values()):
            controller.abort(
                400, "Malformed filters parameter: use strings as values only"
            )

        global_filter = filters.get("global", None)
        if global_filter not in ("pinned", "starred", "started", "", None):
            controller.abort(400, f"Global filter '{global_filter}' is not supported")
        user.filter_bind = global_filter

        return Module.get_module_list(
            session, filters, search, sort, user.id, start, finish - start
        )


@controller.route("/hidden/")
class HiddenModuleLister(Resource):  # [POST] /modules/hidden/
    @controller.jwt_authorizer(User)
    @controller.argument_parser(counter_parser)
    @controller.lister(12, Module.ShortModel)
    def post(self, session, user: User, start: int, finish: int) -> list:
        """Lists short metadata for hidden modules"""
        return Module.get_hidden_module_list(session, user.id, start, finish - start)


@controller.route("/<int:module_id>/")
class ModuleGetter(Resource):  # GET /modules/<int:module_id>/
    @controller.jwt_authorizer(User)
    @controller.database_searcher(Module, use_session=True, check_only=True)
    @controller.marshal_with(module_view_json)
    def get(self, session, user: User, module_id: int):
        """Returns module's full metadata & some user relation"""
        ModuleFilterSession.find_or_create(session, user.id, module_id).visit_now()
        return Module.find_with_relation(session, module_id, user.id)


@controller.route("/<int:module_id>/preference/")
class ModulePreferences(Resource):  # [POST] /modules/<int:module_id>/preference/
    parser: RequestParser = RequestParser()
    parser.add_argument(
        "a",
        required=True,
        dest="operation",
        choices=PreferenceOperation.get_all_field_names(),
    )

    @controller.jwt_authorizer(User)
    @controller.database_searcher(Module, check_only=True, use_session=True)
    @controller.argument_parser(parser)
    @controller.a_response()
    def post(self, session, module_id: int, user: User, operation: str) -> None:
        """Changes user relation to some module"""
        module: ModuleFilterSession | None = ModuleFilterSession.find_by_ids(
            session, user.id, module_id
        )
        if module is None:
            if operation.startswith("un"):
                return
            module = ModuleFilterSession.create(session, user.id, module_id)
        module.change_preference(session, PreferenceOperation.from_string(operation))


@controller.route("/<int:module_id>/report/")
class ModuleReporter(Resource):  # [POST] /modules/<int:module_id>/report/
    @controller.jwt_authorizer(User, check_only=True, use_session=False)
    @controller.database_searcher(Module)
    @controller.argument_parser(report_parser)
    @controller.a_response()
    def post(self, module: Module, reason: str, message: str) -> None:
        pass
