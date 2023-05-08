from __future__ import annotations

import logging

from discord_webhook import DiscordWebhook
from flask_fullstack import TypeEnum

from common.consts import DISABLE_WEBHOOKS


class WebhookURLs(TypeEnum):
    STATUS = "843500826223312936/9ZcT7YinTBn4g0hdwPL_ca-YszwRUYrNrLhVEPjDrZQw_lMWHeo7l5LNtl6rq4LAUhgv"
    ERRORS = "843536959624445984/-V9-tEd9Af2mz-0L18YQqlabtK4rJatCSs0YS0XUFh-Tl-s49e2DG1Jg0z3wG2Soo0Op"
    WEIRDO = "843431829931556864/XY-k_4IOZ9NVatCuPEYB8OU6_DPSfUBP_lvGROf55g8GTM6TbDarcvLIJiz5KvGOZZZD"
    GITHUB = "854307355347779614/T5F80VykQKj4-5bwgriePYXWpkIDxpP84KMZ5rohRuLOwrsJcyLvchy3pkXwnV0_QNeJ"
    NOTIFY = "854307934233952266/efeU2EMEJvEad9mw45bJscKdX_vMVJE5xYRknfo7bP_BTli_xX7_ubJJBJMjYqKnSHEx"
    HEROKU = "899768347405729892/_-roOKd49JDjD0tPRbY6b0zon469e_KByPL7bakMTBlbEdPxTL0PtqLlIY0fna1B_w3Z"
    NETLIF = "903386251112120360/7WcUs86qDZkjp59PgWQUrbXpFK7ABrNTBc1P1Jopf05BNi05VhoW06oGDrjHAAtdSp3R"
    MAILBT = "994354341202890762/wyqKQiHUdAwbFwNW1MpKrcnH_enD4A7dv7zIRJP4M9cavv5ZBNnx2OSAR6FiORuzR3us"
    LOLBOT = "1005549141730009108/saLOYG8mQXtUk8yLnD-9Vh4Sagr63sgy7SvYSHzmc1-0gjdyqPvqOdapNP0cYW3VvBgg"


def send_file_message(
    webhook_url: WebhookURLs,
    message: str,
    file_content: str | None = None,
    file_name: str = "attachment.txt",
) -> None:
    if DISABLE_WEBHOOKS:
        logging.warning(message)
        if file_content is not None:
            logging.warning(file_content)
        return

    webhook = DiscordWebhook(
        url=f"https://discord.com/api/webhooks/{webhook_url.value}"
    )
    if file_content is not None:
        webhook.add_file(file=file_content, filename=file_name)
    webhook.set_content(message)
    webhook.execute().raise_for_status()


def send_message(webhook_url: WebhookURLs, message: str) -> None:
    send_file_message(webhook_url, message=message)
