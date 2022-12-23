from common.testing import SocketIOTestClient
from common import db
from communities.base.roles_db import ParticipantRole, Role, PermissionType, RolePermission
from communities.base.meta_db import Participant
from .services.videochat_test import get_messages_list
from sqlalchemy.orm import aliased


def test_utils(
        client,
        socketio_client,
        test_community

):
    permissions: list[str] = sorted(PermissionType.get_all_field_names())
    community_id_json = {"community_id": test_community}
    socketio_client2 = SocketIOTestClient(client)

    # content_data = {"content": "Test message"}
    # send_data = dict(**community_id_json, **content_data)
    #
    # # Use user
    # result = socketio_client.assert_emit_ack("send_message", send_data)
    # print(result, "first result")

    role_data = {
        "permissions": permissions,
        "name": "test_role",
        "color": "FFFF00",
    }

    create_data = dict(**role_data, **community_id_json)

    # Check successfully open roles-room
    for user in (socketio_client, socketio_client2):
        user.assert_emit_success("open_roles", community_id_json)

    for _ in range(3):
        result = socketio_client.assert_emit_ack("new_role", create_data)
        socketio_client2.assert_only_received("new_role", result)
        stmt = db.insert(ParticipantRole).values(role_id=result['id'], participant_id=1)
        db.session.execute(stmt)

    # x = db.select(RolePermission.permission_type)\
    #     .join(ParticipantRole, ParticipantRole.role_id == Role.id)\
    #     .join(Role, Role.id == RolePermission.role_id)\
    #     .where(ParticipantRole.participant_id == 1)\
    #
    #
    # print(db.session.get_all(x)[0])

    # for i in x:
    #     print()
    # print(get_messages_list(client, test_community), "list message")
    #
    # # Use Participant
    # data = dict(community_id_json, message_id=result['id'])
    # socketio_client.assert_emit_ack("delete_message", data)
    #
    # print(get_messages_list(client, test_community), "list message second")
