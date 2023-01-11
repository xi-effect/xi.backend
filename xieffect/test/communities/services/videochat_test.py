from __future__ import annotations

from flask_fullstack import check_code, dict_equal
from pytest import mark, fixture

from common.testing import SocketIOTestClient
from ..base.invites_test import create_assert_successful_join
from ..base.meta_test import assert_create_community
from ..conftest import COMMUNITY_DATA


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


def get_messages_list(client, community_id: int) -> list[dict]:
    result = check_code(
        client.get(
            f"/communities/{community_id}/videochat/messages/",
            json={"counter": 20, "offset": 0},
        )
    ).get("results")
    assert isinstance(result, list)
    return result


@mark.order(1200)
def test_videochat_tools(
    client,
    multi_client,
    list_tester,
    socketio_client,
    test_community,
    create_participant_role,
    create_permission,
):
    role_id = create_participant_role(
        permission_type="MANAGE_INVITATIONS",
        community_id=test_community,
        client=socketio_client.flask_test_client,
    )

    create_permission(permission_type="MANAGE_MESSAGES", role_id=role_id)

    # Create base clients
    invite_data = {
        "community_id": test_community,
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
        create_data = dict(
            **community_id_json, state={"microphone": True, "camera": True}
        )
        participant = user.assert_emit_ack("new_participant", create_data)
        participant_id = participant.get("user_id")
        assert isinstance(participant_id, int)
        assert participant_id in participants_ids
    member_data = dict(create_data, user_id=participant_id)
    socketio_client.assert_only_received("new_participant", member_data)
    assert len(get_participant_list(client, test_community)) == len(participants_ids)

    # Check sending message
    content_data, message_count = {"content": "Test message"}, 0
    send_data = dict(**community_id_json, **content_data)
    owner_message = socketio_client.assert_emit_ack("send_message", send_data)
    message_count += 1
    user = check_code(client.get("/users/me/profile/"))
    assert user.get("username") is not None
    assert owner_message.get("sender").get("username") == user.get("username")
    sio_member.assert_only_received("send_message", content_data)

    users = [[socketio_client, sio_member], [sio_member, socketio_client]]
    for user in users:
        member_message = sio_member.assert_emit_ack("send_message", send_data)
        message_count += 1
        socketio_client.assert_only_received("send_message", content_data)
        user.append(member_message.get("id"))
    message_list = get_messages_list(client, test_community)
    assert len(message_list) == message_count
    assert dict_equal(owner_message, message_list[0], *owner_message.keys())

    # Check deleting message
    for emitter, receiver, message_id in users:
        data = dict(community_id_json, message_id=message_id)
        emitter.assert_emit_success("delete_message", data)
        message_count -= 1
        receiver.assert_only_received("delete_message", data)
    check_data = dict(community_id_json, message_id=owner_message.get("id"))
    sio_member.assert_emit_success(
        "delete_message", check_data, code=403, message="Permission Denied"
    )
    assert len(get_messages_list(client, test_community)) == message_count

    # Check changing participant states
    state_data = dict(community_id_json, target="microphone", state=False)
    sio_member.assert_emit_ack("change_state", state_data)
    member_data["state"][state_data.get("target")] = state_data.get("state")
    socketio_client.assert_only_received("change_state", dict(member_data))

    # Check sending actions
    data = dict(**community_id_json, participant_id=participant_id)
    action_data = dict(data, action_type="reaction", action=":av:")
    sio_member.assert_emit_success("send_action", action_data)
    socketio_client.assert_only_received("send_action", action_data)

    # Check successfully delete participant
    for code, message in ((200, "Success"), (404, "Participant not found")):
        sio_member.assert_emit_success(
            "delete_participant", data, code=code, message=message
        )
        participant_list = get_participant_list(client, test_community)
        assert len(participant_list) == len(participants_ids) - 1
    socketio_client.assert_only_received("delete_participant", data)
