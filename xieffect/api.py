from datetime import timedelta
from json import dump, load
from logging import Logger
from os.path import exists
from sys import stderr

from common import app, versions, SocketIO
from common import db_meta, db_url  # noqa
from communities import (communities_namespace, invitation_namespace, invitation_join_namespace,
                         communities_meta_events)
# from communication import (chats_namespace)
from education import (authors_namespace, wip_json_file_namespace, wip_images_namespace,
                       images_view_namespace, wip_index_namespace, modules_view_namespace,
                       pages_view_namespace, education_namespace, interaction_namespace, result_namespace)
from other import (webhook_namespace, send_discord_message, send_file_discord_message, WebhookURLs)
from users import (reglog_namespace, users_namespace, invites_namespace, feedback_namespace,
                   settings_namespace, other_settings_namespace, protected_settings_namespace)

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
                    WebhookURLs.ERRORS, message, "error_message.txt", "Server error appeared!")
            if response.status_code < 200 or response.status_code > 299:
                send_discord_message(WebhookURLs.ERRORS, f"Server error appeared!\nBut I failed to report it...")


jwt = app.configure_jwt_with_loaders(["cookies"], timedelta(hours=72), lambda *x: logger.warning(x[1]),
                                     samesite_cookie="None", csrf_protect=False)
api = app.configure_restx()

api.add_namespace(reglog_namespace)
api.add_namespace(users_namespace)

api.add_namespace(settings_namespace)
api.add_namespace(other_settings_namespace)
api.add_namespace(protected_settings_namespace)
api.add_namespace(feedback_namespace)
api.add_namespace(invites_namespace)

# api.add_namespace(chats_namespace)

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
api.add_namespace(invitation_join_namespace)

api.add_namespace(webhook_namespace)

socketio = SocketIO(app, cors_allowed_origins="*", version=versions["SIO"], logger=True, engineio_logger=True)

socketio.add_namespace("/", communities_meta_events, protected=True)


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


version_check()


@app.cli.command("form-sio-docs")
def form_sio_docs():
    with open("../files/async-api.json", "w") as f:
        dump(socketio.docs(), f, ensure_ascii=False)

# class MessagesNamespace(Namespace):
#     @jwt_required()  # if not self.authenticate(request.args): raise ConnectionRefusedError("unauthorized!")
#     def on_connect(self, _):
#         join_room(f"user-{get_jwt_identity()}")
#
#     # def on_disconnect(self, session, user_id: int):
#     #     chat_ids = [int(chat_id) for room_name in rooms() if (chat_id := room_name.partition("chat-")[2]) != ""]
#     #     if len(chat_ids):
#     #        UserToChat.find_and_close(session, user.id, ids)
#
#
# messages_namespace = MessagesNamespace("/")
# messages_namespace.attach_event_group(messaging_events, use_kebab_case=True)
# messages_namespace.attach_event_group(chat_management_events, use_kebab_case=True)
# messages_namespace.attach_event_group(user_management_events, use_kebab_case=True)
#
# socketio.on_namespace(messages_namespace)

# remove-item alias:\curl
