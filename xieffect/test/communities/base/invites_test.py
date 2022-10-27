from __future__ import annotations

from collections.abc import Iterator, Callable
from datetime import datetime, timedelta

from flask.testing import FlaskClient
from flask_fullstack import check_code, dict_equal
from pytest import mark, fixture

from common.testing import SocketIOTestClient
from .meta_test import assert_create_community

INVITATIONS_PER_REQUEST = 20
COMMUNITY_DATA = {"name": "test"}


@fixture
def test_community(socketio_client: SocketIOTestClient) -> int:
    # TODO place more globally
    # TODO use yield & delete the community after
    return assert_create_community(socketio_client, COMMUNITY_DATA)


class InvitesTester:
    def __init__(self, client: FlaskClient, room_data: dict, *clients):
        self.sio1 = SocketIOTestClient(client)
        self.sio2 = SocketIOTestClient(client)
        self.sio3 = SocketIOTestClient(client)
        self.sio4 = SocketIOTestClient(client)
        self.clients = [self.sio1, self.sio2, self.sio3, self.sio4] + list(clients)

        self.sio1.assert_emit_success("open_invites", room_data)
        self.sio2.assert_emit_success("open_invites", room_data)
        self.sio3.assert_emit_success("open_invites", room_data)
        self.sio3.assert_emit_success("close_invites", room_data)
        self.assert_nop()

    def assert_create_invite(self, invite_data: dict) -> dict:
        invite = self.sio1.assert_emit_ack("new_invite", invite_data)
        assert isinstance(invite, dict)
        assert "id" in invite
        assert "code" in invite
        assert dict_equal(invite, invite_data, "role", "limit")

        days = invite_data.get("days")
        if days is not None:
            deadline = invite.get("deadline")
            assert deadline is not None
            dt: datetime = datetime.fromisoformat(deadline)
            assert dt.day == (datetime.utcnow() + timedelta(days=days)).day

        self.sio2.assert_only_received("new_invite", invite)
        self.assert_nop()

        return invite

    def assert_delete_invite(self, delete_data: dict) -> None:
        self.sio1.assert_emit_success("delete_invite", delete_data)
        self.sio2.assert_only_received("delete_invite", delete_data)
        self.assert_nop()

    def assert_nop(self):
        SocketIOTestClient.assert_bulk_nop(*self.clients)


@mark.order(1020)
def test_invites(client, list_tester, test_community):
    invite_data = {
        "community_id": test_community,
        "role": "base",
        "limit": 2,
        "days": 10,
    }
    index_url = f"/communities/{test_community}/invitations/index/"

    # check that the invite list is empty
    assert len(list(list_tester(index_url, {}, INVITATIONS_PER_REQUEST))) == 0

    # init sio & join rooms
    invite_tester = InvitesTester(client, {"community_id": test_community})

    # create a new invite
    invite = invite_tester.assert_create_invite(invite_data)
    data = list(list_tester(index_url, {}, INVITATIONS_PER_REQUEST))
    assert len(data) == 1
    assert dict_equal(data[0], invite, *invite.keys())

    # delete invite & check again
    invite_tester.assert_delete_invite({
        "community_id": test_community,
        "invitation_id": invite["id"],
    })
    assert len(list(list_tester(index_url, {}, INVITATIONS_PER_REQUEST))) == 0


def find_invite(list_tester, community_id: int, invite_id: int) -> dict | None:
    index_url = f"/communities/{community_id}/invitations/index/"

    for data in list_tester(index_url, {}, INVITATIONS_PER_REQUEST):
        if data["id"] == invite_id:
            return data
    return None


def assert_successful_get(client: FlaskClient, code, joined: bool):
    data = check_code(client.get(f"/communities/join/{code}/"))
    assert data.get("joined") is joined
    assert data.get("authorized") is True

    community = data.get("community")
    assert community is not None
    assert dict_equal(community, COMMUNITY_DATA, *COMMUNITY_DATA.keys())


def create_assert_successful_join(list_tester, community_id):
    def assert_successful_join(client: FlaskClient, invite_id: int, code: str, *sio_clients: SocketIOTestClient):
        invite = find_invite(list_tester, community_id, invite_id)
        assert invite is not None, "Invitation not found inside assert_successful_join"
        limit_before = invite.get("limit")

        assert_successful_get(client, code, joined=False)
        assert dict_equal(check_code(client.post(f"/communities/join/{code}/")), COMMUNITY_DATA, *COMMUNITY_DATA.keys())

        if limit_before is not None:
            invite = find_invite(list_tester, community_id, invite_id)
            if invite is None:
                assert limit_before == 1
            else:
                assert invite["limit"] == limit_before - 1

        for sio in sio_clients:
            sio.assert_only_received("new_community", COMMUNITY_DATA)

    return assert_successful_join


