from api_resources.base.checkers import argument_parser
from webhooks import send_discord_message, WebhookURLs, execute_in_console, disable_webapp

from flask_restful import Resource
from flask_restful.reqparse import RequestParser

github_token: str = ""


class GithubWebhook(Resource):  # /update/
    parser: RequestParser = RequestParser()
    parser.add_argument("X-GitHub-Event", str, location="headers")

    @argument_parser(parser, ("X-GitHub-Event", "event_type"))
    def post(self, event_type: str):
        if event_type == "push":
            send_discord_message(WebhookURLs.GITHUB, f"Got a push notification.\n"
                                                     f"Starting auto-update")
            execute_in_console("python updater.py")
            disable_webapp()
        elif event_type == "release":
            send_discord_message(WebhookURLs.GITHUB, f"Got a release notification.\n"
                                                     f"Releases are not supported yet!")
        else:
            send_discord_message(WebhookURLs.GITHUB, f"Got a {event_type} notification.\n"
                                                     f"No action was applied.")


class GithubDocumentsWebhook(Resource):  # /update/
    parser: RequestParser = RequestParser()
    parser.add_argument("X-GitHub-Event", str, location="headers")

    @argument_parser(parser, ("X-GitHub-Event", "event_type"))
    def post(self, event_type: str):
        if event_type == "push":
            send_discord_message(WebhookURLs.GITHUB, "Documentation has been updated")
