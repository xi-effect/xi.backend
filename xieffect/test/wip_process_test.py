from json import load
from typing import Callable, Iterator, Union, Optional

from flask.testing import FlaskClient
from pytest import mark

from xieffect.test.components import check_status_code

PER_REQUEST = 50


# https://discord.com/channels/706806130348785715/843536940083314728/880041704651108432


class WIPRecycler:
    def __init__(self, client: FlaskClient, file_type: str, file_path1: str, file_path2: str,
                 list_tester: Callable[[str, dict, int], Iterator[dict]]):
        self.client: FlaskClient = client
        self.list_tester: Callable[[str, dict, int], Iterator[dict]] = list_tester

        self.file_type: str = file_type
        self.wip_url: str = f"/wip/{self.file_type}"

        self.file_id: Optional[Union[int, str]] = None

        with open(file_path1, "rb") as f:
            self.file_content1 = load(f)  # content shouldn't have any id info!

        with open(file_path2, "rb") as f:
            self.file_content2 = load(f)

    def is_in_list(self, url) -> bool:
        return any(file["id"] == self.file_id for file in self.list_tester(url, {}, PER_REQUEST))

    def creating(self):
        pass

    def editing(self):
        pass

    def publishing(self):
        pass

    def deleting(self):
        pass

    def wip_full_cycle(self):
        self.creating()
        self.editing()
        self.publishing()
        self.deleting()


@mark(200)
def test_pages(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    WIPRecycler(client, "pages", "lululululul", "lululululul", list_tester).wip_full_cycle()


@mark(220)
def test_modules(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    WIPRecycler(client, "modules", "lululululul", "lululululul", list_tester).wip_full_cycle()
