from flask.testing import FlaskClient
from typing import Iterator, Callable
from .components import check_status_code


def test_invitation_create(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    community_creature = check_status_code(client.post("/communities/", json={"name": "123", "description": "123"}))
    assert community_creature is not None

    id = 1
    for i in range(5):
        assert check_status_code(client.post(f"/communities/{id}/invitations/", json={"role": "base", "limit": "2", "time": "10"}))

    assert list_tester(f"/communities/{id}/invitations/index/", {}, 20)


def test_invitation_delete(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    community_creature = check_status_code(client.post("/communities/", json={"name": "123", "description": "123"}))
    assert community_creature is not None

    id = 1
    for i in range(5):
        assert check_status_code(client.post(f"/communities/{id}/invitations/", json={"role": "base", "limit": "2", "time": "10"}))

    assert check_status_code(client.delete("/communities/1/invitations/1/")) == {"a": True}


def test_invitation_get_communities_info(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    community_creature = check_status_code(client.post("/communities/", json={"name": "123", "description": "123"}))
    assert community_creature is not None

    id = 1
    for i in range(5):
        assert check_status_code(client.post(f"/communities/{id}/invitations/", json={"role": "base", "limit": "2", "time": "10"}))

    for item in list_tester(f"/communities/{id}/invitations/index/", {}, 20):
        code = item["code"]
        assert check_status_code(client.get(f"/communities/join/{code}/"))


def test_invitation_join(multi_client: Callable[[str], FlaskClient], client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    community_creature = check_status_code(client.post("/communities/", json={"name": "123", "description": "123"}))
    assert community_creature is not None

    client1: FlaskClient = multi_client("1@user.user")
    client2: FlaskClient = multi_client("2@user.user")
    client3: FlaskClient = multi_client("3@user.user")
    client4: FlaskClient = multi_client("4@user.user")
    client5: FlaskClient = multi_client("5@user.user")
    client6: FlaskClient = multi_client("6@user.user")

    client_mas = [client1, client2, client3, client4, client5, client6]

    id = 1
    assert check_status_code(client.post(f"/communities/{id}/invitations/", json={"role": "base", "limit": "3", "time": "10"}))

    code = ""

    for item in list_tester(f"/communities/{id}/invitations/index/", {}, 20):
        code = item["code"]

    for i in range(6):
        assert check_status_code(client.post(f"/communities/join/{code}/"))




