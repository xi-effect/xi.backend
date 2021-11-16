from .conftest import MultiClient, TEST_EMAIL, BASIC_PASS
from .library2 import Client


def test_the_setup(multi_client: MultiClient):
    user: Client
    with multi_client.auth_user(TEST_EMAIL, BASIC_PASS) as user:
        user.emit("add-chat", data={"name": "hey"})
        from time import sleep
        sleep(3)
        print(list(user.new_events()))
