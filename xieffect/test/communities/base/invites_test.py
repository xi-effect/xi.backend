from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta, datetime
from typing import Any

from flask_fullstack import (
    FlaskTestClient,
    SocketIOTestClient,
    dict_cut,
    assert_contains,
)
from pydantic import constr
from pytest import mark
from pytest_mock import MockerFixture

from communities.base import Community, Invitation
from test.communities.conftest import COMMUNITY_DATA, assert_create_community
from test.conftest import delete_by_id


class InvitesTester:
    def __init__(self, client: FlaskTestClient, room_data: dict, *clients):
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
        days = invite_data.get("days")
        if days is not None:
            deadline_regex: str = (
                datetime.utcnow().date() + timedelta(days=days)
            ).isoformat() + r"T\d{2}:\d{2}:\d{2}\.\d+"

        invite = self.sio1.assert_emit_ack(
            event_name="new_invite",
            data=invite_data,
            expected_data={
                "id": int,
                "code": str,
                "deadline": None if days is None else constr(regex=deadline_regex),
                **dict_cut(invite_data, "role", "limit", default=None),
            },
        )

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
def test_invites(client, socketio_client, test_community, get_role_ids):
    role_ids = get_role_ids(client, test_community)
    invite_data = {
        "community_id": test_community,
        "limit": 2,
        "days": 10,
        "role_ids": role_ids,
    }
    index_url = f"/communities/{test_community}/invitations/"

    # check that the invite list is empty
    assert len(list(client.paginate(index_url))) == 0

    # init sio & join rooms
    invite_tester = InvitesTester(client, {"community_id": test_community})

    # create a new invite
    invite = invite_tester.assert_create_invite(invite_data)
    data = list(client.paginate(index_url))
    assert len(data) == 1
    assert_contains(data[0], invite)

    # delete invite & check again
    invite_tester.assert_delete_invite(
        {
            "community_id": test_community,
            "invitation_id": invite["id"],
        }
    )
    assert len(list(client.paginate(index_url))) == 0

    # check constraints
    community_data = {"name": "invite_test"}
    community_id = assert_create_community(socketio_client, community_data)
    index_url = f"/communities/{community_id}/invitations/"
    invite_tester = InvitesTester(client, {"community_id": community_id})
    invite = invite_tester.assert_create_invite(
        dict(invite_data, community_id=community_id)
    )
    assert len(list(client.paginate(index_url))) == 1

    delete_by_id(community_id, Community)
    assert Invitation.find_by_id(invite.get("id")) is None


def find_invite(
    client: FlaskTestClient,
    community_id: int,
    invite_id: int,
) -> dict | None:
    index_url = f"/communities/{community_id}/invitations/"

    for data in client.paginate(index_url):
        if data["id"] == invite_id:
            return data
    return None


def assert_successful_get(client: FlaskTestClient, code: str, joined: bool):
    client.get(
        f"/communities/join/{code}/",
        expected_json={
            "joined": joined,
            "authorized": True,
            "community": COMMUNITY_DATA,
        },
    )


def create_assert_successful_join(member: FlaskTestClient, community_id: int):
    def assert_successful_join(
        client: FlaskTestClient,
        invite_id: int,
        code: str,
        *sio_clients: SocketIOTestClient,
    ):
        invite = find_invite(member, community_id, invite_id)
        assert invite is not None, "Invitation not found inside assert_successful_join"
        limit_before = invite.get("limit")

        assert_successful_get(client, code, joined=False)
        assert client.post(f"/communities/join/{code}/", expected_json=COMMUNITY_DATA)

        if limit_before is not None:
            invite = find_invite(member, community_id, invite_id)
            if invite is None:
                assert limit_before == 1
            else:
                assert invite["limit"] == limit_before - 1

        for sio in sio_clients:
            sio.assert_only_received("new_community", COMMUNITY_DATA)

    return assert_successful_join


