from __future__ import annotations

from functools import wraps

from flask_fullstack import ResourceController, EventController, get_or_pop

from communities.tasks.tests_db import Test, Question


def test_finder(
    controller: ResourceController | EventController,
    *,
    use_test: bool = True,
    use_community: bool = False,
):
    def test_finder_wrapper(function):
        @controller.database_searcher(Test)
        @wraps(function)
        def test_finder_inner(*args, **kwargs):
            test = get_or_pop(kwargs, "test", use_test)
            community = get_or_pop(kwargs, "community", use_community)

            if test.community_id != community.id:
                controller.abort(404, Test.not_found_text)
            return function(*args, **kwargs)

        return test_finder_inner

    return test_finder_wrapper


def question_finder(
    controller: ResourceController | EventController,
    *,
    use_test: bool = False,
    use_question: bool = True,
):
    def question_finder_wrapper(function):
        @test_finder(controller, use_test=True, use_community=False)
        @controller.database_searcher(Question)
        @wraps(function)
        def question_finder_inner(*args, **kwargs):
            question = get_or_pop(kwargs, "question", use_question)
            test = get_or_pop(kwargs, "test", use_test)

            if question.test_id != test.id:
                controller.abort(404, Question.not_found_text)  # TODO pragma: no cover
            return function(*args, **kwargs)

        return question_finder_inner

    return question_finder_wrapper
