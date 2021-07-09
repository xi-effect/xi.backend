from enum import Enum
from typing import List, Dict

from flask import redirect
from flask_restful import Resource
from flask_restful.reqparse import RequestParser

from api_resources.base.checkers import jwt_authorizer, database_searcher, argument_parser, lister
from api_resources.base.parsers import counter_parser
from database import User, Course, CourseFilterSession
from webhooks import send_discord_message, WebhookURLs


class FilterGetter(Resource):  # [GET] /filters/
    @jwt_authorizer(User)
    def get(self, user: User):
        return {"a": user.get_filter_bind()}


class SortType(str, Enum):
    POPULARITY = "popularity"
    VISIT_DATE = "visit-date"
    CREATION_DATE = "creation-date"


COURSES_PER_REQUEST: int = 12


class CourseLister(Resource):  # [POST] /courses/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("filters", type=dict, required=False)
    parser.add_argument("sort", required=False)

    @lister(12, argument_parser=argument_parser(parser, "counter", "filters", "sort"))
    def post(self, user: User, start: int, finish: int, filters: Dict[str, str], sort: str):
        try:
            if sort is None:
                sort: SortType = SortType.POPULARITY
            else:
                sort: SortType = SortType(sort)
        except ValueError:
            return {"a": f"Sorting '{sort}' is not supported"}, 406

        if filters is not None:
            if "global" in filters.keys():
                if "owned" in filters["global"]:  # TEMPORARY
                    return redirect("/cat/courses/owned/", 307)
                user.set_filter_bind(filters["global"])
            else:
                user.set_filter_bind()
        user_id: int = user.id

        result: List[Course] = Course.get_course_list(filters, user_id, start, finish-start)

        if sort == SortType.POPULARITY:
            result.sort(key=lambda x: x.popularity, reverse=True)
        elif sort == SortType.VISIT_DATE:
            result.sort(key=lambda x: (CourseFilterSession.find_visit_date(user_id, x.id), x.popularity), reverse=True)
        elif sort == SortType.CREATION_DATE:
            result.sort(key=lambda x: (x.creation_date.timestamp(), x.popularity), reverse=True)

        return list(map(lambda x: x.to_json(user_id), result))


class HiddenCourseLister(Resource):
    @lister(-12)
    def post(self, user: User, start: int, finish: int) -> list:
        result = list()
        for course_id in CourseFilterSession.filter_ids_by_user(user.id, start, finish - start, hidden=True):
            course: Course = Course.find_by_id(course_id)
            result.append(course.to_short_json())
        return result


class CoursePreferences(Resource):  # [POST] /courses/<int:course_id>/preference/
    parser: RequestParser = RequestParser()
    parser.add_argument("a", required=True)

    @jwt_authorizer(User)
    @database_searcher(Course, "course_id", check_only=True)
    @argument_parser(parser, ("a", "operation"))
    def post(self, course_id: int, user: User, operation: str):
        course: CourseFilterSession = CourseFilterSession.find_or_create(user.id, course_id)
        course.change_preference(operation)
        return {"a": True}


class CourseReporter(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("reason", required=True)
    parser.add_argument("message", required=False)

    @jwt_authorizer(User, None)
    @database_searcher(Course, "course_id", "course")
    @argument_parser(parser, "reason", "message")
    def post(self, course: Course, reason: str, message: str):
        send_discord_message(
            WebhookURLs.COMPLAINER,
            f"Появилась новая жалоба на курс #{course.id} ({course.name})\n"
            f"Причина: {reason}" + f"\nСообщение: {message}" if message is not None else ""
        )
        return {"a": True}


class ShowAll(Resource):  # test
    @jwt_authorizer(User)
    def get(self, user: User):
        CourseFilterSession.change_by_user(user.id, "show")
        return {"a": True}
