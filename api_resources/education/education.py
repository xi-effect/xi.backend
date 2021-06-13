from enum import Enum
from typing import List, Dict

from flask import redirect
from flask_restful import Resource
from flask_restful.reqparse import RequestParser

from api_resources.base.checkers import jwt_authorizer, database_searcher, argument_parser, lister
from api_resources.base.discorder import send_discord_message, WebhookURLs
from api_resources.base.parsers import counter_parser
from database import Filters, User, Course


class FilterGetter(Resource):  # [GET] /filters/
    @jwt_authorizer(User)
    def get(self, user: User):
        return user.get_filter_binds()


class SortType(str, Enum):
    POPULARITY = "popularity"
    VISIT_DATE = "visit-date"
    CREATION_DATE = "creation-date"


COURSES_PER_REQUEST: int = 12


class CourseLister(Resource):  # [POST] /courses/
    parser: RequestParser = counter_parser.copy()
    parser.add_argument("filters", type=dict, required=False)
    parser.add_argument("search", required=False)
    parser.add_argument("sort", required=False)

    @lister(User, 12, "user", argument_parser(parser, "counter", "filters", "search", "sort"))
    def post(self, user: User, start: int, finish: int, search: str,
             filters: Dict[str, List[str]], sort: str):
        user_filters: Filters = user.get_filters()

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
                user_filters.update_binds(filters["global"])
            else:
                user_filters.update_binds(list())
            user.update_filters(user_filters)

        result: List[Course] = Course.get_course_list(
            filters, search, user_filters, start, finish-start)

        if sort == SortType.POPULARITY:
            result.sort(key=lambda x: x.popularity, reverse=True)
        elif sort == SortType.VISIT_DATE:
            result.sort(key=lambda x: (user_filters.get_visit_date(x.id), x.popularity), reverse=True)
        elif sort == SortType.CREATION_DATE:
            result.sort(key=lambda x: x.creation_date.timestamp(), reverse=True)

        return list(map(lambda x: x.to_json(user_filters), result))


class HiddenCourseLister(Resource):
    @lister(User, -12, "user")
    def post(self, user: User, start: int, finish: int) -> list:
        user_filters: Filters = user.get_filters()

        result = list()
        for course_id in user_filters.hidden_courses[finish:start if start != 0 else None]:
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
        filters: Filters = user.get_filters()

        if operation == "hide":
            filters.hide_course(course_id)
        elif operation == "show":
            filters.unhide_course(course_id)
        elif operation == "star":
            filters.star_course(course_id)
        elif operation == "unstar":
            filters.unstar_course(course_id)
        elif operation == "pin":
            filters.pin_course(course_id)
        elif operation == "unpin":
            filters.unpin_course(course_id)
        user.update_filters(filters)

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
        filters: Filters = user.get_filters()
        filters.hidden_courses = list()
        user.update_filters(filters)
        return {"a": True}
