from json import load
from sys import modules

from api import app as application, log_stuff  # noqa
from authorship import Author, Moderator
from componets import with_session
from education import Module, Page
from file_system.keeper import WIPPage
from other.test_keeper import TestPoint
from users import User
from webhooks import WebhookURLs, send_discord_message

TEST_EMAIL: str = "test@test.test"
ADMIN_EMAIL: str = "admin@admin.admin"

if __name__ == "__main__" or "pytest" in modules.keys():  # test only  # pytest here temporarily!!!
    application.debug = True
else:  # works on server restart:
    send_discord_message(WebhookURLs.NOTIF, "Application restated")


@with_session
def init_all(session):
    if (test_user := User.find_by_email_address(session, TEST_EMAIL)) is None:
        log_stuff("status", "Database has been reset")
        test_user: User = User.create(session, TEST_EMAIL, "test", "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c" +
                                      "13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454")
        test_user.author = Author.create(session, test_user)

    if (admin_user := User.find_by_email_address(session, ADMIN_EMAIL)) is None:
        admin_user: User = User.create(session, ADMIN_EMAIL, "admin", "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c" +
                                       "13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454")
        # admin_user.moderator = Moderator.create(session, admin_user)

    Page.create_test_bundle(session, test_user.author)

    with open("../files/tfs/module-bundle.json", encoding="utf-8") as f:
        module_bundle_data = load(f)

    for module_data in module_bundle_data:
        Module.create(session, module_data, test_user.author, force=True)

    WIPPage.create_test_bundle(session, test_user.author)
    TestPoint.test(session)


init_all()

if __name__ == "__main__":  # test only
    application.run()  # (ssl_context="adhoc")
