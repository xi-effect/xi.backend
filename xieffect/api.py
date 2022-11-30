from __future__ import annotations

from datetime import timedelta
from json import dump as dump_json
from logging import Logger
from sys import stderr

from flask_fullstack import SocketIO

from common import app, versions, open_file
from common import db  # noqa: F401
from communities import (
    communities_meta_events,
    communities_namespace,
    invitation_events,
    invitation_namespace,
    news_namespace,
    news_events,
    tasks_namespace,
    tasks_events,
)
from education import (
    authors_namespace,
    education_namespace,
    images_view_namespace,
    interaction_namespace,
    modules_view_namespace,
    pages_view_namespace,
    result_namespace,
    wip_images_namespace,
    wip_index_namespace,
    wip_json_file_namespace,
)
from moderation import mub_base_namespace, mub_cli_blueprint, mub_super_namespace
from other import (
    send_discord_message,
    send_file_discord_message,
    webhook_namespace,
    WebhookURLs,
)
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


def log_stuff(level: str, message: str):  # TODO # noqa: WPS231
    if app.debug:
        print(message, **({"file": stderr} if level == "error" else {}))
    else:  # pragma: no cover
        if level == "status":
            send_discord_message(WebhookURLs.STATUS, message)
        else:
            if len(message) < 200:
                response = send_discord_message(WebhookURLs.ERRORS, message)
            else:
                response = send_file_discord_message(
                    WebhookURLs.ERRORS,
                    message,
                    "error_message.txt",
                    "Server error appeared!",
                )
            if response.status_code < 200 or response.status_code > 299:
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

api.add_namespace(education_namespace)
api.add_namespace(modules_view_namespace)
api.add_namespace(pages_view_namespace)
api.add_namespace(images_view_namespace)

api.add_namespace(interaction_namespace)
api.add_namespace(result_namespace)

api.add_namespace(authors_namespace)
api.add_namespace(wip_images_namespace)
api.add_namespace(wip_json_file_namespace)
api.add_namespace(wip_index_namespace)

api.add_namespace(communities_namespace)
api.add_namespace(invitation_namespace)
api.add_namespace(news_namespace)
api.add_namespace(tasks_namespace)

api.add_namespace(webhook_namespace)

app.register_blueprint(mub_cli_blueprint)
api.add_namespace(mub_base_namespace)
api.add_namespace(mub_super_namespace)

api.add_namespace(emailer_qa_namespace)
api.add_namespace(mub_users_namespace)
api.add_namespace(invites_mub_namespace)

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
    invitation_events,
    news_events,
    tasks_events,
    protected=True
)

socketio.after_event(db.with_autocommit)


@app.cli.command("form-sio-docs")
def form_sio_docs():  # TODO pragma: no coverage
    with open_file("files/async-api.json", "w") as f:
        dump_json(socketio.docs(), f, ensure_ascii=False)

# remove-item alias:\curl
