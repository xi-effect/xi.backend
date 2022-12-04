from __future__ import annotations

from flask.testing import FlaskClient
from flask_fullstack import check_code, dict_equal
from pytest import mark

from users import generate_code
from ..vault_test import upload


def assert_message(
    client,
    url: str,
    message: str | bool,
    status=200,
    method="POST",
    **kwargs,
):
    assert check_code(
        client.open(url, json=kwargs, method=method), status
    )["a"] == message


@mark.order(30)
def test_feedback(
    base_client: FlaskClient,
    client: FlaskClient,
    mod_client: FlaskClient,
    test_user_id: int,
    list_tester,
):
    base_url, jsons = "/mub/feedback/", ("test-1.json", "test-2.json")
    files = [
        upload(client, filename)[0].get("id") for filename in jsons
    ]
    feedback = {"type": "general", "data": {"lol": "hey"}, "files": files}
    counter: int = len(list(list_tester(base_url, {}, 50, use_post=False)))

    # Check create feedback
    create_data = [
        (None, "Neither the user is authorized, nor the code is provided"),
        ("lol", "Bad code signature"),
        (generate_code(-1), "Code refers to non-existing user"),
        (generate_code(test_user_id), "Success"),
    ]
    for code, message in create_data:
        data = dict(feedback, code=code)
        assert_message(base_client, "/feedback/", message, **data)
        counter += 1 if message == "Success" else 0

    client_data = ["content-report", "bug-report"]
    for feedback_type in client_data:
        data = dict(feedback, type=feedback_type)
        assert_message(client, "/feedback/", "Success", **data)
        counter += 1
    wrong_data = dict(feedback, files=[1, 3, 4])
    assert_message(client, "/feedback/", "Files don't exist", 404, **wrong_data)
    new_list = list(list_tester(base_url, {}, 50, use_post=False))
    assert len(new_list) == counter

    # Check getting feedback list
    base_id, client_id = new_list[0].get("user-id"), new_list[-1].get("user-id")
    dump_data = [
        (base_id, None),
        (client_id, None),
        (None, "general"),
        (None, "content-report"),
        (None, "bug-report"),
    ]
    for user_id, feedback_type in dump_data:
        data = {"user-id": user_id}
        if feedback_type is not None:
            data = dict(data, type=feedback_type)
        feedback_list = list(list_tester(base_url, data, 50, use_post=False))
        result_counter = counter if feedback_type is None else 1
        assert len(feedback_list) == result_counter
    assert_message(client, base_url, "Permission denied", 403, method="GET")

    # Check getting feedback by id
    feedback = new_list[-1]
    assert (feedback_id := feedback.get("id")) is not None
    get_url = f"/mub/feedback/{feedback_id}/"
    feedback_received = check_code(mod_client.get(get_url))
    assert dict_equal(feedback, feedback_received, *feedback_received.keys())
    assert_message(client, get_url, "Permission denied", 403, method="GET")

    # Check deleting feedbacks
    for feedback in new_list:
        assert (feedback_id := feedback.get("id")) is not None
        id_url = f"/mub/feedback/{feedback_id}/"
        assert_message(client, id_url, "Permission denied", 403, method="DELETE")
        assert_message(mod_client, id_url, message=True, method="DELETE")
        assert_message(mod_client, id_url, "Feedback does not exist", 404, method="GET")
        counter -= 1
    assert len(list(list_tester(base_url, {}, 50, use_post=False))) == counter
