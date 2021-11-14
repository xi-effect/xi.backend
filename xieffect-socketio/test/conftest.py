from requests import post
from pytest import fixture
from threading import Thread

from .library2 import MultiClient as _MultiClient
from run import run
from xieffect.wsgi import application


class MultiClient(_MultiClient):
    def auth_user(self, username: str, email: str, password: str) -> bool:
        response = post("https://xieffect.pythonanywhere.com/auth/", json={"email": email, "password": password})
        if response.status_code == 200 and response.json() == {"a": "Success"}:
            header = response.headers["Set-Cookie"]
            self.attach_user(username, headers={"Cookie": header})
            return True
        return False


@fixture()
def multi_client():
    thr1 = Thread(target=run, daemon=True)
    thr1.start()
    thr2 = Thread(target=application.run, daemon=True, kwargs={"debug": True})
    thr2.start()
    with MultiClient("http://localhost:5050/") as multi_client:
        yield multi_client
