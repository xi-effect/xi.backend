from pytest import mark

from .components import (assert_one, assert_one_with_data, form_pass, assert_broadcast, ensure_broadcast, ensure_pass,
                         assert_no_additional_messages)
from .conftest import MultiClient, BASIC_PASS


@mark.order(600)
def test_chat_owning(socket_tr_io_client: MultiClient):  # assumes test's id == 1
    anatol, evgen, vasil = socket_tr_io_client.get_tr_io()

    # Creating a new chat:
    chat_name1, chat_name2 = "test", "production"
    anatol.emit("add-chat", incoming_data := {"name": chat_name1})

    assert anatol.received_count() == 2
    event_data = assert_one(anatol.filter_received("add-chat"))
    assert event_data.get("name", None) == chat_name1
    assert (chat_id := event_data.get("chat-id", None)) is not None
    ensure_pass(anatol, form_pass("POST", "/chat-temp/", incoming_data, {"id": chat_id}))

    # Inviting Evgen to chat:
    anatol.emit("invite-user", {"chat-id": chat_id, "role": "basic", "target-id": 1})
    ensure_pass(anatol, form_pass("POST", f"/chat-temp/{chat_id}/users/1/", {"role": "basic"}, {"a": True}))
    assert_one_with_data(evgen.filter_received("add-chat"), {"chat-id": chat_id, "name": chat_name1})

    # Editing chat metadata:
    ensure_broadcast(anatol, "edit-chat", {"chat-id": chat_id, "name": chat_name2}, evgen)
    ensure_pass(anatol, form_pass("PUT", f"/chat-temp/{chat_id}/manage/", {"name": chat_name2}, {"a": True}))

    # Deleting the chat:
    ensure_broadcast(anatol, "delete-chat", {"chat-id": chat_id}, evgen)
    ensure_pass(anatol, form_pass("DELETE", f"/chat-temp/{chat_id}/manage/", None, {"a": True}))

    # Deleting it again for all time sake:
    anatol.emit("delete-chat", {"chat-id": chat_id})
    event_data = assert_one(anatol.filter_received("error"))
    assert event_data.pop("timestamp", None) is not None
    assert event_data == {"code": 404, "message": "Chat not found", "event": "delete-chat"}


