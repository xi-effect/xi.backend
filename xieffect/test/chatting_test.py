from typing import Callable, Iterator

from flask.testing import FlaskClient
from pytest import mark

from .components import check_status_code


@mark.order(600)
def test_chat_owning(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    # Creating a new chat:
    chat_name1, chat_name2 = "test", "production"
    assert (chat_id := check_status_code(client.post("/chats/", json={"name": chat_name1})).get("id", None)) is not None

    # Checking initial chat metadata:
    assert check_status_code(client.get(f"/chats/{chat_id}/")) == {"name": chat_name1, "role": "owner", "users": 1}
    assert any(chat == {"id": chat_id, "name": chat_name1} for chat in list_tester("/chats/index/", {}, 50))

    # Checking the initial user-list:
    user_list = list(list_tester(f"/chats/{chat_id}/users/", {}, 50))
    assert len(user_list) == 1
    assert (user := user_list[0])["role"] == "owner"
    test_user_id = user["id"]

    # Generating users to invite:
    invited: dict[int] = {test_user_id: "owner", 3: "muted", 4: "basic", 5: "moder", 6: "admin"}  # redo with /users/
    bulk = [user_id for user_id in list(invited) if user_id != test_user_id]

    # Inviting users:
    assert check_status_code(client.post(f"/chats/{chat_id}/users/add-all/", json={"ids": bulk[:-1]})) == {"a": True}
    assert check_status_code(client.post(f"/chats/{chat_id}/users/{bulk[-1]}/"))

    # Changing users' roles:
    assert all(check_status_code(client.put(f"/chats/{chat_id}/users/{user_id}/", json={"role": role}))["a"]
               for user_id, role in invited.items()
               if user_id != test_user_id)
    # MB add a check for inviting already invited users

    # Editing & checking chat metadata:
    assert check_status_code(client.put(f"/chats/{chat_id}/manage/", json={"name": chat_name2})) == {"a": True}
    chat_data = {"name": chat_name2, "role": "owner", "users": len(invited)}
    assert check_status_code(client.get(f"/chats/{chat_id}/")) == chat_data
    assert any(chat == {"id": chat_id, "name": chat_name2} for chat in list_tester("/chats/index/", {}, 50))

    # Check the updated user-list:
    for user in list_tester(f"/chats/{chat_id}/users/", {}, 50):
        assert list(user.keys()) == ["id", "role", "username"]
        assert user["id"] in invited.keys(), "Invited user not found in a chat"
        assert user["role"] == invited[user["id"]]

    # Kick one user & check the updated user-list:
    check_status_code(client.delete(f"/chats/{chat_id}/users/{(removed_user_id := list(invited)[2])}/"))
    assert all(user["id"] != removed_user_id for user in list_tester(f"/chats/{chat_id}/users/", {}, 50))

    # Delete the chat & check absence:
    assert check_status_code(client.delete(f"/chats/{chat_id}/manage/")) == {"a": True}
    assert check_status_code(client.get(f"/chats/{chat_id}/"), 404)
    assert all(chat["id"] != chat_id for chat in list_tester("/chats/index/", {}, 50))
