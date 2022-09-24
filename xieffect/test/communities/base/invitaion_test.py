from __future__ import annotations

from collections.abc import Iterator, Callable
from datetime import datetime, timedelta

from flask.testing import FlaskClient
from pytest import mark, fixture

from __lib__.flask_fullstack import check_code, dict_equal
from common.testing import SocketIOTestClient
from .meta_test import assert_create_community

INVITATIONS_PER_REQUEST = 20


@fixture
def test_community(socketio_client: SocketIOTestClient) -> int:
    # TODO use yield & delete the community after
    return assert_create_community(socketio_client, {"name": "test"})


@mark.order(1020)
def test_invitations(client, list_tester, test_community):
    invitation_data = {
        "community-id": test_community,
        "role": "base",
        "limit": 2,
        "days": 10,
    }
    room_data = {"community-id": test_community}
    index_url = f"/communities/{test_community}/invitations/index/"

    # check that the invitation list is empty
    assert len(list(list_tester(index_url, {}, INVITATIONS_PER_REQUEST))) == 0

    # init sio & join rooms
    sio1 = SocketIOTestClient(client)
    sio2 = SocketIOTestClient(client)
    sio3 = SocketIOTestClient(client)
    sio4 = SocketIOTestClient(client)

    sio1.assert_emit_success("open-invites", room_data)
    sio2.assert_emit_success("open-invites", room_data)
    sio3.assert_emit_success("open-invites", room_data)
    sio3.assert_emit_success("close-invites", room_data)

    # create a new invitation
    invitation = sio1.assert_emit_ack("new-invite", invitation_data)
    assert isinstance(invitation, dict)
    assert "id" in invitation
    assert "code" in invitation
    assert dict_equal(invitation, invitation_data, "role", "limit")

    days = invitation_data.get("days")
    if days is not None:
        deadline = invitation.get("deadline")
        assert deadline is not None
        dt: datetime = datetime.fromisoformat(deadline)
        assert dt.day == (datetime.utcnow() + timedelta(days=days)).day

    sio2.assert_only_received("new-invite", invitation)
    sio3.assert_nop()
    sio4.assert_nop()

    # check if invitation list was updated
    data = list(list_tester(index_url, {}, INVITATIONS_PER_REQUEST))
    assert len(data) == 1
    assert dict_equal(data[0], invitation, *invitation.keys())

    # delete invitation & check again
    delete_data = {"community-id": test_community, "invitation-id": invitation["id"]}
    sio1.assert_emit_success("delete-invite", delete_data)
    sio2.assert_only_received("delete-invite", delete_data)
    sio3.assert_nop()
    sio4.assert_nop()

    assert len(list(list_tester(index_url, {}, INVITATIONS_PER_REQUEST))) == 0


def create_assert_successful_get(community_data):
    def assert_successful_get(client: FlaskClient, code, joined: bool):
        data = check_code(client.get(f"/communities/join/{code}/"))
        assert data.get("joined", None) is joined
        assert data.get("authorized", None) is True

        community = data.get("community", None)
        assert community is not None
        assert dict_equal(community, community_data, *community_data.keys())

    return assert_successful_get


def create_assert_successful_join(list_tester, community_id, community_data):
    assert_successful_get = create_assert_successful_get(community_data)

    def assert_successful_join(client: FlaskClient, invitation_id: int, code: str, *sio_clients: SocketIOTestClient):
        for data in list_tester(f"/communities/{community_id}/invitations/index/", {}, INVITATIONS_PER_REQUEST):
            if data["id"] == invitation_id:
                limit_before = data.get("limit", None)
                break
        else:
            raise AssertionError("Invitation not found inside assert_successful_join")

        assert_successful_get(client, code, joined=False)
        assert dict_equal(check_code(client.post(f"/communities/join/{code}/")), community_data, *community_data.keys())

        if limit_before is None:
            return
        for data in list_tester(f"/communities/{community_id}/invitations/index/", {}, INVITATIONS_PER_REQUEST):
            if data["id"] == invitation_id:
                assert data["limit"] == limit_before - 1
                break
        else:
            assert limit_before == 1

        for sio in sio_clients:
            events = sio.get_received()
            assert len(events) == 1
            assert (event := events[0]).get("name", None) == "new-community"

            args = event.get("args", None)
            assert isinstance(args, list) and len(args) == 1
            assert isinstance(args[0], dict)

            # TODO mb check community data

    return assert_successful_join