@mark.order(610)
def test_user_managing(socket_tr_io_client: MultiClient):  # relies on chat#3  # assumes vasil's id == 10
    anatol1, evgen1, vasil1, anatol2, evgen2, vasil2 = socket_tr_io_client.get_dtr_io()
    chat_id, vasil_id = 3, 10

    # Setup (open chat were needed)
    anatol1.emit("open-chat", {"chat-id": chat_id})
    ensure_pass(anatol1, form_pass("POST", f"/chat-temp/{chat_id}/presence/", {"online": True}, {"a": False}))
    evgen1.emit("open-chat", {"chat-id": chat_id})
    ensure_pass(evgen1, form_pass("POST", f"/chat-temp/{chat_id}/presence/", {"online": True}, {"a": False}))
    # assert_broadcast("notif", {"chat-id": chat_id, "unread": 0}, anatol1, anatol2, evgen1, evgen2)
    assert_no_additional_messages(anatol1, evgen1, vasil1, anatol2, evgen2, vasil2)

    # Invite vasil to the chat
    ensure_broadcast(anatol1, "invite-user", {"chat-id": chat_id, "role": "basic", "target-id": vasil_id}, evgen1)
    ensure_pass(anatol1, form_pass("POST", f"/chat-temp/{chat_id}/users/{vasil_id}/", {"role": "basic"}, {"a": True}))

    # Check that evgen got add-chat on both
    assert_broadcast("add-chat", {"chat-id": chat_id, "name": "Quaerat"}, vasil1, vasil2)
    assert_no_additional_messages(anatol1, evgen1, vasil1, anatol2, evgen2, vasil2)

    # Fail to invite vasil for the second time
    anatol1.emit("invite-user", {"chat-id": chat_id, "target-id": vasil_id, "role": "basic"})
    ensure_pass(anatol1, form_pass("POST", f"/chat-temp/{chat_id}/users/{vasil_id}/", {"role": "basic"}, {"a": False}))
    assert_no_additional_messages(anatol1, evgen1, vasil1, anatol2, evgen2, vasil2)

    # Setup for vasil
    vasil1.emit("open-chat", {"chat-id": chat_id})
    ensure_pass(vasil1, form_pass("POST", f"/chat-temp/{chat_id}/presence/", {"online": True}, {"a": False}))
    # assert_broadcast("notif", {"chat-id": chat_id, "unread": 0}, vasil1, vasil2)
    assert_no_additional_messages(anatol1, evgen1, vasil1, anatol2, evgen2, vasil2)

    # Fail to assign the same role to vasil
    anatol1.emit("assign-user", {"chat-id": chat_id, "target-id": vasil_id, "role": "basic"})
    ensure_pass(anatol1, form_pass("PUT", f"/chat-temp/{chat_id}/users/{vasil_id}/", {"role": "basic"}, {"a": False}))
    assert_no_additional_messages(anatol1, evgen1, vasil1, anatol2, evgen2, vasil2)

    # Assign vasil a different role
    event_data = {"chat-id": chat_id, "target-id": vasil_id, "role": "muted"}
    ensure_broadcast(anatol1, "assign-user", event_data, vasil1, evgen1)
    ensure_pass(anatol1, form_pass("PUT", f"/chat-temp/{chat_id}/users/{vasil_id}/", {"role": "muted"}, {"a": True}))
    assert_no_additional_messages(anatol1, evgen1, vasil1, anatol2, evgen2, vasil2)

    # Kick vasil
    ensure_broadcast(anatol1, "kick-user", {"chat-id": chat_id, "target-id": vasil_id}, evgen1, vasil1)
    ensure_pass(anatol1, form_pass("DELETE", f"/chat-temp/{chat_id}/users/{vasil_id}/", None, {"a": True}))
    assert_broadcast("delete-chat", {"chat-id": chat_id}, vasil1, vasil2)
    assert_no_additional_messages(anatol1, evgen1, vasil1, anatol2, evgen2, vasil2)

    # Vasil should close chat after the kick:
    vasil1.emit("close-chat", {"chat-id": chat_id, "kicked": True})
    assert_no_additional_messages(anatol1, evgen1, vasil1, anatol2, evgen2, vasil2)

    # Invite vasil to the chat (with invite-users)
    ensure_broadcast(anatol1, "invite-users", {"chat-id": chat_id, "user-ids": [vasil_id]}, evgen1)
    ensure_pass(anatol1, form_pass("POST", f"/chat-temp/{chat_id}/users/add-all/", {"ids": [vasil_id]}, [True]))

    # Check that evgen got add-chat on both (with invite-users)
    assert_broadcast("add-chat", {"chat-id": chat_id, "name": "Quaerat"}, vasil1, vasil2)
    assert_no_additional_messages(anatol1, evgen1, vasil1, anatol2, evgen2, vasil2)

    # Setup for vasil
    vasil1.emit("open-chat", {"chat-id": chat_id})
    ensure_pass(vasil1, form_pass("POST", f"/chat-temp/{chat_id}/presence/", {"online": True}, {"a": False}))
    # assert_broadcast("notif", {"chat-id": chat_id, "unread": 0}, vasil1, vasil2)
    assert_no_additional_messages(anatol1, evgen1, vasil1, anatol2, evgen2, vasil2)

    # Fail to invite vasil for the second time (with invite-users)
    anatol1.emit("invite-users", {"chat-id": chat_id, "user-ids": [vasil_id]})
    ensure_pass(anatol1, form_pass("POST", f"/chat-temp/{chat_id}/users/add-all/", {"ids": [vasil_id]}, [False]))
    assert_no_additional_messages(anatol1, evgen1, vasil1, anatol2, evgen2, vasil2)

    # Vasil can close chat before the kick:
    vasil1.emit("close-chat", {"chat-id": chat_id})
    ensure_pass(vasil1, form_pass("POST", f"/chat-temp/{chat_id}/presence/", {"online": False}, {"a": False}))
    assert_no_additional_messages(anatol1, evgen1, vasil1, anatol2, evgen2, vasil2)

    # Vasil quits
    ensure_broadcast(vasil1, "kick-user", {"chat-id": chat_id, "target-id": vasil_id}, anatol1, evgen1, echo=False)
    ensure_pass(vasil1, form_pass("DELETE", f"/chat-temp/{chat_id}/membership/", None, {"branch": "just-quit"}))
    assert_broadcast("delete-chat", {"chat-id": chat_id}, vasil1, vasil2)
    assert_no_additional_messages(anatol1, evgen1, vasil1, anatol2, evgen2, vasil2)

    # Close opened chats
    anatol1.emit("close-chat", {"chat-id": chat_id})
    ensure_pass(anatol1, form_pass("POST", f"/chat-temp/{chat_id}/presence/", {"online": False}, {"a": False}))
    evgen1.emit("close-chat", {"chat-id": chat_id})
    ensure_pass(evgen1, form_pass("POST", f"/chat-temp/{chat_id}/presence/", {"online": False}, {"a": False}))
    assert_no_additional_messages(anatol1, evgen1, vasil1, anatol2, evgen2, vasil2)


