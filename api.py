from datetime import datetime, timedelta, timezone
from traceback import format_tb

from flask import Response, request
from flask_jwt_extended import JWTManager, get_jwt, get_jwt_identity
from flask_jwt_extended import create_access_token, set_access_cookies
from flask_restful import Api

from api_resources import *
from webhooks import send_discord_message, send_file_discord_message, WebhookURLs
from database import Course, AuthorTeam, Author, TestPoint, User, CourseFilterSession  # test
from database import TokenBlockList
from main import app
from main import db

# Initializing modules
api: Api = Api(app)
jwt: JWTManager = JWTManager(app)


# Some request and error handlers:
@app.before_first_request
def create_tables():
    db.create_all()

    Course.test()
    TestPoint.test()

    if User.find_by_email_address("test@test.test") is None:
        send_discord_message(WebhookURLs.STATUS, "Database has been reset")
        User.create("test@test.test", "test", "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c" +
                    "13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454")
    if User.find_by_email_address("admin@admin.admin") is None:
        User.create("admin@admin.admin", "admin", "2b003f13e43546e8b416a9ff3c40bc4ba694d" +
                    "0d098a5a5cda2e522d9993f47c7b85b733b178843961eefe9cfbeb287fe")

    test_user: User = User.find_by_email_address("test@test.test")

    author = Author.find_by_id(test_user.id)
    if not author:
        print(1)
        author = Author.create(test_user.id)
        team = AuthorTeam.create("The TEST")
        team.courses.append(Course.find_by_id(3))
        team.courses.append(Course.find_by_id(12))
        team.courses.append(Course.find_by_id(13))
        author.teams.append(team)
        db.session.add(author)
        db.session.add(team)
        db.session.commit()

    CourseFilterSession.find_or_create(test_user.id, 0)


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


@app.errorhandler(Exception)
def on_any_exception(error: Exception):
    error_text: str = f"Requested URL: {request.path}\nError: {repr(error)}" + \
                      "".join(format_tb(error.__traceback__)[6:])

    response = send_discord_message(WebhookURLs.ERRORS, f"Server error appeared!\n```{error_text}```")
    if response.status_code < 200 or response.status_code > 299:
        send_file_discord_message(WebhookURLs.ERRORS, error_text, "error_contents.txt", "Server error appeared!")
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
api.add_resource(HelloWorld, "/", )
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
api.add_resource(EmailChanger, "/email-change/")
api.add_resource(PasswordChanger, "/password-change/")

# Adding student's main_page resources:
# api.add_resource(SchoolIntegration, "/school/")
# api.add_resource(Activities, "/activities/")
# api.add_resource(Tasks, "/tasks/<int:task_id>/")
# api.add_resource(Notif, "/notif/<int:notification_id>/")

# Adding education (outside courses) resources:
api.add_resource(FilterGetter, "/filters/")
api.add_resource(CourseLister, "/courses/")
api.add_resource(HiddenCourseLister, "/courses/hidden/")
api.add_resource(CoursePreferences, "/courses/<int:course_id>/preference/")
api.add_resource(CourseReporter, "/courses/<int:course_id>/report/")

# Adding in-course resources:
api.add_resource(CourseMapper, "/courses/<int:course_id>/map/")
api.add_resource(SessionCourseMapper, "/sessions/<int:session_id>/map/")
api.add_resource(ModuleOpener, "/sessions/<int:session_id>/modules/<int:module_id>/")
api.add_resource(Progresser, "/sessions/<int:session_id>/next/")
api.add_resource(Navigator, "/sessions/<int:session_id>/points/<int:point_id>/")
api.add_resource(ContentsGetter, "/sessions/<int:session_id>/contents/")
api.add_resource(TestChecker, "/sessions/<int:session_id>/submit/")

# Adding authorship resources:
api.add_resource(TeamLister, "/cat/teams/")
api.add_resource(OwnedCourseLister, "/cat/courses/owned/")
api.add_resource(OwnedPageLister, "/cat/pages/owned/")
api.add_resource(ReusablePageLister, "/cat/pages/reusable/")

# Adding publishing resources:
api.add_resource(Submitter, "/cat/submissions/")
api.add_resource(SubmissionLister, "/cat/submissions/owned/")
api.add_resource(SubmissionIndexer, "/cat/submissions/index/")
api.add_resource(SubmissionReader, "/cat/submissions/<int:submission_id>/")
api.add_resource(ReviewIndex, "/cat/reviews/<int:submission_id>/")
api.add_resource(Publisher, "/cat/publications/")

# Adding file resource(s):
api.add_resource(PageGetter, "/pages/<int:page_id>/")

# Adding application resource(s):
api.add_resource(Version, "/<app_name>/version/")
api.add_resource(GithubWebhook, "/update/")
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
# curl -v --cookie -X
# curl -H "Content-Type: application/json" http://localhost:5000/settings/
# -X POST -v -d "{\"changed\": {\"username\": \"new\"}}"
# curl "https://qwert45hi.pythonanywhere.com/auth/?email=test@test.test&password=0a989ebc4a77b56a6e2bb7b19d995d185ce440
# 90c13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454" -X POST -v
