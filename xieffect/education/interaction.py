from functools import wraps
from typing import Optional

from flask import redirect
from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import Namespace, ResponseDoc
from users import User
from .elements import Module, Point, ModuleType
from .sessions import StandardModuleSession, TestModuleSession


interaction_namespace: Namespace = Namespace("interaction", path="/modules/<int:module_id>/")


def module_typed(op_name, *possible_module_types: ModuleType):
    def module_typed_wrapper(function):
        @interaction_namespace.doc_responses(ResponseDoc.error_response(400, "Unacceptable module type"))
        @interaction_namespace.jwt_authorizer(User)
        @interaction_namespace.database_searcher(Module, use_session=True)
        @wraps(function)
        def module_typed_inner(*args, **kwargs):
            module_type: ModuleType = kwargs["module"].type
            if module_type not in possible_module_types:
                return {"a": f"Module of type {module_type} can't use {op_name}"}, 400

            if len(possible_module_types) > 1:
                kwargs["module_type"] = module_type

            return function(*args, **kwargs)

        return module_typed_inner

    return module_typed_wrapper


def redirected_to_pages(op_name, *possible_module_types: ModuleType):
    def redirected_to_pages_wrapper(function):
        @interaction_namespace.doc_responses(ResponseDoc(302, r"Redirect to GET /pages/\<id\>/ with generated ID"))
        @module_typed(op_name, *possible_module_types)
        @wraps(function)
        def redirected_to_pages_inner(*args, **kwargs):
            result = function(*args, **kwargs)
            return redirect(f"/pages/{result}/") if isinstance(result, int) else result

        return redirected_to_pages_inner

    return redirected_to_pages_wrapper


@interaction_namespace.route("/next/")
class ModuleProgresser(Resource):
    @interaction_namespace.doc_responses(ResponseDoc.error_response(200, "You have reached the end"))
    @redirected_to_pages("linear progression", ModuleType.STANDARD, ModuleType.PRACTICE_BLOCK)
    def post(self, session, user: User, module: Module, module_type: ModuleType):
        """ Endpoint for progressing a Standard Module or Practice Block """

        if module_type == ModuleType.STANDARD:
            module_session: StandardModuleSession = StandardModuleSession.find_or_create(session, user.id, module.id)
            module_session.progress += 1
            if module_session.progress >= module.length:
                module_session.delete(session)
                return {"a": "You have reached the end"}
            return Point.find_and_execute(session, module, module_session.progress)

        elif module_type == ModuleType.PRACTICE_BLOCK:
            return module.execute_random_point(session)


@interaction_namespace.route("/points/<int:point_id>/")
class ModuleNavigator(Resource):
    @redirected_to_pages("direct navigation", ModuleType.TEST, ModuleType.THEORY_BLOCK)
    def get(self, session, user: User, module: Module, module_type: ModuleType, point_id: int) -> int:
        """ Endpoint for navigating a Theory Block or Test """

        if module_type == ModuleType.TEST:
            return TestModuleSession.find_or_create(session, user.id, module.id).get_task(session, point_id)

        elif module_type == ModuleType.THEORY_BLOCK:
            return Point.find_and_execute(session, module, point_id)


def with_test_session(function):
    @interaction_namespace.doc_responses(ResponseDoc.error_response(404, TestModuleSession.not_found_text))
    @module_typed("reply & results functionality", ModuleType.TEST)
    @wraps(function)
    def with_test_session_inner(session, user: User, module: Module, *args, **kwargs):
        test_session: TestModuleSession = TestModuleSession.find_by_ids(session, user.id, module.id)
        if test_session is None:
            return {"a": TestModuleSession.not_found_text}, 404

        kwargs["test_session"] = test_session
        return function(session, *args, **kwargs)

    return with_test_session_inner


@interaction_namespace.route("/points/<int:point_id>/reply/")
class TestReplySaver(Resource):
    @with_test_session
    @interaction_namespace.a_response()
    # @interaction_namespace.argument_parser()
    def post(self, session, test_session: TestModuleSession, point_id: int) -> None:
        """ Saves user's reply to an open test """
        test_session.set_reply(session, point_id, None)  # temp


@interaction_namespace.route("/results/")
class TestResultGetter(Resource):
    @with_test_session
    @interaction_namespace.doc_responses(ResponseDoc(description="Some sort of TestResults object"))
    def get(self, session, test_session: TestModuleSession):
        """ Ends the test & returns the results / result page """
        return test_session.collect_results(session)