@mark.skip
@mark.order(1022)
def test_invitation_joins(
    base_client,
    multi_client: Callable[[str], FlaskClient],
    list_tester: Callable[[str, dict, int], Iterator[dict]]
):
    community_data = {"name": "test", "description": "12345"}

    # functions
    def create_invitation(invitation_data, skip_id: bool = False, check_auth: bool = True):
        invitation_data["community-id"] = community_id
        invitation = socketio_client1.emit("new-invite", invitation_data, callback=True)["data"]
        assert isinstance(invitation, dict)
        assert "id" in invitation
        assert "code" in invitation

        assert len(socketio_client1.get_received()) == 0
        assert len(socketio_client3.get_received()) == 0
        assert len(socketio_client4.get_received()) == 0

        events = socketio_client2.get_received()
        assert len(events) == 1
        assert (event := events[0]).get("name", None) == "new-invite"

        args = event.get("args", None)
        assert isinstance(args, list) and len(args) == 1
        assert isinstance((data := args[0]), dict)

        assert dict_equal(data, invitation_data, *[key for key in ("role", "limit") if key in invitation_data])
        days = invitation_data.get("days")
        if days is not None:
            deadline = data.get("deadline")
            assert deadline is not None
            dt: datetime = datetime.fromisoformat(deadline)
            assert dt.day == (datetime.utcnow() + timedelta(days=days)).day

        if check_auth:
            assert_unauthorized(invitation["code"])
        if skip_id:
            return invitation["code"]
        return invitation["id"], invitation["code"]

    def assert_unauthorized(code: str):
        data = check_code(base_client.get(f"/communities/join/{code}/"))
        assert data.get("joined", None) is False
        assert data.get("authorized", None) is False

        community = data.get("community", None)
        assert community is not None
        assert dict_equal(community, community_data, *community_data.keys())

        check_code(base_client.post(f"/communities/join/{code}/"), 401)

    assert_successful_get = create_assert_successful_get(community_data)

    def assert_invalid_invitation(client: FlaskClient, code: str):
        assert check_code(client.get(f"/communities/join/{code}/"), 400)["a"] == "Invalid invitation"
        assert check_code(client.post(f"/communities/join/{code}/"), 400)["a"] == "Invalid invitation"

    def assert_already_joined(client: FlaskClient, code: str):
        assert_successful_get(client, code, joined=True)
        assert check_code(client.post(f"/communities/join/{code}/"), 400)["a"] == "User has already joined"

    anatol = multi_client("1@user.user")
    vasil1 = multi_client("2@user.user")
    vasil2 = multi_client("3@user.user")
    vasil3 = multi_client("4@user.user")

    community_id = check_code(anatol.post("/communities/", json=community_data)).get("id", None)
    assert community_id is not None
    room_data = {"community-id": community_id}

    # init sio & join rooms
    def manage_room(sio: SocketIOTestClient, join: bool = True):
        ack = sio.emit("open-invites" if join else "close-invites", room_data, callback=True)
        assert isinstance(ack, dict)
        assert ack.get("code", None) == 200
        assert ack.get("message", None) == "Success"

    socketio_client1 = SocketIOTestClient(anatol)
    socketio_client2 = SocketIOTestClient(anatol)
    socketio_client3 = SocketIOTestClient(anatol)
    socketio_client4 = SocketIOTestClient(anatol)

    socketio_client5 = SocketIOTestClient(vasil1)
    socketio_client6 = SocketIOTestClient(vasil1)

    manage_room(socketio_client1)
    manage_room(socketio_client2)
    manage_room(socketio_client3)
    manage_room(socketio_client3, join=False)

    assert_successful_join = create_assert_successful_join(list_tester, community_id, community_data)

    # testing joining & errors
    invitation_id1, code1 = create_invitation({"role": "base"})
    assert_invalid_invitation(vasil1, "hey")
    assert_already_joined(anatol, code1)
    assert_successful_join(vasil1, invitation_id1, code1, socketio_client5, socketio_client6)
    assert_already_joined(vasil1, code1)

    # testing counter limit
    invitation_id2, code2 = create_invitation({"role": "base", "limit": 1})
    assert_already_joined(vasil1, code2)
    assert_successful_join(vasil2, invitation_id2, code2)
    assert_invalid_invitation(vasil2, code2)  # , "User has already joined")
    assert_invalid_invitation(vasil3, code2)

    # testing time limit
    code3 = create_invitation({"role": "base", "days": 0}, skip_id=True, check_auth=False)
    assert_already_joined(vasil1, code3)
    assert_already_joined(vasil2, code3)
    assert_invalid_invitation(vasil3, code3)

    # delete invitation from test-1020
    delete_data = {"community-id": community_id, "invitation-id": invitation_id1}
    ack = socketio_client2.emit("delete-invite", delete_data, callback=True)
    assert isinstance(ack, dict)
    assert ack.get("code", None) == 200
    assert ack.get("message", None) == "Success"

    assert len(socketio_client2.get_received()) == 0
    assert len(socketio_client3.get_received()) == 0
    assert len(socketio_client4.get_received()) == 0

    events = socketio_client1.get_received()
    assert len(events) == 1
    assert (event := events[0]).get("name", None) == "delete-invite"

    args = event.get("args", None)
    assert isinstance(args, list) and len(args) == 1
    assert isinstance((data := args[0]), dict)
    assert dict_equal(data, delete_data, *delete_data.keys())

    # testing deleted invite
    assert_invalid_invitation(vasil1, code1)  # , "User has already joined")
    assert_invalid_invitation(vasil2, code1)  # , "User has already joined")
    assert_invalid_invitation(vasil3, code1)


