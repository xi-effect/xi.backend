from datetime import datetime
from json import load, dump
from os.path import exists
from pathlib import Path
from sys import modules

from api import app as application, log_stuff, db_meta  # noqa
from authorship import Author, Moderator
from communication.entities import Chat, ChatRole, Message
from componets import with_session
from education import Module, Page
from file_system.keeper import WIPPage
from main import versions
from other.test_keeper import TestPoint
from users import User, Invite, generate_code, dumps_feedback
from webhooks import WebhookURLs, send_discord_message

TEST_EMAIL: str = "test@test.test"
ADMIN_EMAIL: str = "admin@admin.admin"

BASIC_PASS: str = "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454"
ADMIN_PASS: str = "2b003f13e43546e8b416a9ff3c40bc4ba694d0d098a5a5cda2e522d9993f47c7b85b733b178843961eefe9cfbeb287fe"

TEST_INVITE_ID: int = 0

if __name__ == "__main__" or "pytest" in modules.keys():  # test only  # pytest here temporarily!!!
    application.debug = True
    db_meta.drop_all()
    db_meta.create_all()
else:  # works on server restart:
    send_discord_message(WebhookURLs.NOTIF, "Application restated")
    if any([send_discord_message(WebhookURLs.NOTIF, f"ERROR! No environmental variable for secret `{secret_name}`")
            for secret_name in ["SECRET_KEY", "SECURITY_PASSWORD_SALT", "JWT_SECRET_KEY", "API_KEY"]
            if application.config[secret_name] == "hope it's local"]):
        send_discord_message(WebhookURLs.NOTIF, "Production environment setup failed")


def init_folder_structure():
    Path("../files/avatars").mkdir(parents=True, exist_ok=True)
    Path("../files/images").mkdir(parents=True, exist_ok=True)
    Path("../files/temp").mkdir(parents=True, exist_ok=True)

    Path("../files/tfs/wip-pages").mkdir(parents=True, exist_ok=True)
    Path("../files/tfs/wip-modules").mkdir(parents=True, exist_ok=True)


@with_session
def init_invite(session):
    if Invite.find_by_id(session, TEST_INVITE_ID) is None:
        log_stuff("status", "Database has been reset")
        test_invite: Invite = Invite(id=TEST_INVITE_ID, name="TEST_INVITE")
        session.add(test_invite)
        session.flush()


@with_session
def init_users(session):
    invite = Invite.find_by_id(session, TEST_INVITE_ID)

    if (User.find_by_email_address(session, TEST_EMAIL)) is None:
        test_user: User = User.create(session, TEST_EMAIL, "test", BASIC_PASS, invite)
        test_user.author = Author.create(session, test_user)

    if (User.find_by_email_address(session, ADMIN_EMAIL)) is None:
        admin_user: User = User.create(session, ADMIN_EMAIL, "admin", ADMIN_PASS)
        # admin_user.moderator = Moderator.create(session, admin_user)

    with open("../files/test/user-bundle.json", encoding="utf-8") as f:
        for i, user_settings in enumerate(load(f)):
            email: str = f"{i}@user.user"
            if (user := User.find_by_email_address(session, email)) is None:
                user = User.create(session, email, f"user-{i}", BASIC_PASS)
            user.change_settings(user_settings)


@with_session
def init_knowledge(session):
    test_author: Author = User.find_by_email_address(session, TEST_EMAIL).author

    with open(f"../files/test/page-bundle.json", "rb") as f:
        for page_data in load(f):
            WIPPage.create_from_json(session, test_author, page_data)
            Page.find_or_create(session, page_data, test_author)

    with open("../files/test/module-bundle.json", encoding="utf-8") as f:
        for module_data in load(f):
            Module.create(session, module_data, test_author, force=True)


@with_session
def init_oct(session):
    TestPoint.test(session)


@with_session
def init_chats(session):
    with open("../files/test/chat-bundle.json", encoding="utf-8") as f:
        for i, chat_data in enumerate(load(f)):
            if Chat.find_by_id(session, i + 1):
                continue
            owner: User = User.find_by_email_address(session, chat_data["owner-email"])
            chat: Chat = Chat.create(session, chat_data["name"], owner)
            for email, role in chat_data["participants"]:
                if email != owner.email:
                    chat.add_participant(session, User.find_by_email_address(session, email),
                                         ChatRole.from_string(role))
            for message_data in chat_data["messages"]:
                sender = User.find_by_email_address(session, message_data["sender-email"])
                message: Message = Message.create(session, chat, message_data["content"], sender, False)
                message.sent = datetime.fromisoformat(message_data["sent"])
                if message_data["updated"] is not None:
                    message.updated = datetime.fromisoformat(message_data["updated"])


def version_check():
    if exists("../files/versions-lock.json"):
        versions_lock: dict[str, str] = load(open("../files/versions-lock.json", encoding="utf-8"))
    else:
        versions_lock: dict[str, str] = {}

    if versions_lock != versions:
        log_stuff("status", "\n".join([
            f"{key:3} was updated to {versions[key]}"
            for key in versions.keys()
            if versions_lock.get(key, None) != versions[key]
        ]).expandtabs())
        dump(versions, open("../files/versions-lock.json", "w", encoding="utf-8"), ensure_ascii=False)


init_folder_structure()
init_invite()
init_users()
init_knowledge()
init_oct()
init_chats()
version_check()

if __name__ == "__main__":  # test only
    application.run()  # (ssl_context="adhoc")
