from api_resources.base.checkers import argument_parser
from api_resources.base.discorder import send_discord_message, WebhookURLs

from flask_restful import Resource
from flask_restful.reqparse import RequestParser


class GithubWebhook(Resource):  # /update/
    parser: RequestParser = RequestParser()
    parser.add_argument("id", int)
    parser.add_argument("type", str)
    parser.add_argument("actor", dict)
    parser.add_argument("repo", dict)
    parser.add_argument("payload", dict)

    @argument_parser(parser, ("type", "event_type"))
    def post(self, event_type: str):
        if event_type == "PushEvent":
            pass
        elif event_type == "ReleaseEvent":
            pass
        send_discord_message(WebhookURLs.GITHUB, f"Got a {event_type} notification!")