@mark.skip
@mark.order(1024)
def test_invitation_errors(multi_client, list_tester):
    community_data = {"name": "test", "description": "12345"}

    owner = multi_client("1@user.user")
    member = multi_client("2@user.user")
    outsider = multi_client("3@user.user")

    community_id = check_code(owner.post("/communities/", json=community_data)).get("id", None)  # TODO redo with sio
    assert community_id is not None
    invitation_data = {"role": "base", "limit": 2, "days": 10, "community-id": community_id}
    room_data = {"community-id": community_id}

    assert_successful_join = create_assert_successful_join(list_tester, community_id, community_data)

    # init sio & join rooms
    def manage_room(sio: SocketIOTestClient, join: bool = True):
        ack = sio.emit("open-invites" if join else "close-invites", room_data, callback=True)
        assert isinstance(ack, dict)
        assert ack.get("code", None) == 200
        assert ack.get("message", None) == "Success"

    socketio_client1 = SocketIOTestClient(owner)
    socketio_client2 = SocketIOTestClient(owner)
    socketio_client3 = SocketIOTestClient(member)
    socketio_client4 = SocketIOTestClient(outsider)
    manage_room(socketio_client1)
    manage_room(socketio_client2)

    # setup from test-1020
    invitation = socketio_client1.emit("new-invite", invitation_data, callback=True)["data"]
    assert isinstance(invitation, dict)
    assert "id" in invitation
    assert "code" in invitation

    assert len(socketio_client1.get_received()) == 0

    events = socketio_client2.get_received()
    assert len(events) == 1
    assert (event := events[0]).get("name", None) == "new-invite"

    args = event.get("args", None)
    assert isinstance(args, list) and len(args) == 1
    assert isinstance((data := args[0]), dict)

    keys = tuple(key for key in ("role", "limit") if key in invitation_data)
    assert dict_equal(data, invitation_data, *keys)
    days = invitation_data.get("days")
    if days is not None:
        deadline = data.get("deadline")
        assert deadline is not None
        dt: datetime = datetime.fromisoformat(deadline)
        assert dt.day == (datetime.utcnow() + timedelta(days=days)).day

    delete_data = {"community-id": community_id, "invitation-id": invitation["id"]}

    test_events = (
        ("open-invites", room_data),
        ("close-invites", room_data),
        ("new-invite", invitation_data),
        ("delete-invite", delete_data)
    )

    # fail check function
    def assert_fail_event(sio, code: int, message: str):
        for event_name, event_data in test_events:
            ack = sio.emit(event_name, event_data, callback=True)
            assert isinstance(ack, dict)
            assert ack.get("code", None) == code
            assert ack.get("message", None) == message

            assert len(socketio_client1.get_received()) == 0
            assert len(socketio_client2.get_received()) == 0
            assert len(socketio_client3.get_received()) == 0
            assert len(socketio_client4.get_received()) == 0

    # fail to enter the room by outsider
    assert_fail_event(socketio_client4, 403, "Permission Denied: Participant not found")

    # member joins community & fails connecting to room
    assert_successful_join(member, invitation["id"], invitation["code"], socketio_client3)
    assert_fail_event(socketio_client3, 403, "Permission Denied: Low role")
