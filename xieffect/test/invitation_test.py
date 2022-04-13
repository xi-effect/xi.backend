from typing import Iterator, Callable

from flask.testing import FlaskClient

from __lib__.flask_fullstack import check_code


def test_invitation_crud(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    community_creature = check_code(client.post("/communities/", json={"name": "123", "description": "123"}))
    assert community_creature is not False

    invitation_creature = check_code(client.post("/communities/1/invitations/", json={"role": "base", "limit": 2,
                                                                                             "time": 10}))
    assert isinstance(invitation_creature.get("a", False), str)

    assert list_tester("/communities/1/invitations/index/", {}, 20)

    for item in list_tester("/communities/1/invitations/index/", {}, 20):
        code = item["code"]
        assert check_code(client.get(f"/communities/join/{code}/"))

    assert check_code(client.delete("/communities/1/invitations/1/")) == {"a": True}


def test_invitation_join(multi_client: Callable[[str], FlaskClient], client: FlaskClient,
                         list_tester: Callable[[str, dict, int], Iterator[dict]]):
    community_creature = check_code(client.post("/communities/", json={"name": "123", "description": "123"}))
    assert community_creature is not False

    clients = [multi_client(f"{i}@user.user") for i in range(1, 7)]

    invitation_creature = check_code(client.post("/communities/1/invitations/", json={"role": "base", "limit": 2,
                                                                                             "time": 10}))
    assert isinstance(invitation_creature.get("a", False), str)

    code = ""

    for item in list_tester("/communities/1/invitations/index/", {}, 20):
        code = item["code"]

    for i in range(6):
        assert check_code(clients[i].post(f"/communities/join/{code}/"))
