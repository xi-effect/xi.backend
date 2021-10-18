from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from componets import Namespace
from webhooks import send_discord_message, WebhookURLs

github_token: str = ""
github_namespace: Namespace = Namespace("github")


@github_namespace.route("/update/")
class GithubWebhook(Resource):  # [POST] /update/
    parser: RequestParser = RequestParser()
    parser.add_argument("X-GitHub-Event", str, dest="event_type", location="headers")

    @github_namespace.argument_parser(parser)
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


@github_namespace.route("/update-docs/")
class GithubDocumentsWebhook(Resource):  # [POST] /update-docs/
    parser: RequestParser = RequestParser()
    parser.add_argument("X-GitHub-Event", str, dest="event_type", location="headers")

    @github_namespace.argument_parser(parser)
    def post(self, event_type: str):
        if event_type == "push":
            send_discord_message(WebhookURLs.GITHUB, "Documentation has been updated")
