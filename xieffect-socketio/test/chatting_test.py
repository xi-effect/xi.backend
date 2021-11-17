from pytest import mark

from .conftest import MultiClient
from .library2 import Event


@mark.order(600)
def test_chat_owning(socket_tr_io_client: MultiClient):  # assumes test's id == 1
    anatol, evgen, vasil = socket_tr_io_client.get_tr_io()

    # Creating a new chat:
    chat_name1, chat_name2 = "test", "production"
    anatol.emit("add-chat", {"name": chat_name1}, wait_stop=True)

    assert len(events := anatol.get_received()) == 1
    assert (event := Event.from_sio(events[0])).name == "add-chat" and event.data.get("name", None) == chat_name1
    assert (chat_id := event.data.get("chat-id", None)) is not None

    # Editing chat metadata:
    event_data = {"chat-id": chat_id, "name": chat_name2}
    anatol.emit("edit-chat", event_data, wait_stop=True)
    assert len(events := anatol.get_received()) == 1
    assert (event := Event.from_sio(events[0])).name == "edit-chat" and event.data == event_data

    # Deleting the chat:
    event_data = {"chat-id": chat_id}
    anatol.emit("delete-chat", event_data, wait_stop=True)
    assert len(events := anatol.get_received()) == 1
    assert (event := Event.from_sio(events[0])).name == "delete-chat" and event.data == event_data


"""
def get_roles_to_user(multi_client: Callable[[str], FlaskClient], chat):
    roles = ["muted", "basic", "moder", "admin"]
    not_found_roles = roles.copy()
    role_to_email = {not_found_roles.pop(not_found_roles.index(role)): email
                     for email, role in chat["participants"]
                     if role in not_found_roles}
    assert len(not_found_roles) == 0
    return [(role, (email := role_to_email[role]), check_status_code(multi_client(email).get("/settings/main/"))["id"])
            for role in roles]


@mark.order(610)
def test_chat_roles(list_tester: Callable[[str, dict, int], Iterator[dict]],
                    multi_client: Callable[[str], FlaskClient]):  # relies on chat#4
    with open("../files/test/chat-bundle.json", encoding="utf-8") as f:
        chat = load(f)[-1]
    chat_name = chat["name"]
    chat_uc = len(chat["participants"])
    chat_id = [c["id"] for c in list_tester("/chats/index/", {}, 50) if c["name"] == chat_name][0]
    role_to_user = get_roles_to_user(multi_client, chat)

    for i in range(len(role_to_user)):
        role, email, user_id = role_to_user[i]
        client = multi_client(email)
        code: int = 200 if role == "admin" else 403

        check_status_code(client.delete(f"/chats/{chat_id}/manage/"), 403)
        check_status_code(client.put(f"/chats/{chat_id}/manage/", json={"name": "new_name"}), code)
        if role == "admin":
            assert check_status_code(client.get(f"/chats/{chat_id}/"))["name"] == "new_name"
        check_status_code(client.put(f"/chats/{chat_id}/manage/", json={"name": chat_name}), code)

        for target in list_tester(f"/chats/{chat_id}/users/", {}, 50):
            target_id = target["id"]
            if target["role"] == "owner":
                check_status_code(client.delete(f"/chats/{chat_id}/users/{target_id}/"), 403)
            elif target_id != user_id:
                check_status_code(client.delete(f"/chats/{chat_id}/users/{target_id}/"), code)
                assert role != "admin" or check_status_code(client.get(f"/chats/{chat_id}/"))["users"] == chat_uc - 1
                check_status_code(client.post(f"/chats/{chat_id}/users/{target_id}/"), code)
                assert role != "admin" or check_status_code(client.get(f"/chats/{chat_id}/"))["users"] == chat_uc


def test_user_management(socket_tr_io_client: MultiClient,
                         list_tester: Callable[[Session, str, dict, int], Iterator[dict]]):  # relies on chat#3
    anatol, evgen, vasil = get_tr_io(socket_tr_io_client)

    anatol_id = user["id"]  # find anatol as admin!

    # Generating users to invite:
    invited: dict[int] = {anatol_id: "owner", 3: "muted", 4: "basic", 5: "moder", 6: "admin"}  # redo with /users/
    bulk = [user_id for user_id in list(invited) if user_id != anatol_id]

    # Inviting users:
    assert check_status_code(main_server.post(f"/chats/{chat_id}/users/add-all/", json={"ids": bulk[:-1]})) == {"a": True}
    assert check_status_code(main_server.post(f"/chats/{chat_id}/users/{bulk[-1]}/"))

    # Inviting Evgen to chat:
    event_data = {"chat-id": chat_id, "role": "basic", "user-id": 1}
    anatol.emit("invite-user", event_data, wait_stop=True)
    assert anatol.new_event_count() == 1
    assert (event := anatol.next_new_event()).name == "invite-user" and event.data == event_data

    # Changing users' roles:
    assert all(check_status_code(main_server.put(f"/chats/{chat_id}/users/{user_id}/", json={"role": role}))["a"]
               for user_id, role in invited.items()
               if user_id != test_user_id)
    # MB add a check for inviting already invited users

    # Check the updated user-list:
    for user in list_tester(f"/chats/{chat_id}/users/", {}, 50):
        assert list(user.keys()) == ["id", "role", "username"]
        assert user["id"] in invited.keys(), "Invited user not found in a chat"
        assert user["role"] == invited[user["id"]]

    # Kick one user & check the updated user-list:
    check_status_code(main_server.delete(f"/chats/{chat_id}/users/{(removed_user_id := list(invited)[2])}/"))
    assert all(user["id"] != removed_user_id for user in list_tester(f"/chats/{chat_id}/users/", {}, 50))
"""
