from os.path import exists

from api_resources.base.discorder import send_discord_message, WebhookURLs
from main import versions

from github import Github, Repository


def update_available() -> bool:
    if exists(""):
        pass
    return False


def update() -> None:
    github = Github(github_token)
    repo: Repository = github.get_repo(376582002)


def on_restart():
    send_discord_message(WebhookURLs.STATUS, "Application restated\nAPI version is " + versions["API"])
    if update_available():
        update()
