from __future__ import annotations

import re
from collections.abc import Callable
from io import BytesIO
from os import remove
from os.path import exists
from typing import Protocol, Any

from flask_fullstack import FlaskTestClient as _FlaskTestClient, SocketIOTestClient
from flask_fullstack.restx.testing import HeaderChecker
from pydantic import constr
from pydantic_marshals.contains.type_aliases import TypeChecker
from pytest import fixture
from pytest_mock import MockerFixture
from werkzeug.datastructures import FileStorage
from werkzeug.test import TestResponse

from common import mail, mail_initialized, Base, db, open_file
from common.users_db import User
from communities.base.discussion_db import Discussion
from communities.base.users_ext_db import CommunitiesUser
from pages.pages_db import Page
from vault.files_db import File, FILES_PATH
from wsgi import application as app, BASIC_PASS, TEST_EMAIL, TEST_MOD_NAME, TEST_PASS


class OpenProtocol(Protocol):
    def __call__(  # copied form ffs!  # noqa: WPS211
        self,
        path: str = "/",
        *args: Any,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
        expected_status: int = 200,
        expected_data: Any | None = None,
        expected_text: str | None = None,
        expected_json: TypeChecker = None,
        expected_a: int | str | type | re.Pattern | None = None,
        expected_headers: HeaderChecker | None = None,
        get_json: bool = True,
        **kwargs: Any,
    ) -> None | dict | list | TestResponse:
        pass


class FlaskTestClient(_FlaskTestClient):
    head: OpenProtocol
    post: OpenProtocol
    get: OpenProtocol
    put: OpenProtocol
    patch: OpenProtocol
    delete: OpenProtocol
    options: OpenProtocol
    trace: OpenProtocol

    def open(  # noqa: A003
        self,
        *args: Any,
        expected_a: TypeChecker = None,
        **kwargs: Any,
    ) -> None | dict | list | TestResponse:
        if expected_a is not None:
            kwargs.setdefault("expected_json", {})["a"] = expected_a
        return super().open(*args, **kwargs)


app.test_client_class = FlaskTestClient


@fixture(scope="session", autouse=True)
def application_context() -> None:
    with app.app_context():
        yield


@fixture
def base_client():
    app.debug = True
    with app.test_client() as client:
        yield client


def base_login(
    client: FlaskTestClient, account: str, password: str, mub: bool = False
) -> None:
    response: TestResponse = client.post(
        "/mub/sign-in/" if mub else "/signin/",
        data={"username" if mub else "email": account, "password": password},
        expected_headers={"Set-Cookie": constr(pattern="access_token_cookie=.*")},
        get_json=False,
    )
    client.set_cookie(
        "test", "access_token_cookie", response.headers["Set-Cookie"].partition("=")[1]
    )


def login(account: str, password: str, mub: bool = False) -> FlaskTestClient:
    client: FlaskTestClient
    with app.test_client() as client:
        base_login(client, account, password, mub)
        return client


@fixture
def client() -> FlaskTestClient:
    return login(TEST_EMAIL, BASIC_PASS)


@fixture
def mod_client() -> FlaskTestClient:
    return login(TEST_MOD_NAME, TEST_PASS, mub=True)


@fixture
def full_client() -> FlaskTestClient:
    test_client = login(TEST_EMAIL, BASIC_PASS)
    base_login(test_client, TEST_MOD_NAME, TEST_PASS, mub=True)
    return test_client


@fixture(scope="session")
def multi_client() -> Callable[[str], FlaskTestClient]:
    def multi_client_inner(user_email: str):
        return login(user_email, BASIC_PASS)

    return multi_client_inner


@fixture
def socketio_client(client: FlaskTestClient) -> SocketIOTestClient:  # noqa: WPS442
    return SocketIOTestClient(client)


@fixture
def mock_mail(mocker: MockerFixture):
    with mail.record_messages() as outbox:
        if not mail_initialized:
            mocker.patch("other.emailer.mail_initialized", side_effect=True)
            mocker.patch("common._core.mail.send", lambda params: outbox.append(params))
        yield outbox


@fixture(scope="session")
def test_user_id() -> int:
    return User.find_by_email_address("test@test.test").id


def delete_by_id(entry_id: int, table: type[Base]) -> None:
    table.delete_by_kwargs(id=entry_id)
    db.session.commit()
    assert table.find_first_by_kwargs(id=entry_id) is None


@fixture
def base_user_data() -> tuple[str, str]:
    return "hey@hey.hey", BASIC_PASS


@fixture
def base_user_id(base_user_data: tuple[str, str]) -> int:
    user_id: int = User.create(
        email=base_user_data[0],
        password=base_user_data[1],
        username="hey",
    ).id
    CommunitiesUser.find_or_create(user_id)  # TODO remove after CU removal
    db.session.commit()
    yield user_id
    delete_by_id(user_id, User)


@fixture
def fresh_client(
    base_user_data: tuple[str, str], base_user_id: int  # noqa: U100
) -> FlaskTestClient:
    return login(*base_user_data)


@fixture
def test_page_data() -> dict[str, str | dict]:
    return {"title": "test", "content": {"test": "content"}}


@fixture
def test_page_id(base_user_id: int, test_page_data: dict[str, str | dict]) -> int:
    page_id: int = Page.create(**test_page_data, creator_id=base_user_id).id
    db.session.commit()
    yield page_id
    delete_by_id(page_id, Page)


def create_file(filename: str, contents: bytes) -> FileStorage:
    return FileStorage(stream=BytesIO(contents), filename=filename)


@fixture
def file_maker(base_user_id: int) -> Callable[File]:
    created: dict[int, str] = {}

    def file_maker_inner(filename: str) -> File:
        with open_file(f"xieffect/test/json/{filename}", "rb") as f:
            contents: bytes = f.read()
        user: User = User.find_first_by_kwargs(id=base_user_id)
        file_storage: FileStorage = create_file(filename, contents)
        file: File = File.create(user, file_storage.filename)
        file_storage.save(FILES_PATH + file.filename)
        created[file.id] = file.filename
        return file

    yield file_maker_inner

    for file_id, name in created.items():
        if exists(FILES_PATH + name):
            remove(FILES_PATH + name)
        delete_by_id(file_id, File)


@fixture
def file(file_maker: Callable[[str], File]) -> File:
    return file_maker("test-1.json")


@fixture
def test_file_id(file_maker: Callable[[str], File]) -> int:
    return file_maker("test-1.json").id


@fixture
def test_discussion_id() -> int:
    discussion_id: int = Discussion.create().id
    yield discussion_id
    delete_by_id(discussion_id, Discussion)


@fixture
def file_id(client: FlaskTestClient) -> int:
    with open_file("xieffect/test/json/test-1.json", "rb") as f:
        contents: bytes = f.read()
    return client.post(
        "/files/",
        content_type="multipart/form-data",
        data={"file": create_file("task-file", contents)},
        expected_json={"id": int},
    )["id"]
