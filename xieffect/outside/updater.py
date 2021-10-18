from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import Namespace
from webhooks import send_discord_message, WebhookURLs

github_token: str = ""
webhook_namespace: Namespace = Namespace("webhooks")


@webhook_namespace.route("/update/")
class GithubWebhook(Resource):  # [POST] /update/
    parser: RequestParser = RequestParser()
    parser.add_argument("X-GitHub-Event", str, dest="event_type", location="headers")

    @webhook_namespace.argument_parser(parser)
    def post(self, event_type: str):
        if event_type == "push":
            send_discord_message(WebhookURLs.GITHUB, f"Got a push notification.\n"
                                                     f"Starting auto-update")
            # execute_in_console("git pull")
            # reload_webapp()
        elif event_type == "release":
            send_discord_message(WebhookURLs.GITHUB, f"Got a release notification.\n"
                                                     f"Releases are not supported yet!")
        else:
            send_discord_message(WebhookURLs.GITHUB, f"Got a {event_type} notification.\n"
                                                     f"No action was applied.")


@webhook_namespace.route("/update-docs/")
class GithubDocumentsWebhook(Resource):  # [POST] /update-docs/
    parser: RequestParser = RequestParser()
    parser.add_argument("X-GitHub-Event", str, dest="event_type", location="headers")

    @webhook_namespace.argument_parser(parser)
    def post(self, event_type: str):
        if event_type == "push":
            send_discord_message(WebhookURLs.GITHUB, "Documentation has been updated")


@webhook_namespace.route("/heroku-build/")
class HerokuBuildWebhook(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("action", str, required=True)
    parser.add_argument("resource", str, required=True)

    @webhook_namespace.a_response()
    @webhook_namespace.argument_parser(parser)
    def post(self, resource: str, action: str) -> None:
        send_discord_message(WebhookURLs.HEROKU, f"Heroku may be online [{resource}:{action}]")
