from __future__ import annotations

from flask.testing import FlaskClient
from flask_fullstack import dict_equal, check_code

counter = 0


def assert_user_index(client, code=200, use_post=True, **kwargs):
    global counter
    result = check_code(
        client.open(
            "/mub/users/",
            json=kwargs,
            method="POST" if use_post else "GET",
        ),
        code,
    )

    if code == 403:
        assert result.get("a") == "Permission denied"
    else:
        assert dict_equal(result, kwargs, "username", "email")
        counter += 1
    return result


def test_user_index(
    client: FlaskClient,
    mod_client: FlaskClient,
    list_tester,
):
    global counter

    # Check getting list of users
    user_list = list(list_tester("/mub/users/", {}, 50, use_post=False))
    counter += len(user_list)
    assert_user_index(client, use_post=False, code=403, counter=50, offset=0)

    # Check creating new user
    user_data = {"username": "mub", "password": 123456}
    new_user = assert_user_index(mod_client, **dict(user_data, email="fi@test.mub"))
    assert_user_index(client, code=403, **dict(user_data, email="se@test.mub"))
    assert counter == len(list(list_tester("/mub/users/", {}, 50, use_post=False)))

    # Check email-confirmed update
    old_date = list(
        list_tester(
            "/mub/users/",
            {"username": new_user["username"]},
            50,
            use_post=False,
        )
    )
    update_data = [
        (mod_client, 200, True),
        (client, 403, True),
        (mod_client, 200, False),
    ]
    for client, code, conf in update_data:
        result = check_code(
            client.put(
                f"/mub/users/{new_user['id']}/",
                json={"email-confirmed": conf},
            ),
            code,
        )

        assert isinstance(old_date[0], dict)
        assert old_date[0].get("id") == new_user["id"]

        if code == 403:
            assert result.get("a") == "Permission denied"
        else:
            assert result.get("email-confirmed") == conf
            assert dict_equal(result, old_date[0], "id", "username", "email", "code")
