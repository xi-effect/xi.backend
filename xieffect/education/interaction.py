from flask import redirect
from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import Namespace, with_session, with_auto_session
from .elements import Module, Point, ModuleType
from .sessions import StandardModuleSession, TestModuleSession
from users import User


def redirected_to_pages(func):
    @interaction_namespace.jwt_authorizer(User, check_only=True)
    def inner_redirected_to_pages(*args, **kwargs):
        return redirect(f"/pages/{func(*args, **kwargs)}/")

    return inner_redirected_to_pages


interaction_namespace: Namespace = Namespace("interaction", path="/modules/<int:module_id>/")


@interaction_namespace.route("/next/")
class ModuleProgresser(Resource):
    @interaction_namespace.jwt_authorizer(User)
    @interaction_namespace.database_searcher(Module, use_session=True)
    def post(self, session, user: User, module: Module):
        if module.type == ModuleType.STANDARD:
            pass
        elif module.type == ModuleType.PRACTICE_BLOCK:
            pass
        else:
            return {"a": f"Module of type {module.type} can't use linear progression"}, 400


@interaction_namespace.route("/points/<int:point_id>/")
class ModuleNavigator(Resource):
    @interaction_namespace.jwt_authorizer(User)
    @interaction_namespace.database_searcher(Module, use_session=True)
    def get(self, user: User, module: Module, point_id: int):
        if module.type == ModuleType.TEST:
            pass
        elif module.type == ModuleType.THEORY_BLOCK:
            pass
        else:
            return {"a": f"Module of type {module.type} can't use direct navigation"}, 400


@interaction_namespace.route("/points/<int:point_id>/reply/")
class TestReplySaver(Resource):
    @interaction_namespace.jwt_authorizer(User)
    @interaction_namespace.database_searcher(Module, use_session=True)
    # @interaction_namespace.argument_parser()
    def post(self, user: User, module: Module, point_id: int):
        pass


@interaction_namespace.route("/results/")
class TestResultGetter(Resource):
    @interaction_namespace.jwt_authorizer(User)
    @interaction_namespace.database_searcher(Module, use_session=True)
    def get(self, user: User, module: Module):
        pass
