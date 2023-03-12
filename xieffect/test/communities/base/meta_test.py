from __future__ import annotations

from flask.testing import FlaskClient
from flask_fullstack import check_code, dict_equal
from pytest import mark

from common.testing import SocketIOTestClient
from ..conftest import assert_create_community


def get_communities_list(client: FlaskClient) -> list[dict]:
    result = check_code(client.get("/home/")).get("communities")
    assert isinstance(result, list)
    return result


def get_participants_list(client: FlaskClient, username: str) -> list[dict]:
    result = check_code(
        client.get(
            f"/communities/?search={username}",
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
    socketio_client: SocketIOTestClient,
    test_community: int,
    create_participant_role,
    full_client,
    get_role_ids,
    get_roles_list_by_ids
):
    socketio_client2 = SocketIOTestClient(client)
    community_id_json = {"community_id": test_community}

    # Check successfully open participants-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("open_participants", community_id_json)

    create_participant_role(
        permission_type="MANAGE_PARTICIPANT",
        community_id=test_community,
        client=socketio_client.flask_test_client,
    )

    participant_id = get_participants_list(client, "")[0].get("id")
    role_ids = get_role_ids(client, test_community)
    assert isinstance(participant_id, int)
    participant_data = {
        "role_ids": role_ids,
        "participant_id": participant_id,
        **community_id_json,
    }
    # print(participant_data)

    response = client.get("/home/")
    user_id = check_code(response, get_json=True)["id"]
    roles = get_roles_list_by_ids(client, test_community, role_ids)
    successful_participant_data = {**community_id_json, "id": participant_id, "user_id": user_id, "roles": roles}
    participant_result = socketio_client.assert_emit_ack("update_participant_role", participant_data)
    socketio_client2.assert_only_received("update_participant_role", successful_participant_data)

    for role in participant_result['roles']:
        assert role in roles

    # Check successfully close participants-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("close_participants", community_id_json)
