from flask import redirect
from flask_restful import Resource

from api_resources.base.checkers import jwt_authorizer, database_searcher
from database import Course, User, Session


class CourseMapper(Resource):
    @jwt_authorizer(User)
    @database_searcher(Course, "course_id", "course")
    def get(self, user: User, course: Course):
        session_id: int = Session.create(user.id, course.id)

        result: dict = user.get_course_relation(course.id)
        result.update({
            "session": session_id,
            "description": "Крутое описание курса!",
            "map": [
                {
                    "id": "0",
                    "type": "input",
                    "data": {
                        "label": "Введение"
                    },
                    "position": {
                        "x": 250,
                        "y": 5
                    },
                    "style": {
                        "background": "#357a38",
                        "color": "#e0e0e0",
                        "cursor": "pointer",
                        "border": "1px solid #777"
                    }
                },
                {
                    "id": "1",
                    "type": "output",
                    "data": {
                        "label": "Механика"
                    },
                    "position": {
                        "x": 100,
                        "y": 100
                    },
                    "style": {
                        "background": "#3f50b5",
                        "color": "#e0e0e0",
                        "cursor": "pointer",
                        "border": "1px solid #777"
                    }
                },
                {
                    "id": "2",
                    "type": "default",
                    "data": {
                        "label": "Электротехника"
                    },
                    "position": {
                        "x": 400,
                        "y": 100
                    },
                    "style": {
                        "background": "#3f50b5",
                        "color": "#e0e0e0",
                        "cursor": "pointer",
                        "border": "5px solid #357a38"
                    }
                },
                {
                    "id": "3",
                    "type": "output",
                    "data": {
                        "label": "Схемотехника"
                    },
                    "position": {
                        "x": 400,
                        "y": 200
                    },
                    "style": {
                        "background": "rgb(183, 28, 28, .8)",
                        "color": "#e0e0e0",
                        "cursor": "not-allowed",
                        "border": "1px solid #777"
                    }
                },
                {
                    "id": "interaction-e1-2",
                    "source": "0",
                    "target": "1"
                },
                {
                    "id": "interaction-e1-3",
                    "source": "0",
                    "target": "2"
                },
                {
                    "id": "interaction-e1-4",
                    "source": "2",
                    "target": "3"
                }
            ],
            "stats": [
                {
                    "value": 40,
                    "label": "Общий прогресс"
                },
                {
                    "value": 1,
                    "maximum": 3,
                    "label": "Завершено модулей"
                }
            ]
        })  # test
        return result


class SessionCourseMapper(Resource):  # /map/
    @jwt_authorizer(User, None)
    @database_searcher(Session, "session_id", "session")
    def get(self, session: Session):
        return redirect(f"/courses/{session.course_id}/map/")


class ModuleOpener(Resource):  # /modules/<ID>/
    @jwt_authorizer(User, None)
    @database_searcher(Session, "session_id", "session")
    def get(self, module_id: int, session: Session):
        session.open_module(module_id)
        return redirect(f"/pages/{session.next_page_id()}/")


class Progresser(Resource):  # /next/
    @jwt_authorizer(User, None)
    @database_searcher(Session, "session_id", "session")
    def post(self, session: Session):
        return redirect(f"/pages/{session.next_page_id()}/")


class Navigator(Resource):
    @jwt_authorizer(User, None)
    @database_searcher(Session, "session_id", "session")
    def get(self, point_id: int, session: Session):
        return redirect(f"/pages/{session.execute_point(point_id)}/")


class ContentsGetter(Resource):
    @jwt_authorizer(User, None)
    @database_searcher(Session, "session_id", "session")
    def get(self, session: Session):
        pass


class TestChecker(Resource):
    @jwt_authorizer(User, None)
    @database_searcher(Session, "session_id", "session")
    def post(self, session: Session):
        pass


class PageGetter(Resource):
    @jwt_authorizer(User, None)
    def get(self, page_id: int):
        if page_id == 0:
            pass
        elif page_id == 1:
            pass
        elif page_id == 2:
            pass
        elif page_id == 3:
            pass
