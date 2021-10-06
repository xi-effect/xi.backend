from datetime import datetime, timedelta, timezone
from json import load, dump
from os.path import exists
from sys import stderr
from traceback import format_tb
from typing import Dict

from flask import Response, request
from flask_jwt_extended import JWTManager, get_jwt, get_jwt_identity, create_access_token, set_access_cookies
from flask_restx import Api
from werkzeug.exceptions import HTTPException

from authorship import (Author, authors_namespace)
from componets import with_session
from education import (modules_view_namespace, pages_view_namespace, StandardProgresser, PracticeGenerator,
                       TheoryNavigator, TheoryContentsGetter, TestContentsGetter, TestNavigator, TestReplySaver,
                       TestResultCollector, FilterGetter)
from file_system import (wip_json_file_namespace, wip_images_namespace, ImageViewer)
from main import app, Session, versions
from other import (Version, SubmitTask, GetTaskSummary, UpdateRequest)  # UploadAppUpdate,
from outside import (basic_namespace, github_namespace)
from users import (TokenBlockList, UserRegistration, UserLogin, UserLogout, PasswordResetSender,
                   PasswordReseter, Avatar, settings_namespace, EmailChanger,
                   PasswordChanger, EmailSender, EmailConfirm, AvatarViewer)
from webhooks import send_discord_message, send_file_discord_message, WebhookURLs

# Initializing modules
api: Api = Api(app, doc="/doc/", version=versions["API"])

ns = api.namespace("main", path="/")

api.add_namespace(basic_namespace)
api.add_namespace(github_namespace)

api.add_namespace(settings_namespace)

api.add_namespace(pages_view_namespace)
api.add_namespace(modules_view_namespace)

api.add_namespace(authors_namespace)

api.add_namespace(wip_images_namespace)
api.add_namespace(wip_json_file_namespace)

jwt: JWTManager = JWTManager(app)


def log_stuff(level: str, message: str):
    if app.debug:
        print(message, **({"file": stderr} if level == "error" else {}))
    else:
        if level == "status":
            send_discord_message(WebhookURLs.STATUS, message)
        else:
            response = send_file_discord_message(
                WebhookURLs.ERRORS, message, "error_message.txt", "Server error appeared!")
            if response.status_code < 200 or response.status_code > 299:
                send_discord_message(WebhookURLs.ERRORS, f"Server error appeared!\nBut I failed to report it...")


# Some request and error handlers:
@app.before_first_request
@with_session
def create_tables(session: Session):
    if exists("../files/versions-lock.json"):
        versions_lock: Dict[str, str] = load(open("../files/versions-lock.json", encoding="utf-8"))
    else:
        versions_lock: Dict[str, str] = {}

    if versions_lock != versions:
        log_stuff("status", "\n".join([
            f"{key:3} was updated to {versions[key]}"
            for key in versions.keys()
            if versions_lock.get(key, None) != versions[key]
        ]).expandtabs())
        dump(versions, open("../files/versions-lock.json", "w", encoding="utf-8"), ensure_ascii=False)

    from main import db_meta
    db_meta.create_all()

    from education.elements import Module, Page
    from file_system.keeper import WIPPage
    from other.test_keeper import TestPoint
    from users import User

    test_user: User
    if (test_user := User.find_by_email_address(session, "test@test.test")) is None:
        log_stuff("status", "Database has been reset")
        test_user = User.create(session, "test@test.test", "test", "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c" +
                                "13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454")
    test_author = Author.find_or_create(session, test_user)

    Module.create_test_bundle(session, test_author)
    Page.create_test_bundle(session, test_author)
    WIPPage.create_test_bundle(session, test_author)
    TestPoint.test(session)

    if User.find_by_email_address(session, "admin@admin.admin") is None:
        User.create(session, "admin@admin.admin", "admin", "2b003f13e43546e8b416a9ff3c40bc4ba694d" +
                    "0d098a5a5cda2e522d9993f47c7b85b733b178843961eefe9cfbeb287fe")


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


@app.errorhandler(HTTPException)
def on_http_exception(error: HTTPException):
    return ("Not found", 404) if error.response is None else error.response


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
    return {"a": f"token verification failed"}, 401


@jwt.invalid_token_loader
def invalid_token_callback(callback):
    return {"a": f"invalid token: {callback}"}, 422


@jwt.unauthorized_loader
def unauthorized_callback(callback):
    return {"a": f"unauthorized: {callback}"}, 401


# Adding email resources:
ns.add_resource(EmailSender, "/email/<email>/")
ns.add_resource(EmailConfirm, "/email-confirm/")

# Adding sign up/in/out resources:
ns.add_resource(UserRegistration, "/reg/")
ns.add_resource(UserLogin, "/auth/")
ns.add_resource(UserLogout, "/logout/")

# Adding password resetting resources:
ns.add_resource(PasswordResetSender, "/password-reset/<email>/")
ns.add_resource(PasswordReseter, "/password-reset/confirm/")

# Adding settings resources:
ns.add_resource(Avatar, "/avatar/")
ns.add_resource(EmailChanger, "/email-change/")
ns.add_resource(PasswordChanger, "/password-change/")

# Adding profile viewing resource(s):
ns.add_resource(AvatarViewer, "/authors/<int:user_id>/avatar/")

# Adding module resources:
ns.add_resource(FilterGetter, "/filters/")

# Adding in-module resources:
ns.add_resource(StandardProgresser, "/sessions/<int:session_id>/")
ns.add_resource(PracticeGenerator, "/modules/<int:module_id>/next/")
ns.add_resource(TheoryContentsGetter, "/modules/<int:module_id>/contents/")
ns.add_resource(TheoryNavigator, "/modules/<int:module_id>/points/<int:point_id>/")
ns.add_resource(TestContentsGetter, "/tests/<int:test_id>/contents/")
ns.add_resource(TestNavigator, "/tests/<int:test_id>/tasks/<int:task_id>/")
ns.add_resource(TestReplySaver, "/tests/<int:test_id>/tasks/<int:task_id>/reply/")
ns.add_resource(TestResultCollector, "/tests/<int:test_id>/results/")

# Adding image resources:
ns.add_resource(ImageViewer, "/images/<image_id>/")

# Adding application resource(s):
ns.add_resource(Version, "/<app_name>/version/")

# Adding side-thing resources:
ns.add_resource(UpdateRequest, "/oct/update/")
ns.add_resource(SubmitTask, "/tasks/<task_name>/attempts/new/")
ns.add_resource(GetTaskSummary, "/tasks/<task_name>/attempts/all/")

if __name__ == "__main__":  # test only
    app.run(debug=True)
    # app.run(debug=True, ssl_context="adhoc")

# CURL:
# remove-item alias:\curl
# curl -v --cookie -X
# curl -H "Content-Type: application/json" http://localhost:5000/settings/
# -X POST -v -d "{\"changed\": {\"username\": \"new\"}}"
# curl "https://xieffect.pythonanywhere.com/auth/?email=test@test.test&password=0a989ebc4a77b56a6e2bb7b19d995d185ce4409
# 0c13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454" -X POST -v
# curl "https://xieffect.pythonanywhere.com/" -X POST -v --cookie "access_token_cookie="
