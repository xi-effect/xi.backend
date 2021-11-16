from collections import Callable
from typing import Iterator, Optional

from pytest import fixture
from requests import post

from .components import check_status_code
from .library2 import MultiClient as _MultiClient, Session, AnyClient

TEST_EMAIL: str = "test@test.test"
ADMIN_EMAIL: str = "admin@admin.admin"

BASIC_PASS: str = "0a989ebc4a77b56a6e2bb7b19d995d185ce44090c13e2984b7ecc6d446d4b61ea9991b76a4c2f04b1b4d244841449454"
ADMIN_PASS: str = "2b003f13e43546e8b416a9ff3c40bc4ba694d0d098a5a5cda2e522d9993f47c7b85b733b178843961eefe9cfbeb287fe"


class MultiClient(_MultiClient):
    def auth_user(self, email: str, password: str) -> Optional[AnyClient]:
        response = post(f"{self.server_url}/auth/", json={"email": email, "password": password})
        if response.status_code == 200 and response.json() == {"a": True}:
            header = response.headers["Set-Cookie"]
            return self.connect_user(headers={"Cookie": header})
        return None

    def attach_auth_user(self, username: str, email: str, password: str) -> bool:
        if (client := self.auth_user(email, password)) is not None:
            self.users[username] = client
            return True
        return False


@fixture(scope="session", autouse=True)
def main_server():
    # thr2 = Thread(target=application.run, daemon=True, kwargs={"debug": True})
    # thr2.start()
    s = Session("http://localhost:5000/")
    yield s
    s.close()
    # remove("app.db")


@fixture()
def multi_client(main_server):
    # thr1 = Thread(target=run, daemon=True)
    # thr1.start()
    with MultiClient("http://localhost:5050/") as multi_client:
        yield multi_client


# @fixture()
# def client(multi_client: MultiClient):
#     with multi_client:
#         pass


@fixture
def list_tester(session: Session) -> Callable[[str, dict, int, int], Iterator[dict]]:
    def list_tester_inner(link: str, request_json: dict, page_size: int, status_code: int = 200) -> Iterator[dict]:
        counter = 0
        amount = page_size
        while amount == page_size:
            request_json["counter"] = counter
            response_json: dict = check_status_code(session.post(link, json=request_json), status_code)

            assert "results" in response_json
            assert isinstance(response_json["results"], list)
            for content in response_json["results"]:
                yield content

            amount = len(response_json)
            assert amount <= page_size

            counter += 1

        assert counter > 0

    return list_tester_inner
