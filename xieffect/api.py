from datetime import datetime, timedelta, timezone
from json import dumps
from sys import stderr
from traceback import format_tb

from flask import Response, request
from flask_jwt_extended import JWTManager, get_jwt, get_jwt_identity, create_access_token, set_access_cookies
from flask_restx import Api
from werkzeug.exceptions import NotFound, HTTPException

from common import TokenBlockList, with_session
from common._marshals import flask_restx_has_bad_design  # noqa
# from communication import (chats_namespace)
from education import (authors_namespace, wip_json_file_namespace, wip_images_namespace,
                       images_view_namespace, wip_index_namespace, modules_view_namespace,
                       pages_view_namespace, education_namespace, interaction_namespace)
from education.knowledge.results_rst import result_namespace
from main import app, db_meta, versions  # noqa
from other import (webhook_namespace, send_discord_message, send_file_discord_message, WebhookURLs)
from users import (reglog_namespace, users_namespace, invites_namespace, feedback_namespace,
                   settings_namespace, other_settings_namespace, protected_settings_namespace, profiles_namespace)

from communities import (communities_namespace, invitation_namespace, invitation_join_namespace)

authorizations = {
    "jwt": {
        "type": "apiKey",
        "in": "cookie",
        "name": "access_token_cookie"
    }
}
api: Api = Api(app, doc="/doc/", version=versions["API"], authorizations=authorizations)

api.add_namespace(communities_namespace)
api.add_namespace(invitation_namespace)
api.add_namespace(invitation_join_namespace)

api.add_namespace(reglog_namespace)
api.add_namespace(users_namespace)
api.add_namespace(profiles_namespace)
api.add_namespace(result_namespace)
api.add_namespace(settings_namespace)
api.add_namespace(other_settings_namespace)
api.add_namespace(protected_settings_namespace)
api.add_namespace(feedback_namespace)
api.add_namespace(invites_namespace)

# api.add_namespace(chats_namespace)

api.add_namespace(education_namespace)
api.add_namespace(images_view_namespace)
api.add_namespace(pages_view_namespace)
api.add_namespace(modules_view_namespace)
api.add_namespace(interaction_namespace)

api.add_namespace(authors_namespace)
api.add_namespace(wip_images_namespace)
api.add_namespace(wip_json_file_namespace)
api.add_namespace(wip_index_namespace)

api.add_namespace(webhook_namespace)
api.add_namespace(flask_restx_has_bad_design)  # TODO workaround

jwt: JWTManager = JWTManager(app)

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


@jwt.token_in_blocklist_loader
@with_session
def check_if_token_revoked(_, jwt_payload, session):
    return TokenBlockList.find_by_jti(session, jwt_payload["jti"]) is not None


@app.after_request
def refresh_expiring_jwt(response: Response):
    try:
        target_timestamp = datetime.timestamp(datetime.now(timezone.utc) + timedelta(hours=36))
        if target_timestamp > get_jwt()["exp"]:
            set_access_cookies(response, create_access_token(identity=get_jwt_identity()))
        return response
    except (RuntimeError, KeyError):
        return response


@app.errorhandler(NotFound)
def on_not_found(_):
    return {"a": "Not found"}, 404


@app.errorhandler(HTTPException)
def handle_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = e.get_response()
    # replace the body with JSON
    response.data = dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response


@app.errorhandler(Exception)
def on_any_exception(error: Exception):
    error_text: str = f"Requested URL: {request.path}\nError: {repr(error)}\n" + \
                      "".join(format_tb(error.__traceback__))
    log_stuff("error", error_text)
    return {"a": error_text}, 500


@jwt.expired_token_loader
def expired_token_callback(*_):
    return {"a": "expired token"}, 401


@jwt.token_verification_failed_loader
def verification_failed_callback(*_):
    log_stuff("error", f"Token verification somehow failed\n[`{datetime.utcnow()}`]")
    return {"a": f"token verification failed"}, 401


@jwt.invalid_token_loader
def invalid_token_callback(callback):
    log_stuff("error", f"Invalid token: {callback}\n[`{datetime.utcnow()}`]")
    return {"a": f"invalid token: {callback}"}, 422


@jwt.unauthorized_loader
def unauthorized_callback(callback):
    if callback != "Missing cookie \"access_token_cookie\"":
        log_stuff("error", f"Unauthorized: {callback}\n[`{datetime.utcnow()}`]")
    return {"a": f"unauthorized: {callback}"}, 401

# remove-item alias:\curl
