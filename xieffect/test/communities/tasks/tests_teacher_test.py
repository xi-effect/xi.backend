from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

import pytest
from flask_fullstack import dict_cut, SocketIOTestClient

from common import User
from communities.base import Community
from communities.tasks.tests_db import Test
from test.conftest import FlaskTestClient, delete_by_id


def test_create_test(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    test_community: int,
    file_id: int,
):
    test_data: dict[str, Any] = {
        "community_id": test_community,
        "page_id": 1,
        "name": "test task",
        "files": [file_id],
    }

    created_test_id: int = socketio_client.assert_emit_ack(
        event_name="new_test",
        data=test_data,
        expected_data=dict_cut(test_data, "page_id", "name"),
    ).get("id")

    client.get(
        f"/communities/{test_community}/tests/{created_test_id}/",
        expected_json={
            "name": test_data["name"],
            "files": [{"id": file_id}],
        },
    )
    delete_by_id(created_test_id, Test)


def test_get_wrong_test(
    client: FlaskTestClient,
    client_community_id: int,
    test_id: int,
):
    client.get(
        f"/communities/{client_community_id}/tests/{test_id}/",
        expected_a=Test.not_found_text,
        expected_status=404,
    )


@pytest.mark.parametrize(
    "update_data",
    [
        pytest.param({"name": "update", "description": "test", "files": []}, id="full"),
        pytest.param({"name": "second_update"}, id="partial"),
    ],
)
def test_update_test(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    test_id: int,
    test_community: int,
    test_ids: dict[str, int],
    update_data: dict[str, Any],
):
    socketio_client.assert_emit_ack(
        event_name="update_test",
        data={**test_ids, **update_data},
        expected_data=update_data,
    )

    client.get(
        f"/communities/{test_community}/tests/{test_id}/",
        expected_json=update_data,
    )


def test_delete_test(
    client: FlaskTestClient,
    socketio_client: SocketIOTestClient,
    test_id: int,
    test_community: int,
    test_ids,
):
    socketio_client.assert_emit_success(event_name="delete_test", data=test_ids)

    client.get(
        f"/communities/{test_community}/tests/{test_id}/",
        expected_status=404,
        expected_a=Test.not_found_text,
    )


@pytest.mark.parametrize(
    ("entry_filter", "entry_order", "count"),
    [
        pytest.param("ALL", "CREATED", 2, id="get_all_tests"),
        pytest.param("ACTIVE", "OPENED", 0, id="get_only_active"),
    ],
)
def test_teacher_test_pagination(
    entry_filter: str,
    entry_order: str,
    count: int,
    test_community: int,
    client: FlaskTestClient,
    test_maker: Callable[[], Test],
):
    json_data: dict[str, str] = {"filter": entry_filter, "order": entry_order}
    base_link: str = f"/communities/{test_community}/tests/"

    created: list[int] = [test_maker().id for _ in range(2)]
    assert len(list(client.paginate(base_link, json=json_data))) == count

    if entry_filter == "ACTIVE":
        for test in created:
            test: Test = Test.find_by_id(test)
            test.opened = datetime.utcnow()
            count += 1

    instance_list: list[dict] = list(client.paginate(base_link, json=json_data))
    assert instance_list[count - 1].get("id") == created[-1]
    assert len(instance_list) == count


def test_sio_update_foreign_test(
    socketio_client: SocketIOTestClient,
    client_community_id: int,
    test_id: int,
):
    socketio_client.assert_emit_ack(
        event_name="update_test",
        data={
            "name": "foreign test",
            "community_id": client_community_id,
            "test_id": test_id,
        },
        expected_code=404,
        expected_message=Test.not_found_text,
    )


def test_sio_delete_foreign_test(
    socketio_client: SocketIOTestClient,
    client_community_id: int,
    test_id: int,
):
    socketio_client.assert_emit_ack(
        event_name="delete_test",
        data={"community_id": client_community_id, "test_id": test_id},
        expected_code=404,
        expected_message=Test.not_found_text,
    )


def test_test_constraints(
    table: type[User | Community],
    base_client_test_id: int,
    base_user_id: int,
    community_id: int,
):
    delete_by_id(base_user_id if (table == User) else community_id, table)
    assert Test.find_by_id(base_client_test_id) is None
