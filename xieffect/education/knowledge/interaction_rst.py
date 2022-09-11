from __future__ import annotations

from functools import wraps

from flask import redirect
from flask_restx import Resource, Model
from flask_restx.fields import Integer
from flask_restx.reqparse import RequestParser

from common import ResourceController, ResponseDoc, User
from .interaction_db import ModuleProgressSession, TestModuleSession, TestPointSession
from .modules_db import Module, ModuleType
from .results_db import TestResult

controller = ResourceController("interaction", path="/modules/<int:module_id>/")


def module_typed(op_name, *possible_module_types: ModuleType):
    def module_typed_wrapper(function):
        @controller.doc_abort(400, "Unacceptable module type")
        @controller.jwt_authorizer(User)
        @controller.database_searcher(Module)
        @wraps(function)
        def module_typed_inner(*args, **kwargs):
            module_type: ModuleType = kwargs["module"].type
            if module_type not in possible_module_types:
                controller.abort(
                    400, f"Module of type {module_type.to_string()} can't use {op_name}"
                )

            if len(possible_module_types) > 1:
                kwargs["module_type"] = module_type

            return function(*args, **kwargs)

        return module_typed_inner

    return module_typed_wrapper


def redirected_to_pages(op_name, *possible_module_types: ModuleType):
    def redirected_to_pages_wrapper(function):
        @controller.doc_abort(302, r"Redirect to GET /pages/\<id\>/ with generated ID")
        @module_typed(op_name, *possible_module_types)
        @wraps(function)
        def redirected_to_pages_inner(*args, **kwargs):
            result = function(*args, **kwargs)
            return redirect(f"/pages/{result}/") if isinstance(result, int) else result

        return redirected_to_pages_inner

    return redirected_to_pages_wrapper


def with_point_id(function):
    @controller.doc_abort(404, "Point is not in this module")
    @wraps(function)
    def with_point_id_inner(*args, **kwargs):
        if 0 <= kwargs["point_id"] < kwargs["module"].length:
            return function(*args, **kwargs)
        return {"a": "Point is not in this module"}, 404

    return with_point_id_inner


@controller.route("/open/")
class ModuleOpener(Resource):
    @controller.doc_responses(ResponseDoc(model=Model("ID Response", {"id": Integer})))
    @redirected_to_pages(
        "progress saving", ModuleType.STANDARD, ModuleType.THEORY_BLOCK
    )
    def get(self, user: User, module: Module, module_type: ModuleType):
        """Endpoint for starting a Standard Module or Theory Block from the last visited point"""

        module_session: ModuleProgressSession | None = (
            ModuleProgressSession.find_by_ids(user.id, module.id)
        )
        if module_type == ModuleType.STANDARD:
            if module_session is None or module_session.progress is None:
                return module.execute_point(0, 0.4 + 0.2 * user.theory_level)
            return module.execute_point(
                module_session.progress, module_session.theory_level
            )
        # ModuleType.THEORY_BLOCK
        return {"id": None if module_session is None else module_session.progress}


@controller.route("/next/")
class ModuleProgresser(Resource):
    @controller.doc_abort(200, "You have reached the end")
    @redirected_to_pages(
        "linear progression", ModuleType.STANDARD, ModuleType.PRACTICE_BLOCK
    )
    def post(self, user: User, module: Module, module_type: ModuleType):
        """Endpoint for progressing a Standard Module or Practice Block"""

        if module_type == ModuleType.STANDARD:
            module_session: ModuleProgressSession = (
                ModuleProgressSession.find_or_create(user.id, module.id)
            )

            if module_session.progress is None:
                module_session.progress = 1
                module_session.theory_level = 0.5
            else:
                module_session.progress += 1

            if module_session.progress >= module.length:
                module_session.delete()
                return {"a": "You have reached the end"}

            return module.execute_point(
                module_session.progress, module_session.get_theory_level()
            )

        # ModuleType.PRACTICE_BLOCK
        return module.execute_point()


@controller.route("/points/<int:point_id>/")
class ModuleNavigator(Resource):
    @redirected_to_pages("direct navigation", ModuleType.TEST, ModuleType.THEORY_BLOCK)
    @with_point_id
    def get(
        self,
        user: User,
        module: Module,
        module_type: ModuleType,
        point_id: int,
    ) -> int:
        """Endpoint for navigating a Theory Block or Test"""

        if module_type == ModuleType.TEST:
            new_test_session = TestModuleSession.find_or_create(user.id, module.id)
            new_test_point = new_test_session.find_point_session(point_id)
            if new_test_point is None:
                new_test_point = new_test_session.create_point_session(point_id, module)
            return new_test_point.page_id

        # ModuleType.THEORY_BLOCK
        module_session: ModuleProgressSession = ModuleProgressSession.find_or_create(
            user.id, module.id
        )
        module_session.progress = point_id
        return module.execute_point(point_id)


def with_test_session(function):
    @controller.doc_abort(404, TestModuleSession.not_found_text)
    @module_typed("reply & results functionality", ModuleType.TEST)
    @wraps(function)
    def with_test_session_inner(user: User, module: Module, *args, **kwargs):
        test_session: TestModuleSession = TestModuleSession.find_by_ids(
            user.id, module.id
        )
        if test_session is None:
            return {"a": TestModuleSession.not_found_text}, 404

        kwargs["test_session"] = test_session
        return function(*args, **kwargs)

    return with_test_session_inner


@controller.route("/points/<int:point_id>/reply/")
class TestReplyManager(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("right-answers", type=int, dest="right_answers", required=True)
    parser.add_argument("total-answers", type=int, dest="total_answers", required=True)
    parser.add_argument("answers", type=dict, required=True)

    @controller.doc_responses(ResponseDoc(200, "Answers object"))
    @module_typed("reply functionality", ModuleType.TEST)
    @with_point_id
    def get(self, point_id, user: User, module: Module):
        point_session: TestPointSession = TestPointSession.find_by_ids(
            user.id, module.id, point_id
        )
        if point_session is None or point_session.answers is None:
            return {}
        return point_session.answers

    @module_typed("reply functionality", ModuleType.TEST)
    @with_point_id
    @controller.argument_parser(parser)
    @controller.a_response()
    def post(
        self,
        point_id,
        user: User,
        module: Module,
        right_answers: int,
        total_answers: int,
        answers,
    ) -> bool:
        """Saves user's reply to an open test"""
        point_session = TestPointSession.find_by_ids(user.id, module.id, point_id)
        if point_session is not None:
            point_session.right_answers = right_answers
            point_session.total_answers = total_answers
            point_session.answers = answers
            return True
        return False


@controller.route("/results/")
class TestSaver(Resource):
    @controller.jwt_authorizer(User)
    @controller.database_searcher(Module)
    @controller.marshal_with(TestResult.FullModel)
    def get(self, user: User, module: Module):
        test_session = TestModuleSession.find_by_ids(user.id, module.id)
        if test_session is None:
            controller.abort(400, "Test not started")
        t = test_session.collect_all()
        print(t[0].right_answers)
        result = controller.marshal(t, TestPointSession.IndexModel)
        print(result)
        return TestResult.create(user.id, module, result)
