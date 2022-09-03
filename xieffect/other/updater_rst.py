from __future__ import annotations

from flask import current_app
from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController
from .discorder import send_message as send_discord_message, WebhookURLs

github_token: str = ""
controller = ResourceController("webhooks")


@controller.route("/heroku-build/")
class HerokuBuildWebhook(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("action", str, required=True)
    parser.add_argument("resource", str, required=True)

    @controller.argument_parser(parser)
    @controller.a_response()
    def post(self, resource: str, action: str) -> None:
        send_discord_message(
            WebhookURLs.HEROKU,
            f"Heroku may be online [{resource}:{action}]",
        )


@controller.route("/netlify-build/")
class NetlifyBuildWebhook(Resource):
    arguments = {
        "state": None,
        "error_message": "Error Message",
        "branch": "Branch",
        "title": "Commit Title",
        "committer": "Committer",
        "commit_url": "Commit URL",
    }

    parser: RequestParser = RequestParser()
    for arg_name in arguments.keys():
        parser.add_argument(arg_name, str)

    @controller.argument_parser(parser)
    @controller.a_response()
    def post(self, state: str, commit_url: str, **kwargs) -> None:
        result: str = (
            "__**Netlify build failed!**__\n"
            if state == "error"
            else "__**Netlify build is {state}!**__\n"
        )

        result += "\n".join(
            [
                f"{message}: `{arg}`"
                for name, message in self.arguments.items()
                if (arg := kwargs.get(name, None)) is not None and arg != ""
            ]
        )

        if commit_url is not None:
            result += f"\nCommit URL:\n{commit_url}"

        send_discord_message(WebhookURLs.NETLIF, result)


@controller.route("/pass-through/")
class WebhookPassthrough(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument(
        "Authorization",
        required=True,
        location="headers",
        dest="api_key",
    )
    parser.add_argument(
        "webhook",
        required=True,
        choices=WebhookURLs.get_all_field_names(),
    )
    parser.add_argument(
        "message",
        required=True,
    )

    @controller.argument_parser(parser)
    def post(self, api_key: str, webhook: str, message: str):
        if api_key != current_app.config["API_KEY"]:
            return {"a": "Wrong API_KEY"}, 403
        if (webhook_url := WebhookURLs.from_string(webhook)) is None:
            return {"a": f"Unsupported webhook URL: '{webhook}'"}, 400
        send_discord_message(webhook_url, message)
        return {"a": "Success"}


@controller.route("/lol-bot/")
class LolBot(Resource):
    def get(self):
        try:
            with open("../files/lol-counter.txt", encoding="utf-8") as f:
                count = str(int(f.read()) + 1)
            if "69" in count or count[-1] == "0":
                message = f"Got another one! Total: {count}"
        except (FileNotFoundError, ValueError):
            message = "Reset happened... Got the first one!"
            count = 1

        send_discord_message(WebhookURLs.LOLBOT, message)
        with open("../files/lol-counter.txt", "w", encoding="utf-8") as f:
            f.write(str(count))
