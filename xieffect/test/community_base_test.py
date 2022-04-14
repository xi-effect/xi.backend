from typing import Iterator, Callable

from pytest import mark
from flask.testing import FlaskClient

from __lib__.flask_fullstack import check_code, dict_equal

INVITATIONS_PER_REQUEST = 20


@mark.order(1000)
def test_meta_creation(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    community_data = {"name": "test", "description": "12345"}

    community_data["id"] = check_code(client.post("/communities/", json=community_data)).get("id", None)
    assert community_data["id"] is not None

    for data in list_tester("/communities/index/", {}, 20):
        if dict_equal(data, community_data, "id", "name", "description"):
            break
    else:
        assert False, "Community not found"


@mark.order(1020)
def test_invitations(client: FlaskClient, list_tester: Callable[[str, dict, int], Iterator[dict]]):
    community_data = {"name": "test", "description": "12345"}
    invitation_data = {"role": "base", "limit": 2, "days": 10}

    community_id = check_code(client.post("/communities/", json=community_data)).get("id", None)
    assert community_id is not None

    # check that the invitation list is empty
    assert len(list(list_tester(f"/communities/{community_id}/invitations/index/", {}, INVITATIONS_PER_REQUEST))) == 0

    # create a new invitation
    invitation = check_code(client.post(f"/communities/{community_id}/invitations/", json=invitation_data))
    assert "id" in invitation.keys()
    assert "code" in invitation.keys()

    # check if invitation list was updated
    data = list(list_tester(f"/communities/{community_id}/invitations/index/", {}, INVITATIONS_PER_REQUEST))
    assert len(data) == 1
    assert dict_equal(data[0], invitation, "id", "code")
    assert dict_equal(data[0], invitation_data, "role", "limit")

    # delete invitation & check again
    assert check_code(client.delete(f"/communities/{community_id}/invitations/{invitation['id']}/"))["a"]
    assert len(list(list_tester(f"/communities/{community_id}/invitations/index/", {}, INVITATIONS_PER_REQUEST))) == 0


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