@mark.order(1022)
def test_invite_joins(
    base_client: FlaskTestClient,
    client: FlaskTestClient,
    multi_client: Callable[[str], FlaskTestClient],
    test_community: int,
    create_assert_successful_join,
    assert_successful_get,
    get_role_ids,
):
    role_ids = get_role_ids(client, test_community)

    # functions
    def create_invite(invite_data, check_auth: bool = True):
        invite_data["community_id"] = test_community
        invite = invite_tester.assert_create_invite(invite_data)

        if check_auth:
            join_url = f"/communities/join/{invite['code']}/"
            base_client.get(
                join_url,
                expected_json={
                    "joined": False,
                    "authorized": False,
                    "community": COMMUNITY_DATA,
                },
            )

            base_client.post(join_url, expected_status=401)

        return invite["id"], invite["code"]

    assert_successful_join = create_assert_successful_join(test_community)

    def assert_invalid_invite(client: FlaskTestClient, code: str):
        client.get(
            f"/communities/join/{code}/",
            expected_status=400,
            expected_json={"a": "Invalid invitation"},
        )
        client.post(
            f"/communities/join/{code}/",
            expected_status=400,
            expected_json={"a": "Invalid invitation"},
        )

    def assert_already_joined(client: FlaskTestClient, code: str):
        assert_successful_get(client, code, joined=True)
        client.post(
            f"/communities/join/{code}/",
            expected_status=400,
            expected_json={"a": "User has already joined"},
        )

    vasil1 = multi_client("1@user.user")
    vasil2 = multi_client("2@user.user")
    vasil3 = multi_client("3@user.user")

    # init sio & join rooms
    invite_tester = InvitesTester(client, {"community_id": test_community})
    sio5 = SocketIOTestClient(vasil1)
    sio6 = SocketIOTestClient(vasil1)

    # testing joining & errors
    invite_id1, code1 = create_invite({})
    assert_invalid_invite(vasil1, "hey")
    assert_already_joined(client, code1)
    assert_successful_join(vasil1, invite_id1, code1, sio5, sio6)
    assert_already_joined(vasil1, code1)

    # testing counter limit
    invite_id2, code2 = create_invite({"limit": 1})
    assert_already_joined(vasil1, code2)
    assert_successful_join(vasil2, invite_id2, code2)
    assert_invalid_invite(vasil2, code2)  # may be converted to already joined
    assert_invalid_invite(vasil3, code2)

    # testing time limit
    _, code3 = create_invite({"days": 0}, check_auth=False)
    assert_already_joined(vasil1, code3)
    assert_already_joined(vasil2, code3)
    assert_invalid_invite(vasil3, code3)

    # testing role_participant
    invite_id3, code4 = create_invite({"role_ids": role_ids})
    assert_already_joined(vasil1, code4)
    assert_successful_join(vasil3, invite_id3, code4)

    # delete invite from test-1020
    invite_tester.assert_delete_invite(
        {
            "community_id": test_community,
            "invitation_id": invite_id1,
        }
    )

    # testing deleted invite
    assert_invalid_invite(vasil1, code1)  # may be converted to already joined
    assert_invalid_invite(vasil2, code1)  # may be converted to already joined
    assert_invalid_invite(vasil3, code1)


@mark.order(1024)
def test_invites_errors(
    client: FlaskTestClient,
    multi_client: Callable[[str], FlaskTestClient],
    test_community: int,
    create_assert_successful_join,
):
    member = multi_client("1@user.user")
    outsider = multi_client("2@user.user")

    invite_data = {
        "permission": "manage_invitations",
        "limit": 2,
        "days": 10,
        "community_id": test_community,
        "role_ids": [],
    }
    room_data = {"community_id": test_community}

    assert_successful_join = create_assert_successful_join(test_community)

    # init sio, join rooms & set up the invite
    sio_member = SocketIOTestClient(member)
    sio_outsider = SocketIOTestClient(outsider)
    invite_tester = InvitesTester(
        client, {"community_id": test_community}, sio_member, sio_outsider
    )
    invite = invite_tester.assert_create_invite(invite_data)

    delete_data = {"community_id": test_community, "invitation_id": invite["id"]}
    test_events = (
        ("open_invites", room_data),
        ("close_invites", room_data),
        ("new_invite", invite_data),
        ("delete_invite", delete_data),
    )

    # fail check function
    def assert_fail_event(sio: SocketIOTestClient, code: int, message: str):
        for event_name, event_data in test_events:
            sio.assert_emit_ack(
                event_name=event_name,
                data=event_data,
                expected_code=code,
                expected_message=message,
            )
            invite_tester.assert_nop()

    # fail to enter the room by outsider
    assert_fail_event(sio_outsider, 403, "Permission Denied: Participant not found")

    # member joins community & fails connecting to room
    assert_successful_join(member, invite["id"], invite["code"], sio_member)
    assert_fail_event(sio_member, 403, "Permission Denied: Not sufficient permissions")


def test_limit_invitations(
    client: FlaskTestClient,
    multi_client: Callable[[str], FlaskTestClient],
    test_community: int,
    mocker: MockerFixture,
):
    mocker.patch.object(target=Invitation, attribute="max_count", new=1)

    user1 = multi_client("1@user.user")
    invite_data: dict[str, Any] = {
        "permission": "manage_invitations",
        "limit": 3,
        "days": 10,
        "community_id": test_community,
        "role_ids": [],
    }

    sio_user1 = SocketIOTestClient(user1)

    invite_tester = InvitesTester(client, {"community_id": test_community}, sio_user1)
    invite_tester.assert_create_invite(invite_data)

    invite_tester.sio1.assert_emit_ack(
        event_name="new_invite",
        data=invite_data,
        expected_code=400,
        expected_message="Quantity exceeded",
    )
