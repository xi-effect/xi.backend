from __future__ import annotations

from typing import Iterator, Callable

from flask.testing import FlaskClient
from flask_socketio import SocketIOTestClient
from pytest import mark

from __lib__.flask_fullstack import check_code, dict_equal
from .conftest import socketio_client_factory

INVITATIONS_PER_REQUEST = 20


def assert_create_community(socketio_client: SocketIOTestClient, community_data: dict):
    ack = socketio_client.emit("new-community", community_data, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code", None) == 200

    result_data = ack.get("data", None)
    assert result_data is not None

    community_id = result_data.get("id", None)
    assert isinstance(community_id, int)
    assert dict_equal(result_data, community_data, *community_data.keys())
    return community_id


def get_communities_list(client: FlaskClient):
    result = check_code(client.get("/home/")).get("communities", None)
    assert isinstance(result, list)
    return result


@mark.order(1000)
def test_meta_creation(client: FlaskClient, socketio_client: SocketIOTestClient,
                       list_tester: Callable[[str, dict, int], Iterator[dict]]):
    community_ids = [d["id"] for d in get_communities_list(client)]

    community_data = {"name": "12345", "description": "test"}
    community_id = assert_create_community(socketio_client, community_data)
    community_ids.append(community_id)

    found = False
    for data in get_communities_list(client):
        assert data["id"] in community_ids
        if data["id"] == community_id:
            assert not found
            assert dict_equal(data, community_data, "name", "description")
            found = True
    assert found


@mark.order(1005)
def test_community_list(client: FlaskClient, socketio_client: SocketIOTestClient,
                        list_tester: Callable[[str, dict, int], Iterator[dict]]):
    def assert_order():
        for i, data in enumerate(get_communities_list(client)):
            assert data["id"] == community_ids[i]

    socketio_client2 = socketio_client_factory(client)
    community_ids = [d["id"] for d in get_communities_list(client)]
    assert_order()
    # TODO check order with new community listing

    # Creating
    def assert_double_create(community_data: dict):
        community_id = assert_create_community(socketio_client, community_data)

        events = socketio_client2.get_received()
        assert len(events) == 1
        assert events[0]["name"] == "new-community"
        assert len(events[0]["args"]) == 1

        assert len(events[0]["args"][0]) == len(community_data) + 1
        assert events[0]["args"][0].get("id", None) == community_id
        assert dict_equal(events[0]["args"][0], community_data, *community_data.keys())

        return community_id

    community_datas: list[dict[str, str | int]] = [
        {"name": "12345"}, {"name": "54321", "description": "hi"}, {"name": "test", "description": "i"}]

    for community_data in community_datas:
        community_data["id"] = assert_double_create(community_data)
        community_ids.insert(0, community_data["id"])
    # assert_order()

    # Reordering
    reorder_data = {"source-id": community_datas[0]["id"], "target-index": 0}
    ack = socketio_client2.emit("reorder-community", reorder_data, callback=True)
    assert dict_equal(ack, {"code": 200, "message": "Success"}, ("code", "message"))
    assert len(socketio_client2.get_received()) == 0

    events = socketio_client.get_received()
    assert len(events) == 1
    assert events[0]["name"] == "reorder-community"
    assert len(events[0]["args"]) == 1

    assert len(events[0]["args"][0]) == 2
    assert dict_equal(events[0]["args"][0], reorder_data, *reorder_data.keys())

    community_ids.remove(reorder_data["source-id"])
    community_ids.insert(reorder_data["target-index"], reorder_data["source-id"])
    # assert_order()

    # Leaving
    leave_data = {"community-id": community_datas[-1]["id"]}
    ack = socketio_client.emit("leave-community", leave_data, callback=True)
    assert dict_equal(ack, {"code": 200, "message": "Success"}, ("code", "message"))
    assert len(socketio_client.get_received()) == 0

    events = socketio_client2.get_received()
    assert len(events) == 1
    assert events[0]["name"] == "leave-community"
    assert len(events[0]["args"]) == 1

    assert len(events[0]["args"][0]) == 1
    assert dict_equal(events[0]["args"][0], leave_data, *leave_data.keys())

    community_ids.remove(leave_data["community-id"])
    # assert_order()


@mark.order(1020)  # TODO redo with sio
def test_invitations(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    community_data = {"name": "test", "description": "12345"}
    invitation_data = {"role": "base", "limit": 2, "days": 10}

    community_id = check_code(client.post("/communities/", json=community_data)).get("id", None)
    assert community_id is not None

    # check that the invitation list is empty
    assert len(list(list_tester(f"/communities/{community_id}/invitations/index/", {}, INVITATIONS_PER_REQUEST))) == 0

    # create a new invitation
    invitation = check_code(client.post(f"/communities/{community_id}/invitations/", json=invitation_data))
    assert "id" in invitation.keys()
    assert "code" in invitation.keys()

    # check if invitation list was updated
    data = list(list_tester(f"/communities/{community_id}/invitations/index/", {}, INVITATIONS_PER_REQUEST))
    assert len(data) == 1
    assert dict_equal(data[0], invitation, "id", "code")
    assert dict_equal(data[0], invitation_data, "role", "limit")

    # delete invitation & check again
    assert check_code(client.delete(f"/communities/{community_id}/invitations/{invitation['id']}/"))["a"]
    assert len(list(list_tester(f"/communities/{community_id}/invitations/index/", {}, INVITATIONS_PER_REQUEST))) == 0


@mark.order(1025)  # TODO redo with sio
def test_invitation_joins(multi_client: Callable[[str], FlaskClient],
                          list_tester: Callable[[str, dict, int], Iterator[dict]]):
    community_data = {"name": "test", "description": "12345"}

    # functions
    def create_invitation(invitation_data, skip_id: bool = False):
        invitation = check_code(anatol.post(f"/communities/{community_id}/invitations/", json=invitation_data))
        assert "id" in invitation.keys()
        assert "code" in invitation.keys()

        if skip_id:
            return invitation["code"]
        return invitation["id"], invitation["code"]

    def assert_successful_get(client: FlaskClient, code, joined: bool):
        data = check_code(client.get(f"/communities/join/{code}/"))
        assert data.get("joined", None) is joined
        assert data.get("authorized", None) is True
        community = data.get("community", None)
        assert community is not None
        assert dict_equal(community, community_data, *community_data.keys())

    def assert_invalid_invitation(client: FlaskClient, code: str):
        assert check_code(client.get(f"/communities/join/{code}/"), 400)["a"] == "Invalid invitation"
        assert check_code(client.post(f"/communities/join/{code}/"), 400)["a"] == "Invalid invitation"

    def assert_already_joined(client: FlaskClient, code: str):
        assert_successful_get(client, code, True)
        assert check_code(client.post(f"/communities/join/{code}/"), 400)["a"] == "User has already joined"

    def assert_successful_join(client: FlaskClient, invitation_id: int, code: str):
        for data in list_tester(f"/communities/{community_id}/invitations/index/", {}, INVITATIONS_PER_REQUEST):
            if data["id"] == invitation_id:
                limit_before = data.get("limit", None)
                break
        else:
            assert False, "Invitation not found inside assert_successful_join"

        assert_successful_get(client, code, False)
        assert dict_equal(check_code(client.post(f"/communities/join/{code}/")), community_data, *community_data.keys())

        if limit_before is None:
            return
        for data in list_tester(f"/communities/{community_id}/invitations/index/", {}, INVITATIONS_PER_REQUEST):
            if data["id"] == invitation_id:
                assert data["limit"] == limit_before - 1
                break
        else:
            assert limit_before == 1

    anatol = multi_client("1@user.user")
    vasil1 = multi_client("2@user.user")
    vasil2 = multi_client("3@user.user")
    vasil3 = multi_client("4@user.user")

    community_id = check_code(anatol.post("/communities/", json=community_data)).get("id", None)
    assert community_id is not None

    # testing joining & errors
    invitation_id1, code1 = create_invitation({"role": "base"})
    assert_invalid_invitation(vasil1, "hey")
    assert_already_joined(anatol, code1)
    assert_successful_join(vasil1, invitation_id1, code1)
    assert_already_joined(vasil1, code1)

    # testing counter limit
    invitation_id2, code2 = create_invitation({"role": "base", "limit": 1})
    assert_already_joined(vasil1, code2)
    assert_successful_join(vasil2, invitation_id2, code2)
    assert_invalid_invitation(vasil2, code2)  # , "User has already joined")
    assert_invalid_invitation(vasil3, code2)

    # testing time limit
    _, code3 = create_invitation({"role": "base", "days": 0})
    assert_already_joined(vasil1, code3)
    assert_already_joined(vasil2, code3)
    assert_invalid_invitation(vasil3, code3)

    # testing creating permissions errors
    message = check_code(vasil1.post(f"/communities/{community_id}/invitations/", json={"role": "base"}), 403)["a"]
    assert message == "Permission Denied: Low role"
    message = check_code(vasil3.post(f"/communities/{community_id}/invitations/", json={"role": "base"}), 403)["a"]
    assert message == "Permission Denied: Participant not found"

    # testing deleted invite
    assert check_code(anatol.delete(f"/communities/{community_id}/invitations/{invitation_id1}/"))["a"]
    assert_invalid_invitation(vasil1, code1)  # , "User has already joined")
    assert_invalid_invitation(vasil2, code1)  # , "User has already joined")
    assert_invalid_invitation(vasil3, code1)
