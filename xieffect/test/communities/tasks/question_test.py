from __future__ import annotations

from typing import Any

import pytest
from flask_fullstack import dict_cut, SocketIOTestClient

from communities.tasks.tests_db import Question, QuestionKind
from test.conftest import FlaskTestClient, delete_by_id


@pytest.fixture()
def question_data(test_id: int) -> dict[str, Any]:
    return {
        "text": "Test question",
        "test_id": test_id,
        "kind": QuestionKind.CHOICE.to_string(),
    }


@pytest.fixture()
def question_id(question_data: dict[str, Any]) -> int:
    question: Question = Question.create(
        **dict(question_data, kind=QuestionKind.CHOICE)
    )
    yield question.id
    delete_by_id(question.id, Question)


@pytest.fixture()
def question_ids(
    test_ids: dict[str, int],
    question_id: int,
) -> dict[str, int]:
    return {
        **test_ids,
        "question_id": question_id,
    }


def test_open_close_questions(
    socketio_client: SocketIOTestClient, test_ids: dict[str, int]
):
    socketio_client.assert_emit_success(
        event_name="open_questions",
        data=test_ids,
    )

    socketio_client.assert_emit_success(
        event_name="close_questions",
        data=test_ids,
    )


def test_create_question(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    test_id: int,
    test_community: int,
    question_data: dict[str, Any],
):
    socketio_client.assert_emit_ack(
        event_name="new_question",
        data={
            "community_id": test_community,
            **question_data,
        },
        expected_data={**dict_cut(question_data, "kind", "text"), "id": int},
    )
    client.get(
        f"/communities/{test_community}/tests/{test_id}/",
        expected_json={"questions": [dict_cut(question_data, "kind", "text")]},
    )


@pytest.mark.parametrize(
    "data",
    [
        pytest.param({"text": "update", "kind": "detailed"}, id="full"),
        pytest.param({"kind": "simple"}, id="partial"),
    ],
)
def test_update_question(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    test_id: int,
    test_community: int,
    question_ids: dict[str, int],
    data: dict[str, str],
):
    socketio_client.assert_emit_ack(
        event_name="update_question",
        data={**question_ids, **data},
        expected_data=data,
    )

    client.get(
        f"/communities/{test_community}/tests/{test_id}/",
        expected_json={"questions": [data]},
    )


def test_validation_kind(
    socketio_client: SocketIOTestClient,
    question_ids: dict[str, int],
):
    kind: str = "choice11223"
    socketio_client.assert_emit_ack(
        event_name="update_question",
        data={
            **question_ids,
            "text": "update",
            "kind": kind,
        },
        expected_code=400,
        expected_data=[{"msg": f"{kind} is not a valid QuestionKind"}],
    )


def test_delete_question(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    test_id: int,
    test_community: int,
    question_ids: dict[str, int],
):
    socketio_client.assert_emit_success(event_name="delete_question", data=question_ids)
    client.get(
        f"/communities/{test_community}/tests/{test_id}/",
        expected_json={"questions": []},
    )
