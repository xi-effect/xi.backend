from json import load
from typing import Callable, Iterator

from flask.testing import FlaskClient
from pytest import mark

from __lib__.flask_fullstack import check_code, dict_equal


@mark.skip
@mark.order(600)
def test_chat_owning(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    # Creating a new chat:
    chat_name1, chat_name2 = "test", "production"
    chat_id = check_code(client.post("/chat-temp/", json={"name": chat_name1})).get("id", None)
    assert chat_id is not None

    # Checking initial chat metadata & message-history:
    data = {"name": chat_name1, "role": "owner", "users": 1, "unread": 0}
    assert check_code(client.get(f"/chats/{chat_id}/")) == data
    assert any(chat["id"] == chat_id and chat["name"] == chat_name1 for chat in list_tester("/chats/index/", {}, 50))
    assert len(list(list_tester(f"/chats/{chat_id}/message-history/", {}, 50))) == 0

    # Checking the initial user-list:
    user_list = list(list_tester(f"/chats/{chat_id}/users/", {}, 50))
    assert len(user_list) == 1
    assert (user := user_list[0])["role"] == "owner"
    test_user_id = user["id"]

    # Generating users to invite:
    invited: dict[int] = {test_user_id: "owner", 3: "muted", 4: "basic", 5: "moder", 6: "admin"}  # redo with /users/
    bulk = [user_id for user_id in list(invited) if user_id != test_user_id]
    an_id = bulk[-1]

    # Inviting users:
    assert all(check_code(client.post(f"/chat-temp/{chat_id}/users/add-all/", json={"ids": bulk[:-1]})))
    assert check_code(client.post(f"/chat-temp/{chat_id}/users/{an_id}/", json={"role": invited[an_id]}))["a"]

    # Fail to invite the same users:
    assert not any(check_code(client.post(f"/chat-temp/{chat_id}/users/add-all/", json={"ids": bulk[:-1]})))
    assert not check_code(client.post(f"/chat-temp/{chat_id}/users/{an_id}/", json={"role": invited[an_id]}))["a"]

    # Changing users' roles:
    assert all(client.put(f"/chat-temp/{chat_id}/users/{user_id}/", json={"role": role}).status_code == 200
               for user_id, role in invited.items()
               if user_id != test_user_id and user_id != an_id)
    # MB add a check for inviting already invited users

    # Editing chat metadata:
    assert check_code(client.put(f"/chat-temp/{chat_id}/manage/", json={"name": chat_name2})) == {"a": True}
    # Checking chat metadata:
    chat_data = {"name": chat_name2, "role": "owner", "users": len(invited), "unread": 0}
    assert check_code(client.get(f"/chats/{chat_id}/")) == chat_data
    assert any(chat["id"] == chat_id and chat["name"] == chat_name2 for chat in list_tester("/chats/index/", {}, 50))

    # Check the updated user-list:
    for user in list_tester(f"/chats/{chat_id}/users/", {}, 50):
        assert list(user.keys()) == ["id", "role", "user-avatar", "username"]
        assert user["id"] in invited.keys(), "Invited user not found in a chat"
        assert user["role"] == invited[user["id"]]

    # Kick one user:
    check_code(client.delete(f"/chat-temp/{chat_id}/users/{(removed_user_id := list(invited)[2])}/"))
    # Check the updated user-list
    assert all(user["id"] != removed_user_id for user in list_tester(f"/chats/{chat_id}/users/", {}, 50))

    # Delete the chat:
    assert check_code(client.delete(f"/chat-temp/{chat_id}/manage/")) == {"a": True}
    # Check chat's absence:
    assert check_code(client.get(f"/chats/{chat_id}/"), 404)
    assert all(chat["id"] != chat_id for chat in list_tester("/chats/index/", {}, 50))


def get_roles_to_user(multi_client: Callable[[str], FlaskClient], chat):
    roles = ["muted", "basic", "moder", "admin"]
    not_found_roles = roles.copy()
    role_to_email = {not_found_roles.pop(not_found_roles.index(role)): email
                     for email, role in chat["participants"]
                     if role in not_found_roles}
    assert len(not_found_roles) == 0
    return [(role, (email := role_to_email[role]), check_code(multi_client(email).get("/settings/main/"))["id"])
            for role in roles]


@mark.skip
@mark.order(620)
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
        code = 200 if role == "admin" else 403

        check_code(client.delete(f"/chat-temp/{chat_id}/manage/"), 403)
        check_code(client.put(f"/chat-temp/{chat_id}/manage/", json={"name": "new_name"}), code)
        if role == "admin":
            assert check_code(client.get(f"/chats/{chat_id}/"))["name"] == "new_name"
        check_code(client.put(f"/chat-temp/{chat_id}/manage/", json={"name": chat_name}), code)
        if role == "admin":
            assert check_code(client.get(f"/chats/{chat_id}/"))["name"] == chat_name

        for target in list_tester(f"/chats/{chat_id}/users/", {}, 50):
            target_id = target["id"]
            code = 200 if role == "admin" and target["role"] not in ("owner", "admin") else 403
            if target_id != user_id:
                check_code(client.delete(f"/chat-temp/{chat_id}/users/{target_id}/"), code)
                assert code == 403 or (check_code(client.get(f"/chats/{chat_id}/"))["users"] == chat_uc - 1)

                check_code(client.post(f"/chat-temp/{chat_id}/users/{target_id}/",
                                       json={"role": target["role"]}), code)
                assert code == 403 or check_code(client.get(f"/chats/{chat_id}/"))["users"] == chat_uc


@mark.skip
@mark.order(625)
def test_ownership_transfer(multi_client: Callable[[str], FlaskClient]):
    anatol, evgen, vasil = multi_client("1@user.user"), multi_client("2@user.user"), multi_client("3@user.user")
    anatol_id, evgen_id, vasil_id = 4, 5, 6  # user ids are assumed

    # Creating the chat
    chat_id = check_code(anatol.post("/chat-temp/", json={"name": "test"})).get("id", None)
    assert chat_id is not None

    # Inviting evgen & vasil
    assert check_code(anatol.post(f"/chat-temp/{chat_id}/users/{evgen_id}/", json={"role": "basic"}))["a"]
    assert check_code(anatol.post(f"/chat-temp/{chat_id}/users/{vasil_id}/", json={"role": "basic"}))["a"]

    # Transfer ownership
    assert check_code(anatol.post(f"/chat-temp/{chat_id}/users/{vasil_id}/owner/"))["a"]
    assert check_code(anatol.get(f"/chats/{chat_id}/")).get("role", None) == "admin"
    assert check_code(vasil.get(f"/chats/{chat_id}/")).get("role", None) == "owner"

    # Vasil quits, ownership transfers back to anatol
    result = check_code(vasil.delete(f"/chat-temp/{chat_id}/membership/"))
    assert dict_equal(result, {"branch": "assign-owner", "successor": anatol_id}, "branch", "successor")
    assert check_code(anatol.get(f"/chats/{chat_id}/")).get("role", None) == "owner"
    assert check_code(vasil.get(f"/chats/{chat_id}/"), 403)["a"] == "User not in the chat"

    # Evgen quits, nothing happens
    assert check_code(evgen.delete(f"/chat-temp/{chat_id}/membership/"))["branch"] == "just-quit"
    assert check_code(evgen.get(f"/chats/{chat_id}/"), 403)["a"] == "User not in the chat"
    assert check_code(anatol.get(f"/chats/{chat_id}/")).get("role", None) == "owner"

    # Anatol quits, chat is deleted automagically
    assert check_code(anatol.delete(f"/chat-temp/{chat_id}/membership/"))["branch"] == "delete-chat"
    assert check_code(anatol.get(f"/chats/{chat_id}/"), 404)["a"] == "Chat not found"


@mark.skip
@mark.order(650)
def test_messaging(list_tester: Callable[[str, dict, int], Iterator[dict]],
                   multi_client: Callable[[str], FlaskClient]):  # relies on chat#4
    def form_offline() -> dict[int, int]:
        offline_data: list[dict[str, int]] = check_code(anatol.get(f"/chat-temp/{chat_id}/users/offline/"))
        assert all("unread" in data.keys() and "user-id" in data.keys() for data in offline_data)
        return {data["user-id"]: data["unread"] for data in offline_data}

    def ensure_presence(online_users: list[int] = None, offline_users: list[int] = None):
        offline: dict[int, int] = form_offline()
        for user_id in online_users or []:
            assert user_id not in offline, f"Online user {user_id} is in offline users"
        for user_id in offline_users or []:
            assert user_id in offline, f"Offline user {user_id} is not in offline users"

    def get_messages():
        return list(list_tester(f"/chats/{chat_id}/message-history/", {}, 50))

    chat_id, anatol_id, vasil1_id, vasil2_id, evgen_id = 4, 4, 5, 8, 1  # user ids are assumed
    content1, content2 = "Lol that's a message I guess", "Not really I think"
    anatol: FlaskClient = multi_client("1@user.user")  # moder
    vasil1: FlaskClient = multi_client("2@user.user")  # muted
    vasil2: FlaskClient = multi_client("5@user.user")  # basic
    evgen: FlaskClient = multi_client("test@test.test")

    fist_offline: dict[int, int] = form_offline()
    ensure_presence([], [anatol_id, vasil1_id, vasil2_id, evgen_id])

    assert check_code(anatol.post(f"/chat-temp/{chat_id}/presence/", json={"online": True})) == {"a": False}
    assert check_code(vasil1.post(f"/chat-temp/{chat_id}/presence/", json={"online": True})) == {"a": False}
    assert check_code(vasil2.post(f"/chat-temp/{chat_id}/presence/", json={"online": True})) == {"a": False}
    ensure_presence([anatol_id, vasil1_id, vasil2_id], [evgen_id])
    notif_count = form_offline()
    messages = get_messages()

    # Sending a message
    message = {"content": content1}
    data = check_code(vasil1.post(f"/chat-temp/{chat_id}/messages/", json=message), 403)
    assert data == {"a": "You have to be at least chat's basic"}
    data = check_code(vasil2.post(f"/chat-temp/{chat_id}/messages/", json=message))
    assert "message_id" in data.keys() and "sent" in data.keys()

    # Checking message list & unread counts
    message.update({key.replace("message_", ""): value for key, value in data.items()})
    assert dict_equal(message, (new_messages := get_messages())[0], "content", "id", "sent")
    assert len(messages) + 1 == len(new_messages)
    assert {k: v + 1 for k, v in notif_count.items()} == (notif_count := form_offline())

    # Updating a message
    message["content"] = content2
    data = check_code(anatol.put(f"/chat-temp/{chat_id}/messages/{message['id']}/", json=message), 403)
    assert data == {"a": "Not your message"}
    data = check_code(vasil2.put(f"/chat-temp/{chat_id}/messages/{message['id']}/", json=message))
    assert "updated" in data.keys()

    # Checking message list & unread counts
    message.update(data)
    assert dict_equal(message, (new_messages := get_messages())[0], "content", "id", "sent", "updated")
    assert len(messages) + 1 == len(new_messages)
    assert notif_count == form_offline()

    # Deleting the message (by vasil)
    assert check_code(vasil2.delete(f"/chat-temp/{chat_id}/messages/{message['id']}/")) == {"a": True}
    check_code(vasil2.put(f"/chat-temp/{chat_id}/messages/{message['id']}/", json=message), 404)
    assert messages == get_messages()

    # Sending it again & deleting by anatol (moder)
    data = check_code(vasil2.post(f"/chat-temp/{chat_id}/messages/", json=message))
    assert check_code(anatol.delete(f"/chat-temp/{chat_id}/messages/{data['message_id']}/")) == {"a": True}
    check_code(vasil2.put(f"/chat-temp/{chat_id}/messages/{message['id']}/", json=message), 404)
    assert messages == get_messages()

    # Check going offline
    assert check_code(anatol.post(f"/chat-temp/{chat_id}/presence/", json={"online": False})) == {"a": False}
    assert check_code(vasil1.post(f"/chat-temp/{chat_id}/presence/", json={"online": False})) == {"a": False}
    assert check_code(vasil2.post(f"/chat-temp/close-all/", json={"ids": [chat_id]})) == {"a": True}

    last_offline = form_offline()
    for user_id, unread in fist_offline.items():
        assert user_id in last_offline.keys()
        if user_id in (anatol_id, vasil1_id, vasil2_id):
            assert last_offline[user_id] == 0
        else:
            assert last_offline[user_id] == unread + 2  # temp, until the deleted messages fix
