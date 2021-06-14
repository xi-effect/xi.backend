from os import mkdir, environ
from os.path import exists
from json import load
from typing import List

from github import Github, Repository
from github.ContentFile import ContentFile
from requests import post

excluded: List[str] = ["README.md", ".gitignore"]

github_token: str = "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"
domain_name: str = "qwert45hi.pythonanywhere.com"
headers: dict = {"Authorization": f"Token {environ['API_TOKEN']}"}


if __name__ == "__main__":
    github = Github(github_token)
    repo: Repository = github.get_repo(376582002)

    contents: List[ContentFile] = repo.get_contents("")
    content: ContentFile

    for content in contents:
        if content.type == "dir":
            addition = repo.get_contents(content.path)
            mkdir(content.path) if not exists(content.path) else None
            contents.extend(addition) if type(addition) == list else contents.append(addition)
        elif content.path not in excluded:
            with open(content.path, "wb") as f:
                f.write(content.decoded_content)
            print(content.path)

    version: str = load(open("files/versions.json"))["API"]
    post(f"https://discord.com/api/webhooks/843500826223312936/"
         f"9ZcT7YinTBn4g0hdwPL_ca-YszwRUYrNrLhVEPjDrZQw_lMWHeo7l5LNtl6rq4LAUhgv",
         json={"content": f"New API version {version} uploaded.\nRestarting the server."})

    post(f"https://www.pythonanywhere.com/api/v0/user/qwert45hi/webapps/{domain_name}/enable/",
         headers=headers)
