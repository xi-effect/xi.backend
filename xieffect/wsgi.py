from api import app as application  # noqa
from webhooks import WebhookURLs, send_discord_message

# works on restart:
send_discord_message(WebhookURLs.NOTIF, "Application restated")