@mark.order(625)
def test_ownership_transfer(multi_client: MultiClient):  # user ids are assumed
    multi_client.attach_auth_user("Anatol-1", "1@user.user", BASIC_PASS)
    multi_client.attach_auth_user("Anatol-2", "1@user.user", BASIC_PASS)
    multi_client.attach_auth_user("Evgen-1", "2@user.user", BASIC_PASS)
    multi_client.attach_auth_user("Evgen-2", "2@user.user", BASIC_PASS)
    multi_client.attach_auth_user("Vasil-1", "3@user.user", BASIC_PASS)
    multi_client.attach_auth_user("Vasil-2", "3@user.user", BASIC_PASS)
    anatol, evgen, vasil, anatol2, evgen2, vasil2 = multi_client.get_dtr_io()
    anatol_id, evgen_id, vasil_id = 4, 5, 6

    # Creating the chat
    anatol.emit("add-chat", {"name": "test"})
    assert (chat_id := assert_one(anatol.filter_received("add-chat")).get("chat-id", None)) is not None
    ensure_pass(anatol, form_pass("POST", "/chat-temp/", {"name": "test"}, {"id": chat_id}))
    assert assert_one(anatol2.filter_received("add-chat")) == {"chat-id": chat_id, "name": "test"}
    assert_no_additional_messages(anatol, evgen, vasil, anatol2, evgen2, vasil2)

    # Open chat for anatol
    anatol.emit("open-chat", {"chat-id": chat_id})
    ensure_pass(anatol, form_pass("POST", f"/chat-temp/{chat_id}/presence/", {"online": True}, {"a": False}))

    # Inviting evgen & vasil
    ensure_broadcast(anatol, "invite-users", {"chat-id": chat_id, "user-ids": [vasil_id, evgen_id]})
    ensure_pass(anatol, form_pass("POST", f"/chat-temp/{chat_id}/users/add-all/",
                                  {"ids": [vasil_id, evgen_id]}, [True, True]))
    assert_broadcast("add-chat", {"chat-id": chat_id, "name": "test"}, vasil, vasil2, evgen, evgen2)
    assert_no_additional_messages(anatol, evgen, vasil, anatol2, evgen2, vasil2)

    # Open chats for evgen and vasil
    evgen.emit("open-chat", {"chat-id": chat_id})
    ensure_pass(evgen, form_pass("POST", f"/chat-temp/{chat_id}/presence/", {"online": True}, {"a": False}))
    vasil.emit("open-chat", {"chat-id": chat_id})
    ensure_pass(vasil, form_pass("POST", f"/chat-temp/{chat_id}/presence/", {"online": True}, {"a": False}))
    assert_no_additional_messages(anatol, evgen, vasil, anatol2, evgen2, vasil2)

    # Transfer ownership
    anatol.emit("assign-owner", incoming_data := {"chat-id": chat_id, "target-id": vasil_id, "source-id": anatol_id})
    assert_broadcast("assign-owner", incoming_data, anatol, evgen, vasil)
    ensure_pass(anatol, form_pass("POST", f"/chat-temp/{chat_id}/users/{vasil_id}/owner/", None, {"a": True}))
    assert_no_additional_messages(anatol, evgen, vasil, anatol2, evgen2, vasil2)

    # Vasil quits, ownership transfers back to anatol
    vasil.emit("kick-user", {"chat-id": chat_id})
    ensure_pass(vasil, form_pass("DELETE", f"/chat-temp/{chat_id}/membership/", None,
                                 {"branch": "assign-owner", "successor": anatol_id}))
    assert_broadcast("kick-user", {"chat-id": chat_id, "target-id": vasil_id}, anatol, evgen)
    assert_broadcast("assign-owner", {"chat-id": chat_id, "target-id": anatol_id}, anatol, evgen)
    assert_broadcast("delete-chat", {"chat-id": chat_id}, vasil, vasil2)
    assert_no_additional_messages(anatol, evgen, vasil, anatol2, evgen2, vasil2)

    # Evgen quits, nothing happens
    evgen.emit("kick-user", {"chat-id": chat_id})
    ensure_pass(evgen, form_pass("DELETE", f"/chat-temp/{chat_id}/membership/", None, {"branch": "just-quit"}))
    assert_broadcast("kick-user", {"chat-id": chat_id, "target-id": evgen_id}, anatol)
    assert_broadcast("delete-chat", {"chat-id": chat_id}, evgen, evgen2)
    assert_no_additional_messages(anatol, evgen, vasil, anatol2, evgen2, vasil2)

    # Anatol quits, chat is deleted automagically
    anatol.emit("kick-user", {"chat-id": chat_id})
    ensure_pass(anatol, form_pass("DELETE", f"/chat-temp/{chat_id}/membership/", None, {"branch": "delete-chat"}))
    assert_broadcast("delete-chat", {"chat-id": chat_id}, anatol, anatol2)
    assert_no_additional_messages(anatol, evgen, vasil, anatol2, evgen2, vasil2)


