from __future__ import annotations

import logging
from json import dump as dump_json, load as load_json
from pathlib import Path

from api import app as application, log_stuff, socketio
from common import (
    db,
    db_url,
    mail_initialized,
    open_file,
    versions,
    TEST_MOD_NAME,
    TEST_PASS,
    TEST_INVITE_ID,
    TEST_EMAIL,
    BASIC_PASS,
    absolute_path,
)
from common.consts import PRODUCTION_MODE, DATABASE_RESET
from moderation import Moderator, permission_index
from other.discorder import send_message as send_discord_message, WebhookURLs
from users.invites_db import Invite
from users.users_db import User

SECRETS = (
    "SECRET_KEY",
    "SECURITY_PASSWORD_SALT",
    "JWT_SECRET_KEY",
    "API_KEY",
)


def init_test_mod() -> None:
    if Moderator.find_by_name(TEST_MOD_NAME) is None:
        moderator = Moderator.register(TEST_MOD_NAME, TEST_PASS)
        moderator.super = True


if PRODUCTION_MODE:  # works on server restart  # pragma: no coverage
    try:
        send_discord_message(WebhookURLs.NOTIFY, "Application restated")
    except Exception as e:  # noqa: PIE786
        logging.error("Bot reporting failed", exc_info=e)

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
else:  # pragma: no coverage
    application.debug = True
    with application.app_context():
        if db_url.endswith("app.db") or DATABASE_RESET:
            db.drop_all()
        if not db_url.startswith("postgresql") or DATABASE_RESET:
            db.create_all()
        init_test_mod()
        db.session.commit()


def init_folder_structure() -> None:
    Path(absolute_path("files/avatars")).mkdir(parents=True, exist_ok=True)
    Path(absolute_path("files/images")).mkdir(parents=True, exist_ok=True)
    Path(absolute_path("files/temp")).mkdir(parents=True, exist_ok=True)
    Path(absolute_path("files/vault")).mkdir(parents=True, exist_ok=True)

    Path(absolute_path("files/tfs/wip-pages")).mkdir(parents=True, exist_ok=True)
    Path(absolute_path("files/tfs/wip-modules")).mkdir(parents=True, exist_ok=True)


def init_users() -> None:
    invite: Invite = Invite.find_by_id(TEST_INVITE_ID)
    if invite is None:
        log_stuff("status", "Database has been reset")
        invite: Invite = Invite.create(id=TEST_INVITE_ID, name="TEST_INVITE")

    if (User.find_by_email_address(TEST_EMAIL)) is None:
        User.create(
            email=TEST_EMAIL,
            username="test",
            password=BASIC_PASS,
            invite=invite,
        )

    with open_file("static/test/user-bundle.json") as f:
        for i, user_settings in enumerate(load_json(f)):
            email: str = f"{i}@user.user"
            user: User = User.find_by_email_address(email)
            if user is None:
                user = User.create(
                    email=email,
                    username=f"user-{i}",
                    password=BASIC_PASS,
                )
            user.change_settings(**user_settings)


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


with application.app_context():
    permission_index.initialize()
    init_folder_structure()
    init_users()
    version_check()
    db.session.commit()

if __name__ == "__main__":  # test only
    socketio.run(
        application,
        reloader_options={"extra_files": [absolute_path("static/public/index.html")]},
    )
