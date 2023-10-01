from __future__ import annotations

from pytest import mark, fixture, param

from common import open_file
from test.conftest import delete_by_id, FlaskTestClient
from test.vault_test import create_file, upload
from users import generate_code
from users.feedback_db import Feedback, FeedbackType
from users.users_db import User
from vault.files_db import File


@fixture()
def feedback_files(client: FlaskTestClient) -> list[tuple[dict, bytes]]:
    return [
        upload(client, filename)[0].get("id")
        for filename in ("test-1.json", "test-2.json")
    ]


@fixture()
def default_feedback(feedback_files) -> dict:
    return {"type": "general", "data": {"lol": "hey"}, "files": feedback_files}


@mark.parametrize(
    ("code", "message"),
    [
        param(
            None,
            "Neither the user is authorized, nor the code is provided",
            id="no_code",
        ),
        param("lol", "Bad code signature", id="bad_signature"),
        param(generate_code(-1), "Code refers to non-existing user", id="bad_user"),
    ],
)
def test_fail_creating_feedback(
    base_client: FlaskTestClient,
    default_feedback: dict,
    code: str | None,
    message: str,
):
    data = dict(default_feedback, code=code)
    base_client.post("/feedback/", expected_a=message, json=data)


@mark.order(30)
def test_feedback(
    base_client: FlaskTestClient,
    client: FlaskTestClient,
    mod_client: FlaskTestClient,
    default_feedback: dict,
    test_user_id: int,
):
    base_url = "/mub/feedback/"
    counter: int = len(list(mod_client.paginate(base_url)))

    # Check create feedback
    data = dict(default_feedback, code=generate_code(test_user_id))
    base_client.post("/feedback/", expected_a="Success", json=data)
    counter += 1

    for feedback_type in ("content-report", "bug-report"):
        data = dict(default_feedback, type=feedback_type)
        client.post("/feedback/", expected_a="Success", json=data)
        counter += 1

    wrong_data = dict(default_feedback, files=[1, 3, 4])
    client.post(
        "/feedback/",
        expected_a="Files don't exist",
        expected_status=404,
        json=wrong_data,
    )

    new_list = list(mod_client.paginate(base_url))
    assert len(new_list) == counter

    # Check getting feedback list
    base_id = new_list[0].get("user-id")
    client_id = new_list[-1].get("user-id")
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
        feedback_list = list(mod_client.paginate(base_url, json=data))
        result_counter = counter if feedback_type is None else 1
        assert len(feedback_list) == result_counter
    client.get(base_url, expected_a="Permission denied", expected_status=403)

    # Check getting feedback by id
    feedback = new_list[-1]
    feedback_id: int | None = feedback.get("id")
    assert feedback_id is not None
    get_url = f"/mub/feedback/{feedback_id}/"
    mod_client.get(get_url, expected_json=feedback)
    client.get(get_url, expected_a="Permission denied", expected_status=403)

    # Check deleting feedbacks
    for feedback in new_list:
        feedback_id: int | None = feedback.get("id")
        assert feedback_id is not None
        id_url = f"/mub/feedback/{feedback_id}/"
        client.delete(id_url, expected_a="Permission denied", expected_status=403)
        mod_client.delete(id_url, expected_a=True)
        mod_client.delete(
            id_url, expected_a="Feedback does not exist", expected_status=404
        )
        counter -= 1

    assert counter == 0
    assert len(list(mod_client.paginate(base_url))) == 0


def test_feedback_constraints(base_user_id: int):
    with open_file("xieffect/test/json/test-1.json", "rb") as f:
        contents: bytes = f.read()
    file_storage = create_file("test-1.json", contents)
    user = User.find_by_id(base_user_id)
    file_id = File.create(user, file_storage.filename).id
    feedback_id = Feedback.create(
        user_id=base_user_id, type=FeedbackType.GENERAL, data={"lol": "hey"}
    ).id
    assert isinstance(feedback_id, int)
    assert isinstance(file_id, int)
    assert File.find_by_id(file_id) is not None
    assert Feedback.find_by_id(feedback_id) is not None

    delete_by_id(base_user_id, User)
    assert File.find_by_id(file_id) is None
    assert Feedback.find_by_id(feedback_id) is None
