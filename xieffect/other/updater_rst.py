from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController
from .discorder import send_message as send_discord_message, WebhookURLs

github_token: str = ""
controller = ResourceController("webhooks")


@controller.route("/update/")
class GithubWebhook(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("X-GitHub-Event", str, dest="event_type", location="headers")

    @controller.argument_parser(parser)
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


@controller.route("/update-docs/")
class GithubDocumentsWebhook(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("X-GitHub-Event", str, dest="event_type", location="headers")

    @controller.argument_parser(parser)
    def post(self, event_type: str):
        if event_type == "push":
            send_discord_message(WebhookURLs.GITHUB, "Documentation has been updated")


@controller.route("/heroku-build/")
class HerokuBuildWebhook(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("action", str, required=True)
    parser.add_argument("resource", str, required=True)

    @controller.argument_parser(parser)
    @controller.a_response()
    def post(self, resource: str, action: str) -> None:
        send_discord_message(WebhookURLs.HEROKU, f"Heroku may be online [{resource}:{action}]")


@controller.route("/netlify-build/")
class NetlifyBuildWebhook(Resource):
    arguments = {
        "state": None,
        "error_message": "Error Message",
        "branch": "Branch",
        "title": "Commit Title",
        "committer": "Committer",
        "commit_url": "Commit URL"
    }

    parser: RequestParser = RequestParser()
    for arg_name in arguments.keys():
        parser.add_argument(arg_name, str)

    @controller.argument_parser(parser)
    @controller.a_response()
    def post(self, state: str, commit_url: str, **kwargs) -> None:
        result: str = (f"__**Netlify build failed!**__\n" if state == "error" else
                       f"__**Netlify build is {state}!**__\n")

        result += "\n".join([
            f"{message}: `{arg}`"
            for name, message in self.arguments.items()
            if (arg := kwargs.get(name, None)) is not None and arg != ""
        ])

        if commit_url is not None:
            result += f"\nCommit URL:\n{commit_url}"

        send_discord_message(WebhookURLs.NETLIF, result)


@controller.route("/pass-through/")
class WebhookPassthrough(Resource):
    parser: RequestParser = RequestParser()
    parser.add_argument("Authorization", required=True, location="headers", dest="api_key")
    parser.add_argument("webhook", required=True, choices=WebhookURLs.get_all_field_names())
    parser.add_argument("message", required=True)

    from api import app

    @controller.argument_parser(parser)
    def post(self, api_key: str, webhook: str, message: str):
        if api_key != self.app.config["API_KEY"]:
            return {"a": "Wrong API_KEY"}, 403
        if (webhook_url := WebhookURLs.from_string(webhook)) is None:
            return {"a": f"Unsupported webhook URL: '{webhook}'"}, 400
        send_discord_message(webhook_url, message)


@controller.route("/lol-bot/")
class WebhookPassthrough(Resource):
    def get(self):
        try:
            with open("../files/lol-counter.txt") as f:
                count = str(int(f.read()) + 1)
            if "69" in count or count.count("0") == len(count) - 1:
                send_discord_message(WebhookURLs.LOLBOT, f"Got another one! Total: {count}")
        except (FileNotFoundError, ValueError):
            send_discord_message(WebhookURLs.LOLBOT, f"Reset happened... Got the first one!")
            count = 1
        with open("../files/lol-counter.txt", "w") as f:
            f.write(str(count))
