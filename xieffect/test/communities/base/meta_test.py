from __future__ import annotations

from collections.abc import Callable

from flask.testing import FlaskClient
from flask_fullstack import check_code, dict_equal
from pytest import mark

from common.testing import SocketIOTestClient
from communities.base import Participant
from ..conftest import assert_create_community


def get_communities_list(client: FlaskClient) -> list[dict]:
    result = check_code(client.get("/home/")).get("communities")
    assert isinstance(result, list)
    return result


def get_participants_list(
    client: FlaskClient, community_id: int, username: str | None = None
) -> list[dict]:
    link = f"/communities/{community_id}/participants/"
    if username is not None:
        link += f"?search={username}"
    result = check_code(
        client.get(
            link,
            json={"counter": 20, "offset": 0},
        )
    ).get("results")
    assert isinstance(result, list)
    return result


@mark.order(1000)
def test_meta_creation(client: FlaskClient, socketio_client: SocketIOTestClient):
    community_ids = [d["id"] for d in get_communities_list(client)]

    community_data = {"name": "12345", "description": "test"}
    community_id = assert_create_community(socketio_client, community_data)
    community_ids.append(community_id)

    found = False
    for data in get_communities_list(client):
        assert data["id"] in community_ids
        if data["id"] == community_id:
            assert not found
            assert dict_equal(data, community_data, *community_data.keys())
            found = True
    assert found


@mark.order(1005)
def test_community_list(client: FlaskClient, socketio_client: SocketIOTestClient):
    def assert_order():
        for i, data in enumerate(get_communities_list(client)):
            assert data["id"] == community_ids[i]

    socketio_client2 = SocketIOTestClient(client)
    community_ids = [d["id"] for d in get_communities_list(client)]
    assert_order()

    # TODO check order with new community listing

    # Creating
    def assert_double_create(community_data: dict):
        community_id = assert_create_community(socketio_client, community_data)
        socketio_client2.assert_received(
            "new_community", dict(community_data, id=community_id)
        )
        return community_id

    community_datas: list[dict[str, str | int]] = [
        {"name": "12345"},
        {"name": "54321", "description": "hi"},
        {"name": "test", "description": "i"},
    ]

    for community_data in community_datas:
        community_data["id"] = assert_double_create(community_data)
        community_ids.insert(0, community_data["id"])
    # assert_order

    # Reordering
    reorder_data = {"source_id": community_datas[0]["id"], "target_index": 0}
    socketio_client.assert_emit_success("reorder_community", reorder_data)
    socketio_client2.assert_only_received("reorder_community", reorder_data)

    community_ids.remove(reorder_data["source_id"])
    community_ids.insert(reorder_data["target_index"], reorder_data["source_id"])
    # assert_order

    # Leaving
    leave_data = {"community_id": community_datas[-1]["id"]}
    socketio_client.assert_emit_success("leave_community", leave_data)
    socketio_client2.assert_only_received("leave_community", leave_data)

    community_ids.remove(leave_data["community_id"])
    # assert_order


def test_participant(
    client: FlaskClient,
    multi_client: Callable[str],
    socketio_client: SocketIOTestClient,
    test_community: int,
    create_participant_role: Callable[str, int, FlaskClient],
    get_role_ids: Callable[FlaskClient, int],
    get_roles_list_by_ids: Callable[FlaskClient, int, list[int]],
):
    socketio_client2 = SocketIOTestClient(client)
    community_id_json = {"community_id": test_community}

    # Check successfully open participants-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("open_participants", community_id_json)

    create_participant_role(
        permission_type="MANAGE_PARTICIPANTS",
        community_id=test_community,
        client=socketio_client.flask_test_client,
    )

    user = check_code(client.get("/home/"))
    username, user_id = user.get("username"), user.get("id")
    participant = get_participants_list(client, test_community)[0]
    participant_id, community_id = participant.get("id"), participant.get("community-id")
    assert len(get_participants_list(client, test_community, username)) != 0

    role_ids = get_role_ids(client, test_community)
    assert isinstance(participant_id, int)

    # Participant update data
    participant_data = {
        "role_ids": role_ids,
        "participant_id": participant_id,
        **community_id_json,
    }
    roles = get_roles_list_by_ids(client, test_community, role_ids)
    successful_participant_data = {
        "community_id": community_id,
        "id": participant_id,
        "user_id": user_id,
        "roles": roles,
    }
    # Assert participant update with different data
    participant_result = socketio_client.assert_emit_ack(
        "update_participant_role", participant_data
    )

    assert dict_equal(
        participant_result,
        successful_participant_data,
        *successful_participant_data.keys(),
    )

    socketio_client2.assert_only_received(
        "update_participant_role", successful_participant_data
    )

    create_participant_role(
        permission_type="MANAGE_PARTICIPANTS",
        community_id=test_community,
        client=socketio_client.flask_test_client,
    )

    slice_role_ids = len(role_ids) // 2
    participant_data["role_ids"] = role_ids[slice_role_ids:]
    second_participant_result = socketio_client.assert_emit_ack(
        "update_participant_role", participant_data
    )

    successful_participant_data["roles"] = get_roles_list_by_ids(
        client, test_community, role_ids[slice_role_ids:]
    )

    assert dict_equal(
        second_participant_result,
        successful_participant_data,
        *successful_participant_data.keys(),
    )

    socketio_client2.assert_only_received(
        "update_participant_role", successful_participant_data
    )

    # delete participant data
    delete_data = {"community_id": test_community, "participant_id": participant_id}

    create_participant_role(
        permission_type="MANAGE_PARTICIPANTS",
        community_id=test_community,
        client=socketio_client.flask_test_client,
    )

    socketio_client.assert_emit_success("delete_participant_role", delete_data, code=400, message="Target is the source")

    new_user_id = check_code(multi_client("2@user.user").get("/home/")).get("id")
    new_participant_id = Participant.create(test_community, new_user_id).id

    delete_data["participant_id"] = new_participant_id

    socketio_client.assert_emit_success("delete_participant_role", delete_data)
    socketio_client2.assert_only_received("delete_participant_role", delete_data)

    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("close_participants", community_id_json)
