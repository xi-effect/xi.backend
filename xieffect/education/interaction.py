from functools import wraps
from typing import Optional

from flask import redirect
from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import Namespace, ResponseDoc
from .elements import Module, Point, ModuleType
from .sessions import StandardModuleSession, TestModuleSession
from users import User


def redirected_to_pages(op_name, *possible_module_types: ModuleType):
    responses = [ResponseDoc.error_response(400, "Unacceptable module type"),
                 ResponseDoc(302, r"Redirect to GET /pages/\<id\>/ with generated ID")]

    def redirected_to_pages_wrapper(function):
        @interaction_namespace.doc_responses(*responses)
        @interaction_namespace.jwt_authorizer(User)
        @interaction_namespace.database_searcher(Module, use_session=True)
        @wraps(function)
        def redirected_to_pages_inner(*args, **kwargs):
            module_type: ModuleType = kwargs["module"].type
            if module_type not in possible_module_types:
                return {"a": f"Module of type {module_type} can't use {op_name}"}, 400
            if len(possible_module_types) > 1:
                kwargs["module_type"] = module_type
            result: Optional[bool] = function(*args, **kwargs)
            return {"a": "You have reached the end"} if result is None else redirect(f"/pages/{result}/")

        return redirected_to_pages_inner

    return redirected_to_pages_wrapper


interaction_namespace: Namespace = Namespace("interaction", path="/modules/<int:module_id>/")


@interaction_namespace.route("/next/")
class ModuleProgresser(Resource):
    @interaction_namespace.doc_responses(ResponseDoc.error_response(200, "You have reached the end"))
    @redirected_to_pages("linear progression", ModuleType.STANDARD, ModuleType.PRACTICE_BLOCK)
    def post(self, session, user: User, module: Module, module_type: ModuleType) -> Optional[int]:
        if module_type == ModuleType.STANDARD:
            module_session: StandardModuleSession = StandardModuleSession.find_or_create(session, user.id, module.id)
            module_session.progress += 1
            if module_session.progress >= module.length:
                module_session.delete(session)
                return None
            return Point.find_and_execute(session, module.id, module_session.progress)
        elif module_type == ModuleType.PRACTICE_BLOCK:
            return module.execute_random_point(session)


@interaction_namespace.route("/points/<int:point_id>/")
class ModuleNavigator(Resource):
    @redirected_to_pages("direct navigation", ModuleType.TEST, ModuleType.THEORY_BLOCK)
    def get(self, user: User, module: Module, module_type: ModuleType, point_id: int) -> int:
        if module_type == ModuleType.TEST:
            return 3
        elif module_type == ModuleType.THEORY_BLOCK:
            return 1


@interaction_namespace.route("/points/<int:point_id>/reply/")
class TestReplySaver(Resource):
    @redirected_to_pages(ModuleType.TEST)
    # @interaction_namespace.argument_parser()
    def post(self, user: User, module: Module, point_id: int) -> int:
        pass


@interaction_namespace.route("/results/")
class TestResultGetter(Resource):
    @redirected_to_pages(ModuleType.TEST)
    def get(self, user: User, module: Module) -> int:
        pass
