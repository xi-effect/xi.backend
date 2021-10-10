from flask import redirect
from flask_restx import Resource

from componets import Namespace, with_session, with_auto_session
from education.elements import Module, Point
from education.sessions import StandardModuleSession as SMS, TestModuleSession as TMS
from users import User


def redirected_to_pages(func):  # session related parts have to be redone!!!!!!!
    @interaction_namespace.jwt_authorizer(User, chek_only=True)
    def inner_redirected_to_pages(*args, **kwargs):
        return redirect(f"/pages/{func(*args, **kwargs)}/")

    return inner_redirected_to_pages


interaction_namespace: Namespace = Namespace("interaction", path="")


# module_type: ModuleType = ModuleType(module.type)
# if module_type == ModuleType.STANDARD:
#     return {"session": SMS.find_or_create(session, user.id, module.id).id}
# elif module_type == ModuleType.PRACTICE_BLOCK:
#     return redirect(f"/modules/{module.id}/next/")
# elif module_type == ModuleType.THEORY_BLOCK:
#     return redirect(f"/modules/{module.id}/contents/")
# elif module_type == ModuleType.TEST:
#     return {"test": TMS.find_or_create(session, user.id, module.id).id}


@interaction_namespace.route("/sessions/<int:session_id>/")
class StandardProgresser(Resource):  # POST /sessions/<int:session_id>/
    @with_auto_session  # redo!!
    @redirected_to_pages
    @interaction_namespace.database_searcher(SMS, "session_id", "session")
    def post(self, session: SMS):
        return session.next_page_id()


@interaction_namespace.route("/module/<int:module_id>/next/")
class PracticeGenerator(Resource):  # GET /module/<int:module_id>/next/
    @redirected_to_pages
    @interaction_namespace.database_searcher(Module, "module_id", "module")
    def get(self, session, module: Module):
        return module.get_any_point(session).execute()


@interaction_namespace.route("/module/<int:module_id>/contents/")
class TheoryContentsGetter(Resource):  # GET /module/<int:module_id>/contents/
    @interaction_namespace.jwt_authorizer(User, chek_only=True, use_session=False)
    @interaction_namespace.database_searcher(Module, "module_id", "module")
    def get(self, module: Module):
        pass  # not done!


@interaction_namespace.route("/module/<int:module_id>/points/<int:point_id>/")
class TheoryNavigator(Resource):  # GET /module/<int:module_id>/points/<int:point_id>/
    @with_session
    @redirected_to_pages
    @interaction_namespace.database_searcher(Module, "module_id", "module")
    def get(self, session, module: Module, point_id: int):
        return Point.find_and_execute(session, module.id, point_id)


@interaction_namespace.route("/tests/<int:test_id>/contents/")
class TestContentsGetter(Resource):  # GET /tests/<int:test_id>/contents/
    @interaction_namespace.jwt_authorizer(User, chek_only=True, use_session=False)
    @interaction_namespace.database_searcher(TMS, "test_id", "test")
    def get(self, test: TMS):
        pass  # not done!


@interaction_namespace.route("/tests/<int:test_id>/points/<int:task_id>/")
class TestNavigator(Resource):  # GET /tests/<int:test_id>/points/<int:task_id>/
    @interaction_namespace.jwt_authorizer(User, chek_only=True, use_session=False)
    @interaction_namespace.database_searcher(TMS, "test_id", "test")
    def get(self, test: TMS, task_id: int):
        return test.get_task(task_id)


@interaction_namespace.route("/tests/<int:test_id>/tasks/<int:task_id>/reply/")
class TestReplySaver(Resource):  # P*T /tests/<int:test_id>/tasks/<int:task_id>/reply/
    @interaction_namespace.jwt_authorizer(User, chek_only=True)
    @interaction_namespace.database_searcher(TMS, "test_id", "test")
    def post(self, session, test: TMS, task_id: int, reply):
        test.set_reply(session, task_id, reply)
        return {"a": True}

    def put(self, *args, **kwargs):
        self.post(*args, **kwargs)


@interaction_namespace.route("/tests/<int:test_id>/results/")
class TestResultCollector(Resource):  # GET /tests/<int:test_id>/results/
    @interaction_namespace.jwt_authorizer(User, chek_only=True, use_session=False)
    @interaction_namespace.database_searcher(TMS, "test_id", "test")
    def get(self, test: TMS):
        return test.collect_results()
