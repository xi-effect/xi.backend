from __future__ import annotations

from flask_fullstack import check_code
from pytest import mark, fixture

from common.testing import SocketIOTestClient
from ..base.invites_test import create_assert_successful_join
from ..base.meta_test import assert_create_community

COMMUNITY_DATA = {"name": "test"}


@fixture
def test_community(socketio_client: SocketIOTestClient) -> int:
    # TODO place more globally (duplicate from invites_test)
    # TODO use yield & delete the community after
    return assert_create_community(socketio_client, COMMUNITY_DATA)


def get_participant_list(client, community_id: int):
    result = check_code(
        client.get(f"/communities/{community_id}/videochat/participants/")
    )
    assert isinstance(result, list)
    return result


@mark.order(1200)
def test_videochat_tools(
    client,
    multi_client,
    list_tester,
    socketio_client,
    test_community,
):
    # Create base clients
    invite_data = {
        "community_id": test_community,
        "role": "base",
        "limit": 2,
        "days": 10,
    }
    invite = socketio_client.assert_emit_ack("new_invite", invite_data)
    member = multi_client("1@user.user")
    sio_member = SocketIOTestClient(member)
    assert_successful_join = create_assert_successful_join(
        list_tester,
        test_community,
    )
    assert_successful_join(member, invite["id"], invite["code"], sio_member)

    community_id_json = {"community_id": test_community}
    participants_ids = []

    for user in (client, member):
        participants_ids.append(check_code(user.get("/users/me/profile/")).get("id"))

    # Check successfully create new participants
    for user in (socketio_client, sio_member):
        participant = user.assert_emit_ack("new_participant", community_id_json)
        participant_id = participant.get("user_id")
        assert isinstance(participant_id, int)
        assert participant_id in participants_ids
    member_data = dict(
        community_id_json, user_id=participant_id, microphone=True, camera=True
    )
    socketio_client.assert_only_received("new_participant", member_data)
    assert len(get_participant_list(client, test_community)) == len(participants_ids)

    # Check sending message
    text_data = {"text": "Test message"}
    message = socketio_client.assert_emit_ack(
        "send_message", dict(**community_id_json, **text_data)
    )
    user = check_code(client.get("/users/me/profile/"))
    assert user.get("username") is not None
    assert message.get("creator").get("username") == user.get("username")
    sio_member.assert_only_received("send_message", text_data)

    # Check changing device status
    change_data = (
        ("microphone", False, 200, None), ("keyboard", True, 404, "Device not found")
    )
    for target, state, code, message in change_data:
        device_data = dict(community_id_json, target=target, state=state)
        sio_member.assert_emit_ack(
            "device_status", device_data, code=code, message=message
        )
        if code == 200:
            member_data[device_data.get('target')] = device_data.get('state')
            socketio_client.assert_only_received("device_status", dict(member_data))

    # Check successfully delete participant
    for code, message in ((200, "Success"), (404, "Participant doesn't exist")):
        sio_member.assert_emit_success(
            "delete_participant", community_id_json, code=code, message=message
        )
        participant_list = get_participant_list(client, test_community)
        assert len(participant_list) == len(participants_ids) - 1
    socketio_client.assert_only_received("delete_participant", community_id_json)
