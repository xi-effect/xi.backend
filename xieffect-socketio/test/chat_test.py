from typing import Callable, Iterator

from .conftest import MultiClient, TEST_EMAIL, BASIC_PASS
from .library2 import DoubleClient, Session


def test_the_setup(multi_double_client: MultiClient,
                   list_tester: Callable[[Session, str, dict, int], Iterator[dict]]):
    user: DoubleClient
    with multi_double_client.auth_user(TEST_EMAIL, BASIC_PASS) as user:
        user.sio.emit("add-chat", data={"name": "hey"})
        user.sio.emit("add-chat", data={"name": "hey"})
        user.sio.emit("add-chat", data={"name": "hey"})
        user.sio.emit("add-chat", data={"name": "hey"})
        user.sio.wait_stop()
        print(list(user.sio.new_events()))
        
        for data in list_tester(user.rst, "/chats/index/", {}, 50):
            print(data)