@mark.order(1022)
def test_invite_joins(
    base_client: FlaskClient,
    client: FlaskClient,
    multi_client: Callable[[str], FlaskClient],
    list_tester: Callable[[str, dict, int], Iterator[dict]],
    test_community: int,
):
    # functions
    def create_invite(invite_data, check_auth: bool = True):
        invite_data["community_id"] = test_community
        invite = invite_tester.assert_create_invite(invite_data)

        if check_auth:
            join_url = f"/communities/join/{invite['code']}/"
            data = check_code(base_client.get(join_url))
            assert data.get("joined") is False
            assert data.get("authorized") is False

            community = data.get("community")
            assert community is not None
            assert dict_equal(community, COMMUNITY_DATA, *COMMUNITY_DATA.keys())

            check_code(base_client.post(join_url), 401)

        return invite["id"], invite["code"]

    assert_successful_join = create_assert_successful_join(list_tester, test_community)

    def assert_invalid_invite(client: FlaskClient, code: str):
        assert check_code(client.get(f"/communities/join/{code}/"), 400)["a"] == "Invalid invitation"
        assert check_code(client.post(f"/communities/join/{code}/"), 400)["a"] == "Invalid invitation"

    def assert_already_joined(client: FlaskClient, code: str):
        assert_successful_get(client, code, joined=True)
        assert check_code(client.post(f"/communities/join/{code}/"), 400)["a"] == "User has already joined"

    vasil1 = multi_client("1@user.user")
    vasil2 = multi_client("2@user.user")
    vasil3 = multi_client("3@user.user")

    # init sio & join rooms
    invite_tester = InvitesTester(client, {"community_id": test_community})
    sio5 = SocketIOTestClient(vasil1)
    sio6 = SocketIOTestClient(vasil1)

    # testing joining & errors
    invite_id1, code1 = create_invite({"role": "base"})
    assert_invalid_invite(vasil1, "hey")
    assert_already_joined(client, code1)
    assert_successful_join(vasil1, invite_id1, code1, sio5, sio6)
    assert_already_joined(vasil1, code1)

    # testing counter limit
    invite_id2, code2 = create_invite({"role": "base", "limit": 1})
    assert_already_joined(vasil1, code2)
    assert_successful_join(vasil2, invite_id2, code2)
    assert_invalid_invite(vasil2, code2)  # may be converted to already joined
    assert_invalid_invite(vasil3, code2)

    # testing time limit
    _, code3 = create_invite({"role": "base", "days": 0}, check_auth=False)
    assert_already_joined(vasil1, code3)
    assert_already_joined(vasil2, code3)
    assert_invalid_invite(vasil3, code3)

    # delete invite from test-1020
    invite_tester.assert_delete_invite({
        "community_id": test_community,
        "invitation_id": invite_id1,
    })

    # testing deleted invite
    assert_invalid_invite(vasil1, code1)  # may be converted to already joined
    assert_invalid_invite(vasil2, code1)  # may be converted to already joined
    assert_invalid_invite(vasil3, code1)


@mark.order(1024)
def test_invites_errors(client, multi_client, list_tester, test_community):
    member = multi_client("1@user.user")
    outsider = multi_client("2@user.user")

    invite_data = {"role": "base", "limit": 2, "days": 10, "community_id": test_community}
    room_data = {"community_id": test_community}

    assert_successful_join = create_assert_successful_join(list_tester, test_community)

    # init sio, join rooms & set up the invite
    sio_member = SocketIOTestClient(member)
    sio_outsider = SocketIOTestClient(outsider)
    invite_tester = InvitesTester(client, {"community_id": test_community}, sio_member, sio_outsider)
    invite = invite_tester.assert_create_invite(invite_data)

    delete_data = {"community_id": test_community, "invitation_id": invite["id"]}
    test_events = (
        ("open_invites", room_data),
        ("close_invites", room_data),
        ("new_invite", invite_data),
        ("delete_invite", delete_data)
    )

    # fail check function
    def assert_fail_event(sio, code: int, message: str):
        for event_name, event_data in test_events:
            sio.assert_emit_ack(event_name, event_data, code=code, message=message)
            invite_tester.assert_nop()

    # fail to enter the room by outsider
    assert_fail_event(sio_outsider, 403, "Permission Denied: Participant not found")

    # member joins community & fails connecting to room
    assert_successful_join(member, invite["id"], invite["code"], sio_member)
    assert_fail_event(sio_member, 403, "Permission Denied: Low role")
