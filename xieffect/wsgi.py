from __future__ import annotations

from json import dump as dump_json, load as load_json
from pathlib import Path
from sys import argv, modules

from api import app as application, log_stuff, socketio
from common import (
    db,
    db_url,
    mail_initialized,
    open_file,
    User,
    versions,
    TEST_MOD_NAME,
    TEST_PASS,
    TEST_INVITE_ID,
    TEST_EMAIL,
    BASIC_PASS,
    absolute_path,
)
from moderation import Moderator, permission_index
from other import send_discord_message, WebhookURLs
from users.invites_db import Invite

SECRETS = (
    "SECRET_KEY",
    "SECURITY_PASSWORD_SALT",
    "JWT_SECRET_KEY",
    "API_KEY",
)


def init_test_mod():
    if Moderator.find_by_name(TEST_MOD_NAME) is None:
        moderator = Moderator.register(TEST_MOD_NAME, TEST_PASS)
        moderator.super = True


if (  # noqa: WPS337
    __name__ == "__main__"
    or "pytest" in modules
    or db_url.endswith("test.db")
    or "form-sio-docs" in argv
):  # pragma: no coverage
    application.debug = True
    if db_url.endswith("app.db"):
        db.drop_all()
    if not db_url.startswith("postgresql"):
        db.create_all()
    with application.app_context():
        init_test_mod()
        db.session.commit()
else:  # works on server restart  # pragma: no coverage
    send_discord_message(WebhookURLs.NOTIFY, "Application restated")

    setup_fail: bool = False
    for secret_name in SECRETS:
        if application.config[secret_name] == "hope it's local":
            send_discord_message(
                WebhookURLs.NOTIFY,
                f"ERROR! No environmental variable for secret `{secret_name}`",
            )
            setup_fail = True
    if db_url.endswith("app.db"):
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


def init_folder_structure():
    Path(absolute_path("files/avatars")).mkdir(parents=True, exist_ok=True)
    Path(absolute_path("files/images")).mkdir(parents=True, exist_ok=True)
    Path(absolute_path("files/temp")).mkdir(parents=True, exist_ok=True)
    Path(absolute_path("files/vault")).mkdir(parents=True, exist_ok=True)

    Path(absolute_path("files/tfs/wip-pages")).mkdir(parents=True, exist_ok=True)
    Path(absolute_path("files/tfs/wip-modules")).mkdir(parents=True, exist_ok=True)


def init_users():
    if (invite := Invite.find_by_id(TEST_INVITE_ID)) is None:
        log_stuff("status", "Database has been reset")
        invite: Invite = Invite.create(id=TEST_INVITE_ID, name="TEST_INVITE")

    from education.authorship import Author

    if (User.find_by_email_address(TEST_EMAIL)) is None:
        test_user: User = User.create(
            email=TEST_EMAIL,
            username="test",
            password=BASIC_PASS,
            invite=invite,
        )
        test_user.author = Author.create(test_user)

    with open_file("static/test/user-bundle.json") as f:
        for i, user_settings in enumerate(load_json(f)):
            email: str = f"{i}@user.user"
            if (user := User.find_by_email_address(email)) is None:
                user = User.create(
                    email=email,
                    username=f"user-{i}",
                    password=BASIC_PASS,
                )
            user.change_settings(**user_settings)


def init_knowledge():
    from education.authorship import Author
    from education.knowledge import Module, Page
    from education.studio import WIPPage, WIPModule

    test_author: Author = User.find_by_email_address(TEST_EMAIL).author

    with open_file("static/test/page-bundle.json") as f:
        for page_data in load_json(f):
            WIPPage.create_from_json(test_author, page_data)
            Page.find_or_create(page_data, test_author)

    with open_file("static/test/module-bundle.json") as f:
        for module_data in load_json(f):
            module = WIPModule.create_from_json(test_author, module_data)
            module.id = module_data["id"]
            db.session.flush()
            Module.create(module_data, test_author, force=True)


def version_check():  # TODO pragma: no coverage
    try:
        with open_file("files/versions-lock.json") as f:
            versions_lock: dict[str, str] = load_json(f)
    except FileNotFoundError:
        versions_lock: dict[str, str] = {}

    if versions_lock != versions:
        log_stuff(
            "status",
            "\n".join(
                [
                    f"{key:3} was updated to {versions[key]}"
                    for key in versions.keys()
                    if versions_lock.get(key) != versions[key]
                ]
            ).expandtabs(),
        )
        with open_file("files/versions-lock.json", "w") as f:
            dump_json(versions, f, ensure_ascii=False)


def sqlite_pragma():
    if db_url.startswith("sqlite"):
        from sqlalchemy import event
        from sqlalchemy.engine import Engine

        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(*args):
            cursor = args[0].cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()


with application.app_context():
    permission_index.initialize()
    init_folder_structure()
    init_users()
    init_knowledge()
    version_check()
    sqlite_pragma()
    db.session.commit()

if __name__ == "__main__":  # test only
    socketio.run(
        application,
        reloader_options={"extra_files": [absolute_path("static/public/index.html")]},
    )
