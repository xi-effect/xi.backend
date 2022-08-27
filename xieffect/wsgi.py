from datetime import datetime
from json import load, dump
from os.path import exists
from pathlib import Path
from sys import modules, argv

from api import app as application, log_stuff, socketio
from common import User, sessionmaker, db_url, db_meta, mail_initialized, versions
from moderation import permission_index, Moderator
from other import WebhookURLs, send_discord_message
from users.invites_db import Invite  # noqa: F401  # passthrough for tests

TEST_EMAIL: str = "test@test.test"
ADMIN_EMAIL: str = "admin@admin.admin"
TEST_MOD_NAME: str = "test"

TEST_PASS: str = "q"
BASIC_PASS: str = "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454"  # not secret!
ADMIN_PASS: str = "2b003f13e43546e8b416a9ff3c40bc4ba694d0d098a5a5cda2e522d9993f47c7b85b733b178843961eefe9cfbeb287fe"  # not secret!

TEST_INVITE_ID: int = 0


@sessionmaker.with_begin
def init_test_mod(session):
    if Moderator.find_by_name(session, TEST_MOD_NAME) is None:
        moderator = Moderator.register(session, TEST_MOD_NAME, TEST_PASS)
        moderator.super = True


if (
    __name__ == "__main__"
    or "pytest" in modules
    or db_url == "sqlite:///test.db"
    or "form-sio-docs" in argv
):
    application.debug = True
    if db_url == "sqlite:///app.db":
        db_meta.drop_all()
    db_meta.create_all()
    init_test_mod()
else:  # works on server restart
    send_discord_message(WebhookURLs.NOTIFY, "Application restated")

    setup_fail: bool = False
    for secret_name in (
        "SECRET_KEY",
        "SECURITY_PASSWORD_SALT",
        "JWT_SECRET_KEY",
        "API_KEY",
    ):
        if application.config[secret_name] == "hope it's local":
            send_discord_message(
                WebhookURLs.NOTIFY,
                f"ERROR! No environmental variable for secret `{secret_name}`",
            )
            setup_fail = True
    if db_url == "sqlite:///app.db":
        send_discord_message(
            WebhookURLs.NOTIFY, "ERROR! No environmental variable for db url!"
        )
        setup_fail = True
    if not mail_initialized:
        send_discord_message(
            WebhookURLs.NOTIFY,
            "ERROR! Some environmental variable(s) for main are missing!",
        )
        setup_fail = True
    if setup_fail:
        send_discord_message(WebhookURLs.NOTIFY, "Production environment setup failed")

permission_index.initialize()


def init_folder_structure():
    Path("../files/avatars").mkdir(parents=True, exist_ok=True)
    Path("../files/images").mkdir(parents=True, exist_ok=True)
    Path("../files/temp").mkdir(parents=True, exist_ok=True)
    Path("../files/vault").mkdir(parents=True, exist_ok=True)

    Path("../files/tfs/wip-pages").mkdir(parents=True, exist_ok=True)
    Path("../files/tfs/wip-modules").mkdir(parents=True, exist_ok=True)


@sessionmaker.with_begin
def init_users(session):
    if (invite := Invite.find_by_id(session, TEST_INVITE_ID)) is None:
        log_stuff("status", "Database has been reset")
        invite: Invite = Invite.create(session, id=TEST_INVITE_ID, name="TEST_INVITE")

    from education.authorship import Author

    if (User.find_by_email_address(session, TEST_EMAIL)) is None:
        test_user: User = User.create(
            session,
            email=TEST_EMAIL,
            username="test",
            password=BASIC_PASS,
            invite=invite,
        )
        test_user.author = Author.create(session, test_user)

    if (
        User.find_by_email_address(session, ADMIN_EMAIL)
    ) is None:  # TODO DEPRECATED, redo with MUB
        User.create(session, email=ADMIN_EMAIL, username="admin", password=ADMIN_PASS)

    with open("../static/test/user-bundle.json", encoding="utf-8") as f:
        for i, user_settings in enumerate(load(f)):
            email: str = f"{i}@user.user"
            if (user := User.find_by_email_address(session, email)) is None:
                user = User.create(
                    session, email=email, username=f"user-{i}", password=BASIC_PASS
                )
            user.change_settings(user_settings)


@sessionmaker.with_begin
def init_knowledge(session):
    from education.authorship import Author
    from education.knowledge import Module, Page
    from education.studio import WIPPage, WIPModule

    test_author: Author = User.find_by_email_address(session, TEST_EMAIL).author

    with open("../static/test/page-bundle.json", "rb") as f:
        for page_data in load(f):
            WIPPage.create_from_json(session, test_author, page_data)
            Page.find_or_create(session, page_data, test_author)

    with open("../static/test/module-bundle.json", encoding="utf-8") as f:
        for module_data in load(f):
            module = WIPModule.create_from_json(session, test_author, module_data)
            module.id = module_data["id"]
            session.flush()
            Module.create(session, module_data, test_author, force=True)


@sessionmaker.with_begin
def init_chats(session):
    from communication.chatting_db import Chat, ChatRole, Message

    with open("../static/test/chat-bundle.json", encoding="utf-8") as f:
        for i, chat_data in enumerate(load(f)):
            if Chat.find_by_id(session, i + 1):
                continue
            owner: User = User.find_by_email_address(session, chat_data["owner-email"])
            chat: Chat = Chat.create(session, chat_data["name"], owner)
            for email, role in chat_data["participants"]:
                if email != owner.email:
                    chat.add_participant(
                        session,
                        User.find_by_email_address(session, email),
                        ChatRole.from_string(role),
                    )
            for message_data in chat_data["messages"]:
                sender = User.find_by_email_address(
                    session, message_data["sender-email"]
                )
                message: Message = Message.create(
                    session, chat, message_data["content"], sender, update_unread=False
                )
                message.sent = datetime.fromisoformat(message_data["sent"])
                if message_data["updated"] is not None:
                    message.updated = datetime.fromisoformat(message_data["updated"])


def version_check():
    if exists("../files/versions-lock.json"):
        with open("../files/versions-lock.json", encoding="utf-8") as f:
            versions_lock: dict[str, str] = load(f)
    else:
        versions_lock: dict[str, str] = {}

    if versions_lock != versions:
        log_stuff(
            "status",
            "\n".join(
                [
                    f"{key:3} was updated to {versions[key]}"
                    for key in versions.keys()
                    if versions_lock.get(key, None) != versions[key]
                ]
            ).expandtabs(),
        )
        with open("../files/versions-lock.json", "w", encoding="utf-8") as f:
            dump(versions, f, ensure_ascii=False)


@application.cli.command("form-sio-docs")
def form_sio_docs():
    with open("../files/async-api.json", "w") as f:
        dump(socketio.docs(), f, ensure_ascii=False)


init_folder_structure()
init_users()
init_knowledge()
version_check()

if __name__ == "__main__":  # test only
    socketio.run(
        application,
        reloader_options={"extra_files": ["../../static/public/index.html"]},
    )
