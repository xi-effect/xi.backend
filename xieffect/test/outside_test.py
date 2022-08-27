from flask.testing import FlaskClient
from flask_mail import Message
from pytest import mark, skip
from werkzeug.test import TestResponse

from __lib__.flask_fullstack import check_code, dict_equal
from common import mail, mail_initialized
from other import EmailType
from users import dumps_feedback, generate_code
from wsgi import Invite, TEST_INVITE_ID
from .conftest import TEST_EMAIL, BASIC_PASS, socketio_client_factory

TEST_CREDENTIALS = {"email": TEST_EMAIL, "password": BASIC_PASS}  # noqa: WPS407


@mark.order(1)
def test_login(base_client: FlaskClient):
    response: TestResponse = check_code(base_client.post("/auth/", json=TEST_CREDENTIALS), get_json=False)
    assert "Set-Cookie" in response.headers
    cookie: tuple[str, str] = response.headers["Set-Cookie"].partition("=")[::2]
    assert cookie[0] == "access_token_cookie"

    result: dict[str, ...] = response.json
    assert result.pop("a", None) == "Success"
    for key in ("communities", "user"):
        assert key in result
    for key in ("id", "username", "dark-theme", "language"):
        assert key in result["user"]

    check_code(base_client.post("/logout/"))


@mark.order(10)
def test_signup(base_client: FlaskClient):
    credentials = {"email": "hey@hey.hey", "password": "12345", "username": "hey"}
    default_data = {"username": credentials["username"], "dark-theme": True, "language": "russian"}

    def assert_with_code(code: str, status: int, message: str):
        assert check_code(base_client.post("/reg/", json=dict(credentials, code=code)), status)["a"] == message

    with mail.record_messages() as outbox:
        # Checking fails
        assert_with_code("hey", 400, "Malformed code (BadSignature)")
        assert_with_code(Invite.serializer.dumps((-1, 0)), 404, "Invite not found")

        assert not mail_initialized or len(outbox) == 0

    # Checking successful reg
    data = dict(credentials, code=Invite.serializer.dumps((TEST_INVITE_ID, 0)))
    response = check_code(base_client.post("/reg/", json=data), get_json=False)

    # Checking for cookies
    assert "Set-Cookie" in response.headers
    cookie: tuple[str, str] = response.headers["Set-Cookie"].partition("=")[::2]
    assert cookie[0] == "access_token_cookie"

    # Checking the returned data
    result: dict[str, ...] = response.json
    assert result.pop("a", None) == "Success"

    communities = result.get("communities", None)
    assert isinstance(communities, list)
    assert len(communities) == 0

    user = result.get("user", None)
    assert isinstance(user, dict)
    assert dict_equal(user, default_data, *default_data.keys())
    assert "id" in user

    # Check the /home/ as well
    response = check_code(base_client.get("/home/"))
    assert response == result

    check_code(base_client.post("/logout/"))


@mark.order(12)
def test_email_confirm(base_client: FlaskClient):
    if not mail_initialized:
        skip("Email module is not setup")

    a = [1, 2, 3, 4]
    assert 1 in a

    # TODO use hey@hey.hey but delete account form test_signup (& here)
    credentials = {
        "email": "hey2@hey.hey",
        "password": "12345",
        "username": "hey",
        "code": Invite.serializer.dumps((TEST_INVITE_ID, 0))
    }
    link_start = "https://xieffect.ru/email/"

    with mail.record_messages() as outbox:
        assert check_code(base_client.post("/reg/", json=credentials))["a"] == "Success"

        assert len(outbox) == 1
        message: Message = outbox[0]
        assert message.subject == EmailType.CONFIRM.theme
        assert link_start in message.html

        code = message.html.partition(link_start)[2].partition('/"')[0]
        assert code != ""

        recipients = message.recipients
        assert len(recipients) == 1
        assert recipients[0] == credentials["email"]

    assert check_code(base_client.get("/settings/")).get("email-confirmed", None) is False
    assert check_code(base_client.post(f"/email-confirm/{code}/"))["a"] == "Success"
    assert check_code(base_client.get("/settings/")).get("email-confirmed", None) is True

    check_code(base_client.post("/logout/"))


@mark.order(15)
def test_sio_connection(client: FlaskClient):
    sio_client = socketio_client_factory(client)
    assert sio_client.connected.get("/", None) is True


@mark.order(16)
def test_sio_unauthorized(base_client: FlaskClient):
    sio_client = socketio_client_factory(base_client)
    assert sio_client.connected.get("/", None) is False


def assert_feedback(client: FlaskClient, data: dict, a: str):
    assert check_code(client.post("/feedback/", json=data))["a"] == a


@mark.order(30)
def test_feedback(base_client: FlaskClient, client: FlaskClient):  # assumes user_id=1 (test) exists, user_id=-1 doesn't
    feedback = {"type": "general", "data": {"lol": "hey"}}

    assert_feedback(base_client, feedback, "Neither the user is authorized, nor the code is provided")
    assert_feedback(base_client, dict(feedback, code="lol"), "Bad code signature")
    assert_feedback(base_client, dict(feedback, code=generate_code(-1)), "Code refers to non-existing user")
    assert_feedback(base_client, dict(feedback, code=generate_code(1)), "Success")
    assert_feedback(client, feedback, "Success")

    result = dumps_feedback()
    assert len(result) == 2
    result[0].pop("id")
    result[1].pop("id")
    assert result[0] == result[1]
    assert dict_equal(result[0], feedback, "data", "type")


@mark.order(50)
def test_invite_curds(client: FlaskClient, admin_client: FlaskClient):
    def request_assert_admin(method, url: str, json=None):
        assert check_code(method(client, url, json=json), 403)["a"] == "Permission denied"
        return check_code(method(admin_client, url, json=json))

    invite_data = {"name": "test", "limit": -1, "accepted": 0}
    invite_data2 = {"name": "toast", "limit": 5, "accepted": 0}

    assert (invite_id := request_assert_admin(FlaskClient.post, "/invites/", invite_data).get("id", None)) is not None
    result = request_assert_admin(FlaskClient.get, f"/invites/{invite_id}/")
    assert dict_equal(result, invite_data, "name", "limit", "accepted")
    invite_data2["code"] = result["code"]

    results = request_assert_admin(FlaskClient.post, "/invites/index/", {"offset": 0})["results"]
    assert any(invite == result for invite in results), results

    assert request_assert_admin(FlaskClient.put, f"/invites/{invite_id}/", invite_data2)
    result = request_assert_admin(FlaskClient.get, f"/invites/{invite_id}/")
    assert dict_equal(result, invite_data2, "name", "limit", "accepted", "code")

    results = request_assert_admin(FlaskClient.post, "/invites/index/", {"offset": 0})["results"]
    assert any(invite == result for invite in results), results

    assert request_assert_admin(FlaskClient.delete, f"/invites/{invite_id}/")["a"]
    assert check_code(admin_client.get(f"/invites/{invite_id}/"), 404)["a"] == "Invite not found"

    results = request_assert_admin(FlaskClient.post, "/invites/index/", {"offset": 0})["results"]
    assert not any(invite == result for invite in results), results
