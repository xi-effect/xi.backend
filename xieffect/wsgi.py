# noqa: WPS201
from __future__ import annotations

from json import dump as dump_json, load as load_json
from os.path import exists
from pathlib import Path
from sys import argv, modules

from api import app as application, log_stuff, socketio
from common import db_url, mail_initialized, db, User, versions
from moderation import Moderator, permission_index
from other import send_discord_message, WebhookURLs
from users.invites_db import Invite  # noqa: F401  # noqa: WPS201  # for tests

TEST_EMAIL: str = "test@test.test"
ADMIN_EMAIL: str = "admin@admin.admin"
TEST_MOD_NAME: str = "test"

TEST_PASS: str = "q"
BASIC_PASS: str = "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454"  # not secret!
ADMIN_PASS: str = "2b003f13e43546e8b416a9ff3c40bc4ba694d0d098a5a5cda2e522d9993f47c7b85b733b178843961eefe9cfbeb287fe"  # not secret!

TEST_INVITE_ID: int = 0

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
    or db_url == "sqlite:///test.db"
    or "form-sio-docs" in argv
):
    application.debug = True
    if db_url == "sqlite:///../app.db":
        db.drop_all()
    db.create_all()
    with application.app_context():
        init_test_mod()
        db.session.commit()
else:  # works on server restart
    send_discord_message(WebhookURLs.NOTIFY, "Application restated")

    setup_fail: bool = False
    for secret_name in SECRETS:
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


def init_folder_structure():
    Path("../files/avatars").mkdir(parents=True, exist_ok=True)
    Path("../files/images").mkdir(parents=True, exist_ok=True)
    Path("../files/temp").mkdir(parents=True, exist_ok=True)
    Path("../files/vault").mkdir(parents=True, exist_ok=True)

    Path("../files/tfs/wip-pages").mkdir(parents=True, exist_ok=True)
    Path("../files/tfs/wip-modules").mkdir(parents=True, exist_ok=True)


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

    if (User.find_by_email_address(ADMIN_EMAIL)) is None:
        # TODO DEPRECATED, redo with MUB
        User.create(email=ADMIN_EMAIL, username="admin", password=ADMIN_PASS)

    with open("../static/test/user-bundle.json", encoding="utf-8") as f:
        for i, user_settings in enumerate(load_json(f)):
            email: str = f"{i}@user.user"
            if (user := User.find_by_email_address(email)) is None:
                user = User.create(
                    email=email,
                    username=f"user-{i}",
                    password=BASIC_PASS,
                )
            user.change_settings(user_settings)


def init_knowledge():
    from education.authorship import Author
    from education.knowledge import Module, Page
    from education.studio import WIPPage, WIPModule

    test_author: Author = User.find_by_email_address(TEST_EMAIL).author

    with open("../static/test/page-bundle.json", "rb") as f:
        for page_data in load_json(f):
            WIPPage.create_from_json(test_author, page_data)
            Page.find_or_create(page_data, test_author)

    with open("../static/test/module-bundle.json", encoding="utf-8") as f:
        for module_data in load_json(f):
            module = WIPModule.create_from_json(test_author, module_data)
            module.id = module_data["id"]
            db.session.flush()
            Module.create(module_data, test_author, force=True)


def version_check():
    if exists("../files/versions-lock.json"):
        with open("../files/versions-lock.json", encoding="utf-8") as f:
            versions_lock: dict[str, str] = load_json(f)
    else:
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
        with open("../files/versions-lock.json", "w", encoding="utf-8") as f:
            dump_json(versions, f, ensure_ascii=False)


@application.cli.command("form-sio-docs")
def form_sio_docs():
    with open("../files/async-api.json", "w", encoding="utf-8") as f:
        dump_json(socketio.docs(), f, ensure_ascii=False)


@application.after_request
def hey(res):
    db.session.commit()
    return res


with application.app_context():
    permission_index.initialize()
    init_folder_structure()
    init_users()
    init_knowledge()
    version_check()
    db.session.commit()


if __name__ == "__main__":  # test only
    socketio.run(
        application,
        reloader_options={"extra_files": ["../../static/public/index.html"]},
    )
