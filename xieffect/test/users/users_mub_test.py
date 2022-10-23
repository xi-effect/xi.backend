from __future__ import annotations

from flask.testing import FlaskClient
from flask_fullstack import dict_equal, check_code

from wsgi import Invite


def assert_error(
    client,
    url: str,
    status: int,
    message: str,
    code: str = None,
    use_post=True,
    **kwargs,
):
    if code is not None:
        data = dict(kwargs, code=code)
    else:
        data = kwargs
    assert check_code(
        client.open(url, json=data, method="POST" if use_post else "GET"), status
    )["a"] == message


def test_user_index(
    client: FlaskClient,
    mod_client: FlaskClient,
    list_tester,
):
    # Check getting list of users
    url, stat, mess = "/mub/users/", 403, "Permission denied"
    user_list = list(list_tester(url, {}, 50, use_post=False))
    counter = len(user_list)
    assert_error(client, url, stat, mess, use_post=False, counter=50, offset=0)

    # Check creating new user & errors
    invite_code = Invite.serializer.dumps((-1, 0))
    circle_data = [
        ("fi", None, 200, None),
        ("fi", None, 400, "Email already in use"),
        ("se", "wrong.code", 400, "Malformed code (BadSignature)"),
        ("tr", invite_code, 404, "Invite not found"),
    ]
    user_data = {"username": "mub", "password": "123456"}
    for i, code, status, message in circle_data:
        if message is None:
            data = dict(user_data, email=f"{i}@test.mub")
            new_user = check_code(mod_client.post(url, json=data))
            assert dict_equal(new_user, data, "username", "email")
            counter += 1
        else:
            data = dict(user_data, code=code, email=f"{i}@test.mub")
            assert_error(mod_client, url, status, message, **data)
    assert_error(client, url, stat, mess, **dict(user_data, email="fo@test.mub"))
    assert counter == len(list(list_tester("/mub/users/", {}, 50, use_post=False)))

    # Check email-confirmed update
    old_date = list(
        list_tester(url, {"username": new_user["username"]}, 50, use_post=False)
    )
    url = f"/mub/users/{new_user['id']}/"
    for conf in (True, False):
        result = check_code(mod_client.put(url, json={"email-confirmed": conf}))
        assert isinstance(old_date[0], dict)
        assert old_date[0].get("id") == new_user["id"]
        assert result.get("email-confirmed") == conf
        assert dict_equal(result, old_date[0], "id", "username", "email", "code")