@mark.order(650)
def test_messaging(socket_tr_io_client: MultiClient):  # relies on chat#4
    anatol, evgen, vasil, anatol2, evgen2, vasil2 = socket_tr_io_client.get_dtr_io()
    chat_id, content = 4, "This is a cool message!"

    # Setup (open chats)
    anatol.emit("open-chat", {"chat-id": chat_id})
    ensure_pass(anatol, form_pass("POST", f"/chat-temp/{chat_id}/presence/", {"online": True}, {"a": False}))
    evgen.emit("open-chat", {"chat-id": chat_id})
    ensure_pass(evgen, form_pass("POST", f"/chat-temp/{chat_id}/presence/", {"online": True}, {"a": False}))
    # assert_broadcast("notif", {"chat-id": chat_id, "unread": 0}, anatol, evgen, anatol2, evgen2)
    assert_no_additional_messages(anatol, evgen, vasil, anatol2, evgen2, vasil2)

    # Sending a message
    anatol.emit("send-message", (temp := {"chat-id": chat_id, "content": content}))
    event_data = assert_one(anatol.filter_received("send-message"))
    assert (message_id := event_data.pop("message-id", None)) is not None
    assert (sent := event_data.pop("sent", None)) is not None
    assert event_data == temp
    ensure_pass(anatol, form_pass("POST", f"/chat-temp/{chat_id}/messages/",
                                  temp, {"sent": sent, "message_id": message_id}))

    # Check that everyone got the message or notif
    temp["message-id"] = message_id
    assert_broadcast("send-message", dict(temp, **{"sent": sent}), evgen)
    assert_broadcast("notif", {"chat-id": chat_id, "unread": 1}, vasil)
    assert_broadcast("notif", {"chat-id": chat_id, "unread": 1}, vasil2)
    assert_no_additional_messages(anatol, evgen, vasil, anatol2, evgen2, vasil2)

    # Editing the message
    anatol.emit("edit-message", temp)
    event_data = assert_one(anatol.filter_received("edit-message"))
    assert (updated := event_data.pop("updated", None)) is not None
    assert event_data == temp
    ensure_pass(anatol, form_pass("PUT", f"/chat-temp/{chat_id}/messages/{message_id}/", temp, {"updated": updated}))

    # Check that everyone got the message update
    assert_broadcast("edit-message", dict(temp, **{"updated": updated}), evgen)
    assert_no_additional_messages(anatol, evgen, vasil, anatol2, evgen2, vasil2)

    # Deleting the message & check
    temp.pop("content")
    ensure_broadcast(anatol, "delete-message", temp, evgen)
    ensure_pass(anatol, form_pass("DELETE", f"/chat-temp/{chat_id}/messages/{message_id}/", None, {"a": True}))

    # TODO notif has to be sent to vasil with !0! unread
    assert_broadcast("notif", {"chat-id": chat_id, "unread": 1}, vasil)
    assert_broadcast("notif", {"chat-id": chat_id, "unread": 1}, vasil2)
    assert_no_additional_messages(anatol, evgen, vasil, anatol2, evgen2, vasil2)

    # Close opened chats
    anatol.emit("close-chat", {"chat-id": chat_id})
    ensure_pass(anatol, form_pass("POST", f"/chat-temp/{chat_id}/presence/", {"online": False}, {"a": False}))
    evgen.emit("close-chat", {"chat-id": chat_id})
    ensure_pass(evgen, form_pass("POST", f"/chat-temp/{chat_id}/presence/", {"online": False}, {"a": False}))
    assert_no_additional_messages(anatol, evgen, vasil, anatol2, evgen2, vasil2)
