from .conftest import MultiClient, TEST_EMAIL, BASIC_PASS
from .library2 import DoubleClient


def test_the_setup(multi_double_client: MultiClient):
    user: DoubleClient
    with multi_double_client.auth_user(TEST_EMAIL, BASIC_PASS) as user:
        user.sio.emit("add-chat", data={"name": "hey"})
        user.sio.emit("add-chat", data={"name": "hey"})
        user.sio.emit("add-chat", data={"name": "hey"})
        user.sio.emit("add-chat", data={"name": "hey"})
        user.sio.wait_stop()
        print(list(user.sio.new_events()))
