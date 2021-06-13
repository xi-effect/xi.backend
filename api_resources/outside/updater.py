from api_resources.base.checkers import argument_parser
from api_resources.base.discorder import send_discord_message, WebhookURLs

from flask_restful import Resource
from flask_restful.reqparse import RequestParser


class GithubWebhook(Resource):  # /update/
    parser: RequestParser = RequestParser()
    parser.add_argument("payload", list)
    parser.add_argument("commits", list)
    parser.add_argument("X-GitHub-Event", str, location="headers")

    @argument_parser(parser, ("X-GitHub-Event", "event_type"), "payload", "commits")
    def post(self, event_type: str, commits: list, payload: dict):
        if event_type == "push":
            version: str = commits[0]["message"]
            send_discord_message(WebhookURLs.WEIRDO, f"{repr(commits)}\n{repr(payload)}")
            send_discord_message(WebhookURLs.STATUS, f"New API version {version} uploaded!")
        elif event_type == "release":
            send_discord_message(WebhookURLs.GITHUB, f"Got a {event_type} notification.\n"
                                                     f"Releases are not supported yet!")
        else:
            send_discord_message(WebhookURLs.GITHUB, f"Got a {event_type} notification.\n"
                                                     f"No action was applied.")
