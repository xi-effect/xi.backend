from __future__ import annotations

import re
from collections.abc import Callable
from typing import Protocol, Any

from flask_fullstack import (
    FlaskTestClient as _FlaskTestClient,
    SocketIOTestClient,
    TypeChecker,
)
from flask_fullstack.restx.testing import HeaderChecker
from pydantic import constr
from pytest import fixture
from pytest_mock import MockerFixture
from werkzeug.test import TestResponse

from common import User, mail, mail_initialized, Base, db
from communities.base import CommunitiesUser
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
        expected_json: TypeChecker | None = None,
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
        expected_a: TypeChecker | None = None,
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
        expected_headers={"Set-Cookie": constr(regex="access_token_cookie=.*")},
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


@fixture
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
def base_user_id(base_user_data) -> int:
    user_id = User.create(
        email=base_user_data[0],
        password=base_user_data[1],
        username="hey",
    ).id
    CommunitiesUser.find_or_create(user_id)  # TODO remove after CU removal
    db.session.commit()
    yield user_id
    delete_by_id(user_id, User)


@fixture
def fresh_client(base_user_data, base_user_id) -> FlaskTestClient:  # noqa: U100
    return login(*base_user_data)
