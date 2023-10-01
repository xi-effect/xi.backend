from __future__ import annotations

from collections.abc import Callable

from flask_fullstack import SocketIOTestClient
from pydantic_marshals.contains import assert_contains
from pytest import mark

from communities.base.meta_db import Community
from communities.services.videochat_db import ChatParticipant, ChatMessage
from test.conftest import delete_by_id, FlaskTestClient
from users.users_db import User


def get_participant_list(client: FlaskTestClient, community_id: int):
    return client.get(
        f"/communities/{community_id}/videochat/participants/", expected_json=list
    )


def get_messages_list(client: FlaskTestClient, community_id: int) -> list[dict]:
    return list(client.paginate(f"/communities/{community_id}/videochat/messages/"))


@mark.skip()
@mark.order(1200)
def test_videochat_tools(
    client: FlaskTestClient,
    multi_client: Callable[[str], FlaskTestClient],
    socketio_client: SocketIOTestClient,
    test_community: int,
    create_assert_successful_join,
):
    # Create base clients
    invite_data = {
        "community_id": test_community,
        "limit": 2,
        "days": 10,
    }
    invite = socketio_client.assert_emit_ack(
        event_name="new_invite",
        data=invite_data,
        expected_data={"id": int, "code": str},
    )
    member = multi_client("1@user.user")
    sio_member = SocketIOTestClient(member)
    assert_successful_join = create_assert_successful_join(test_community)
    assert_successful_join(member, invite["id"], invite["code"], sio_member)

    community_id_json = {"community_id": test_community}
    participants_ids = []

    for user in (client, member):
        participants_ids.append(
            user.get("/users/me/profile/", expected_json={"id": int})["id"]
        )

    # Check successfully create new participants
    for user in (socketio_client, sio_member):
        create_data = dict(
            **community_id_json, state={"microphone": True, "camera": True}
        )
        participant_id = user.assert_emit_ack(
            event_name="new_participant",
            data=create_data,
            expected_data={
                "user_id": int,
            },
        )["user_id"]
        assert participant_id in participants_ids
    member_data: dict[..., ...] = dict(create_data, user_id=participant_id)
    socketio_client.assert_only_received("new_participant", member_data)
    assert len(get_participant_list(client, test_community)) == len(participants_ids)

    # Check sending message
    content_data, message_count = {"content": "Test message"}, 0
    send_data = dict(**community_id_json, **content_data)
    owner_message = socketio_client.assert_emit_ack(
        event_name="send_message",
        data=send_data,
        expected_data={"sender": {"username": str}},
    )
    message_count += 1

    client.get(
        "/users/me/profile/",
        expected_json={
            "username": owner_message.get("sender").get("username"),
        },
    )
    sio_member.assert_only_received("send_message", content_data)

    users = [[socketio_client, sio_member], [sio_member, socketio_client]]
    for user in users:
        user.append(
            sio_member.assert_emit_ack(
                event_name="send_message", data=send_data, expected_data={"id": int}
            )["id"]
        )
        message_count += 1
        socketio_client.assert_only_received("send_message", content_data)
    message_list = get_messages_list(client, test_community)
    assert len(message_list) == message_count
    assert_contains(message_list[0], owner_message)

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
    sio_member.assert_emit_ack(
        event_name="change_state",
        data=state_data,
        # TODO expected_data={}
    )
    member_data["state"][state_data["target"]] = state_data["state"]
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


@mark.skip()
def test_videochat_constraints(
    table: type[User | Community],
    base_user_id: int,
    community_id: int,
):
    state = {"microphone": True, "camera": True}
    participant_id = ChatParticipant.create(base_user_id, community_id, state).user_id
    message_id = ChatMessage.create(
        User.find_by_id(base_user_id), community_id, "test"
    ).id
    assert isinstance(participant_id, int)
    assert isinstance(message_id, int)

    delete_by_id(base_user_id if (table == User) else community_id, table)
    message = ChatMessage.find_by_id(message_id)
    if table == User:
        assert message is not None
        assert message.sender is None
    else:
        assert message is None
    assert ChatParticipant.find_by_ids(participant_id, community_id) is None
