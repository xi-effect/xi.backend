from __future__ import annotations

from flask import current_app
from flask_fullstack import RequestParser
from flask_restx import Resource

from common import ResourceController, open_file
from .discorder import send_message as send_discord_message, WebhookURLs

github_token: str = ""
controller = ResourceController("webhooks")


@controller.route("/resume/")
class SendResume(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("name", str, required=True)
    parser.add_argument("tg", str, required=True)
    parser.add_argument("position", str, required=True)
    parser.add_argument("link", str, required=True)
    parser.add_argument("message", str, required=False)

    @controller.argument_parser(parser)
    @controller.a_response()
    def post(
        self,
        name: str,
        tg: str,
        position: str,
        link: str,
        message: str,
    ) -> None:
        send_discord_message(
            WebhookURLs.GALINA,
            f"**Новый отклик на вакансию {position}**\n"
            f"- Имя: {name}\n"
            f"- Телеграм: {tg}\n"
            f"- [Резюме](<{link}>)\n"
            f">>> {message}",
        )


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
        "branch": "Branch",
        "title": "Title",
        "committer": "Author",
        "commit_url": "URL",
    }

    parser: RequestParser = RequestParser()
    for arg_name in arguments.keys():
        parser.add_argument(arg_name, str)

    @controller.argument_parser(parser)
    @controller.a_response()
    def post(self, state: str, commit_url: str, **kwargs) -> None:
        result: list[str] = [
            "__**Netlify build failed!**__"
            if state == "error"
            else f"__**Netlify build is {state}!**__"
        ]

        result.extend(
            f"{message}: `{arg}`"
            for name, message in self.arguments.items()
            if (arg := kwargs.get(name)) is not None and arg != ""
        )

        if commit_url is not None:
            result.append(f"{commit_url}")

        send_discord_message(WebhookURLs.NETLIF, "\n".join(result))


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
        type=WebhookURLs.as_input(),
    )
    parser.add_argument(
        "message",
        required=True,
    )

    @controller.argument_parser(parser)
    def post(self, api_key: str, webhook: WebhookURLs, message: str):
        if api_key != current_app.config["API_KEY"]:
            return {"a": "Wrong API_KEY"}, 403
        send_discord_message(webhook, message)
        return {"a": "Success"}


@controller.route("/lol-bot/")
class LolBot(Resource):
    def get(self):
        message: str | None = None
        try:
            with open_file("files/lol-counter.txt") as f:
                count = str(int(f.read()) + 1)
            if "69" in count or count[-1] == "0":
                message = f"Got another one! Total: {count}"
        except (FileNotFoundError, ValueError):
            message = "Reset happened... Got the first one!"
            count = 1

        if message is not None:
            send_discord_message(WebhookURLs.LOLBOT, message)
        with open_file("files/lol-counter.txt", "w") as f:
            f.write(str(count))
