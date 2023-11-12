from __future__ import annotations

from datetime import timedelta
from json import dump as dump_json
from logging import Logger
from sys import stderr

from flask_fullstack import SocketIO
from requests import HTTPError

import communities.base.discussion_db  # noqa: F401 WPS301  # to create database models
import pages.pages_db  # noqa: F401 WPS301  # to create database models
from common import app, db, versions, open_file, JSONEncoder
from communities.base import (
    invitations_rst,
    invitations_sio,
    meta_rst,
    meta_sio,
    participants_sio,
    roles_rst,
    roles_sio,
)
from communities.services import news_rst, news_sio, videochat_rst, videochat_sio
from communities.tasks import (
    tasks_sio,
    teacher_rst,
    tests_sio,
    tests_teacher_rst,
    questions_sio,
    student_rst,
)
from moderation import mub_base_namespace, mub_cli_blueprint, mub_super_namespace
from other import updater_rst, database_cli
from other.discorder import (
    send_message as send_discord_message,
    send_file_message as send_file_discord_message,
    WebhookURLs,
)
from users import (
    emailer_mub,
    feedback_mub,
    feedback_rst,
    invites_mub,
    profiles_rst,
    reglog_rst,
    settings_rst,
    users_mub,
)
from vault import files_mub, files_rst

logger = Logger("flask-fullstack", "WARN")


def log_stuff(level: str, message: str) -> None:  # TODO # noqa: WPS231
    if app.debug:
        print(message, **({"file": stderr} if level == "error" else {}))
    else:  # pragma: no cover
        if level == "status":
            send_discord_message(WebhookURLs.STATUS, message)
        else:
            try:
                if len(message) < 200:
                    send_discord_message(WebhookURLs.ERRORS, message)
                else:
                    send_file_discord_message(
                        WebhookURLs.ERRORS,
                        file_content=message,
                        file_name="error_message.txt",
                        message="Server error appeared!",
                    )
            except HTTPError:
                send_discord_message(
                    WebhookURLs.ERRORS,
                    "Server error appeared!\nBut I failed to report it...",
                )


jwt = app.configure_jwt_with_loaders(
    ["cookies"],
    timedelta(hours=72),
    lambda *x: logger.warning(x[1]),
    samesite_cookie="None",
    csrf_protect=False,
)
api = app.configure_restx()

# Files
api.add_namespace(files_rst.controller)
api.add_namespace(files_mub.controller)

# Users
api.add_namespace(reglog_rst.controller)
api.add_namespace(profiles_rst.controller)
api.add_namespace(settings_rst.controller)
api.add_namespace(users_mub.controller)

# Feedback
api.add_namespace(feedback_rst.controller)
api.add_namespace(feedback_mub.controller)

# Communities base
api.add_namespace(meta_rst.controller)
api.add_namespace(roles_rst.controller)
api.add_namespace(invitations_rst.controller)

# Communities services
api.add_namespace(news_rst.controller)
api.add_namespace(videochat_rst.controller)

# Communities tasks & tests
api.add_namespace(teacher_rst.controller)
api.add_namespace(tests_teacher_rst.controller)
api.add_namespace(student_rst.controller)

# Other
app.register_blueprint(database_cli.blueprint)
api.add_namespace(updater_rst.controller)

# MUB + QA
app.register_blueprint(mub_cli_blueprint)
api.add_namespace(mub_base_namespace)
api.add_namespace(mub_super_namespace)
api.add_namespace(emailer_mub.controller)
api.add_namespace(invites_mub.controller)

socketio = SocketIO(
    app,
    title="SIO",
    version=versions["SIO"],
    doc_path="/asyncapi.json",
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True,
    remove_ping_pong_logs=True,
    restx_models=api.models,
)

socketio.add_namespace(
    "/",
    # Communities base
    meta_sio.controller,
    roles_sio.controller,
    invitations_sio.controller,
    participants_sio.controller,
    # Communities services
    news_sio.controller,
    videochat_sio.controller,
    # Communities tasks & tests
    tasks_sio.controller,
    tests_sio.controller,
    questions_sio.controller,
    protected=True,
)

socketio.after_event(db.with_autocommit)
app.after_request(db.with_autocommit)


@app.cli.command("form-sio-docs")
def form_sio_docs() -> None:  # TODO pragma: no coverage
    with open_file("files/async-api.json", "w") as f:
        dump_json(socketio.docs(), f, ensure_ascii=False, cls=JSONEncoder)
