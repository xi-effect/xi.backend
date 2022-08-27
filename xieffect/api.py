from datetime import timedelta
from logging import Logger
from sys import stderr

from common import app, versions, SocketIO
from common import db_meta, db_url  # noqa
from communities import (
    communities_namespace,
    invitation_namespace,
    communities_meta_events,
    invitation_events,
)
from education import (
    authors_namespace,
    wip_json_file_namespace,
    wip_images_namespace,
    images_view_namespace,
    wip_index_namespace,
    modules_view_namespace,
    pages_view_namespace,
    education_namespace,
    interaction_namespace,
    result_namespace,
)
from moderation import mub_base_namespace, mub_cli_blueprint, mub_super_namespace
from other import (
    webhook_namespace,
    send_discord_message,
    send_file_discord_message,
    WebhookURLs,
)
from users import (
    reglog_namespace,
    users_namespace,
    invites_namespace,
    feedback_namespace,
    settings_namespace,
    users_mub_namespace,
    emailer_qa_namespace,
)
from vault import files_namespace, mub_files_namespace

logger = Logger("flask-fullstack", "WARN")


def log_stuff(level: str, message: str):
    if app.debug:
        print(message, **({"file": stderr} if level == "error" else {}))
    else:
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

api.add_namespace(settings_namespace)
api.add_namespace(feedback_namespace)
api.add_namespace(invites_namespace)

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

api.add_namespace(webhook_namespace)

app.register_blueprint(mub_cli_blueprint)
api.add_namespace(mub_base_namespace)
api.add_namespace(mub_super_namespace)

api.add_namespace(emailer_qa_namespace)
api.add_namespace(users_mub_namespace)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    version=versions["SIO"],
    logger=True,
    engineio_logger=True,
)

socketio.add_namespace("/", communities_meta_events, invitation_events, protected=True)

# remove-item alias:\curl
