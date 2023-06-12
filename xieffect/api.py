from __future__ import annotations

from datetime import timedelta
from json import dump as dump_json
from logging import Logger
from sys import stderr

from flask_fullstack import SocketIO
from requests import HTTPError

import communities.base.discussion_db  # TODO (use in api) # noqa: F401 WPS301
from common import app, db, versions, open_file
from communities import (
    communities_meta_events,
    communities_namespace,
    participants_events,
    invitation_events,
    invitation_namespace,
    news_namespace,
    news_events,
    role_namespace,
    role_events,
    teacher_tasks_namespace,
    student_tasks_namespace,
    tasks_events,
    videochat_events,
    videochat_namespace,
)
from moderation import mub_base_namespace, mub_cli_blueprint, mub_super_namespace
from other import (
    remove_stale_blueprint,
    send_discord_message,
    send_file_discord_message,
    webhook_namespace,
    WebhookURLs,
)
from pages.pages_db import Page  # noqa: F401 # to create database models
from users import (
    emailer_qa_namespace,
    feedback_namespace,
    invites_mub_namespace,
    mub_feedback_namespace,
    mub_users_namespace,
    reglog_namespace,
    settings_namespace,
    users_namespace,
)
from vault import files_namespace, mub_files_namespace

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

api.add_namespace(files_namespace)
api.add_namespace(mub_files_namespace)

api.add_namespace(reglog_namespace)
api.add_namespace(users_namespace)

api.add_namespace(feedback_namespace)
api.add_namespace(mub_feedback_namespace)
api.add_namespace(settings_namespace)

api.add_namespace(communities_namespace)
api.add_namespace(invitation_namespace)
api.add_namespace(news_namespace)
api.add_namespace(teacher_tasks_namespace)
api.add_namespace(student_tasks_namespace)
api.add_namespace(videochat_namespace)

app.register_blueprint(remove_stale_blueprint)
api.add_namespace(webhook_namespace)

app.register_blueprint(mub_cli_blueprint)
api.add_namespace(mub_base_namespace)
api.add_namespace(mub_super_namespace)

api.add_namespace(emailer_qa_namespace)
api.add_namespace(mub_users_namespace)
api.add_namespace(invites_mub_namespace)

api.add_namespace(role_namespace)

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
    communities_meta_events,
    participants_events,
    invitation_events,
    news_events,
    tasks_events,
    videochat_events,
    role_events,
    protected=True,
)

socketio.after_event(db.with_autocommit)
app.after_request(db.with_autocommit)


@app.cli.command("form-sio-docs")
def form_sio_docs() -> None:  # TODO pragma: no coverage
    with open_file("files/async-api.json", "w") as f:
        dump_json(socketio.docs(), f, ensure_ascii=False)
