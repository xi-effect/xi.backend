from datetime import datetime, timedelta, timezone
from traceback import format_tb

from flask import Response, request
from flask_jwt_extended import JWTManager, get_jwt, get_jwt_identity, create_access_token, set_access_cookies
from flask_restful import Api
from werkzeug.exceptions import HTTPException

from authorship import (Author, Submitter, SubmissionLister, SubmissionIndexer, SubmissionReader,
                        ReviewIndex, Publisher, AuthorInitializer, OwnedPagesLister)
from education import (ModuleLister, HiddenModuleLister, ModuleReporter, ModulePreferences,
                       PageLister, PageReporter, PageMetadataGetter, PageComponentsGetter,
                       StandardProgresser, PracticeGenerator, TheoryNavigator, TheoryContentsGetter,
                       TestContentsGetter, TestNavigator, TestReplySaver, TestResultCollector,
                       FilterGetter, ShowAll, ModuleOpener)
from file_system import (FileLister, FileProcessor, FileCreator)
from main import app, db
from other import (Version, SubmitTask, GetTaskSummary, UpdateRequest)  # UploadAppUpdate,
from outside import (HelloWorld, ServerMessenger, GithubDocumentsWebhook)
from users import (TokenBlockList, UserRegistration, UserLogin, UserLogout, PasswordResetSender,
                   PasswordReseter, Avatar, Settings, MainSettings, RoleSettings, EmailChanger,
                   PasswordChanger, EmailSender, EmailConfirm)
from webhooks import send_discord_message, send_file_discord_message, WebhookURLs

# Initializing modules
api: Api = Api(app)
jwt: JWTManager = JWTManager(app)


# Some request and error handlers:
@app.before_first_request
def create_tables():
    db.create_all()
    # from main import whooshee
    # whooshee.reindex()

    from education.elements import Module, Page
    from other.test_keeper import TestPoint
    from users import User

    test_user: User
    if (test_user := User.find_by_email_address("test@test.test")) is None:
        send_discord_message(WebhookURLs.STATUS, "Database has been reset")
        test_user = User.create("test@test.test", "test", "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c" +
                                "13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454")
    test_author = Author.find_or_create(test_user)

    Module.create_test_bundle()
    Page.create_test_bundle(test_author)
    TestPoint.test()

    if User.find_by_email_address("admin@admin.admin") is None:
        User.create("admin@admin.admin", "admin", "2b003f13e43546e8b416a9ff3c40bc4ba694d" +
                    "0d098a5a5cda2e522d9993f47c7b85b733b178843961eefe9cfbeb287fe")


@jwt.token_in_blocklist_loader
def check_if_token_revoked(_, jwt_payload):
    return TokenBlockList.find_by_jti(jwt_payload["jti"]) is not None


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
                      "".join(format_tb(error.__traceback__)[6:])

    response = send_file_discord_message(WebhookURLs.ERRORS, error_text, "error_message.txt", "Server error appeared!")
    if response.status_code < 200 or response.status_code > 299:
        send_discord_message(WebhookURLs.ERRORS, f"Server error appeared!\nBut I failed to report it...")
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


# Adding basic resources:
api.add_resource(HelloWorld, "/")
api.add_resource(ServerMessenger, "/status/")

# Adding email resources:
api.add_resource(EmailSender, "/email/<email>/")
api.add_resource(EmailConfirm, "/email-confirm/")

# Adding sign up/in/out resources:
api.add_resource(UserRegistration, "/reg/")
api.add_resource(UserLogin, "/auth/")
api.add_resource(UserLogout, "/logout/")

# Adding password resetting resources:
api.add_resource(PasswordResetSender, "/password-reset/<email>/")
api.add_resource(PasswordReseter, "/password-reset/confirm/")

# Adding settings resources:
api.add_resource(Avatar, "/avatar/")
api.add_resource(Settings, "/settings/")
api.add_resource(MainSettings, "/settings/main/")
api.add_resource(RoleSettings, "/settings/roles/")
api.add_resource(EmailChanger, "/email-change/")
api.add_resource(PasswordChanger, "/password-change/")

# Adding student's main_page resources:
# api.add_resource(SchoolIntegration, "/school/")
# api.add_resource(Activities, "/activities/")
# api.add_resource(Tasks, "/tasks/<int:task_id>/")
# api.add_resource(Notif, "/notif/<int:notification_id>/")

# Adding module resources:
api.add_resource(FilterGetter, "/filters/")
api.add_resource(ModuleLister, "/modules/", "/courses/")
api.add_resource(HiddenModuleLister, "/modules/hidden/", "/courses/hidden/")
api.add_resource(ModulePreferences, "/modules/<int:module_id>/preference/", "/courses/<int:module_id>/preference/")
api.add_resource(ModuleReporter, "/modules/<int:module_id>/report/", "/courses/<int:module_id>/report/")

# Adding page resources:
api.add_resource(PageLister, "/pages/")
api.add_resource(PageReporter, "/pages/<int:page_id>/report/")
api.add_resource(PageMetadataGetter, "/pages/<int:page_id>/")
api.add_resource(PageComponentsGetter, "/pages/<int:page_id>/components/")

# Adding in-module resources:
api.add_resource(ModuleOpener, "/modules/<int:module_id>/")
api.add_resource(StandardProgresser, "/sessions/<int:session_id>/")
api.add_resource(PracticeGenerator, "/modules/<int:module_id>/next/")
api.add_resource(TheoryContentsGetter, "/modules/<int:module_id>/contents/")
api.add_resource(TheoryNavigator, "/modules/<int:module_id>/points/<int:point_id>/")
api.add_resource(TestContentsGetter, "/tests/<int:test_id>/contents/")
api.add_resource(TestNavigator, "/tests/<int:test_id>/tasks/<int:task_id>/")
api.add_resource(TestReplySaver, "/tests/<int:test_id>/tasks/<int:task_id>/reply/")
api.add_resource(TestResultCollector, "/tests/<int:test_id>/results/")

# Adding role control:
api.add_resource(AuthorInitializer, "/authors/permit/")

# Adding work-in-progress resources:
api.add_resource(FileLister, "/wip/<file_type>/index/")
api.add_resource(FileCreator, "/wip/<file_type>/")
api.add_resource(FileProcessor, "/wip/<file_type>/<int:file_id>/")

# Adding author studio resource(s):
api.add_resource(OwnedPagesLister, "/pages/owned/")

# Adding publishing resources:
api.add_resource(Submitter, "/cat/submissions/")
api.add_resource(SubmissionLister, "/cat/submissions/owned/")
api.add_resource(SubmissionIndexer, "/cat/submissions/index/")
api.add_resource(SubmissionReader, "/cat/submissions/<int:submission_id>/")
api.add_resource(ReviewIndex, "/cat/reviews/<int:submission_id>/")
api.add_resource(Publisher, "/cat/publications/")

# Adding application resource(s):
api.add_resource(Version, "/<app_name>/version/")
# api.add_resource(GithubWebhook,         "/update/")
api.add_resource(GithubDocumentsWebhook, "/update-docs/")

# Adding side-thing resources:
api.add_resource(UpdateRequest, "/oct/update/")
api.add_resource(SubmitTask, "/tasks/<task_name>/attempts/new/")
api.add_resource(GetTaskSummary, "/tasks/<task_name>/attempts/all/")

# Test only:
api.add_resource(ShowAll, "/test/")

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
