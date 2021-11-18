from json import load
from typing import Callable, Iterator

from flask.testing import FlaskClient
from pytest import mark

from .components import check_status_code


@mark.order(600)
def test_chat_owning(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    # Creating a new chat:
    chat_name1, chat_name2 = "test", "production"
    chat_id = check_status_code(client.post("/chat-temp/", json={"name": chat_name1})).get("id", None)
    assert chat_id is not None

    # Checking initial chat metadata & message-history:
    data = {"name": chat_name1, "role": "owner", "users": 1, "unread": 0}
    assert check_status_code(client.get(f"/chats/{chat_id}/")) == data
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
    assert all(check_status_code(client.post(f"/chat-temp/{chat_id}/users/add-all/", json={"ids": bulk[:-1]})))
    assert check_status_code(client.post(f"/chat-temp/{chat_id}/users/{an_id}/", json={"role": invited[an_id]}))["a"]

    # Fail to invite the same users:
    assert not any(check_status_code(client.post(f"/chat-temp/{chat_id}/users/add-all/", json={"ids": bulk[:-1]})))
    assert not check_status_code(client.post(f"/chat-temp/{chat_id}/users/{an_id}/", json={"role": invited[an_id]}))["a"]

    # Changing users' roles:
    assert all(client.put(f"/chat-temp/{chat_id}/users/{user_id}/", json={"role": role}).status_code == 200
               for user_id, role in invited.items()
               if user_id != test_user_id and user_id != an_id)
    # MB add a check for inviting already invited users

    # Editing chat metadata:
    assert check_status_code(client.put(f"/chat-temp/{chat_id}/manage/", json={"name": chat_name2})) == {"a": True}
    # Checking chat metadata:
    chat_data = {"name": chat_name2, "role": "owner", "users": len(invited), "unread": 0}
    assert check_status_code(client.get(f"/chats/{chat_id}/")) == chat_data
    assert any(chat["id"] == chat_id and chat["name"] == chat_name2 for chat in list_tester("/chats/index/", {}, 50))

    # Check the updated user-list:
    for user in list_tester(f"/chats/{chat_id}/users/", {}, 50):
        assert list(user.keys()) == ["id", "role", "user-avatar", "username"]
        assert user["id"] in invited.keys(), "Invited user not found in a chat"
        assert user["role"] == invited[user["id"]]

    # Kick one user:
    check_status_code(client.delete(f"/chat-temp/{chat_id}/users/{(removed_user_id := list(invited)[2])}/"))
    # Check the updated user-list
    assert all(user["id"] != removed_user_id for user in list_tester(f"/chats/{chat_id}/users/", {}, 50))

    # Delete the chat:
    assert check_status_code(client.delete(f"/chat-temp/{chat_id}/manage/")) == {"a": True}
    # Check chat's absence:
    assert check_status_code(client.get(f"/chats/{chat_id}/"), 404)
    assert all(chat["id"] != chat_id for chat in list_tester("/chats/index/", {}, 50))


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
        code = 200 if role == "admin" else 403

        check_status_code(client.delete(f"/chat-temp/{chat_id}/manage/"), 403)
        check_status_code(client.put(f"/chat-temp/{chat_id}/manage/", json={"name": "new_name"}), code)
        if role == "admin":
            assert check_status_code(client.get(f"/chats/{chat_id}/"))["name"] == "new_name"
        check_status_code(client.put(f"/chat-temp/{chat_id}/manage/", json={"name": chat_name}), code)
        if role == "admin":
            assert check_status_code(client.get(f"/chats/{chat_id}/"))["name"] == chat_name

        for target in list_tester(f"/chats/{chat_id}/users/", {}, 50):
            target_id = target["id"]
            code = 200 if role == "admin" and target["role"] not in ("owner", "admin") else 403
            if target_id != user_id:
                check_status_code(client.delete(f"/chat-temp/{chat_id}/users/{target_id}/"), code)
                assert code == 403 or (check_status_code(client.get(f"/chats/{chat_id}/"))["users"] == chat_uc - 1)

                check_status_code(client.post(f"/chat-temp/{chat_id}/users/{target_id}/",
                                              json={"role": target["role"]}), code)
                assert code == 403 or check_status_code(client.get(f"/chats/{chat_id}/"))["users"] == chat_uc
