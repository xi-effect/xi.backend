from typing import Iterator, Callable

from flask.testing import FlaskClient
from flask_socketio import SocketIOTestClient
from pytest import mark

from __lib__.flask_fullstack import check_code, dict_equal

INVITATIONS_PER_REQUEST = 20


@mark.order(1000)
def test_meta_creation(client: FlaskClient, socketio_client: SocketIOTestClient,
                       list_tester: Callable[[str, dict, int], Iterator[dict]]):
    community_ids = [d["id"] for d in list_tester("/communities/index/", {}, 20)]

    # RST variant
    community_data1 = {"name": "test", "description": "12345"}

    community_id1 = check_code(client.post("/communities/", json=community_data1)).get("id", None)
    assert isinstance(community_id1, int)
    community_ids.append(community_id1)

    # SIO variant
    community_data2 = {"name": "12345", "description": "test"}

    socketio_client.emit("create-community", community_data2)
    events = socketio_client.get_received()
    assert len(events) == 1
    assert events[0]["name"] == "create-community"
    assert len(events[0]["args"]) == 1

    community_id2 = events[0]["args"][0].get("id", None)
    assert isinstance(community_id2, int)
    community_ids.append(community_id2)

    # Checking
    def check_find(data, community_id, community_data, found) -> bool:
        if data["id"] == community_id:
            assert not found
            assert dict_equal(data, community_data, "name", "description")
            return True
        return False

    found1, found2 = False, False

    for data in list_tester("/communities/index/", {}, 20):
        assert data["id"] in community_ids
        found1 = check_find(data, community_id1, community_data1, found1)
        found2 = check_find(data, community_id2, community_data2, found2)


@mark.order(1020)  # TODO redo with sio
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


@mark.order(1025)  # TODO redo with sio
def test_invitation_joins(multi_client: Callable[[str], FlaskClient],
                          list_tester: Callable[[str, dict, int], Iterator[dict]]):
    community_data = {"name": "test", "description": "12345"}

    # functions
    def create_invitation(invitation_data, skip_id: bool = False):
        invitation = check_code(anatol.post(f"/communities/{community_id}/invitations/", json=invitation_data))
        assert "id" in invitation.keys()
        assert "code" in invitation.keys()

        if skip_id:
            return invitation["code"]
        return invitation["id"], invitation["code"]

    def assert_fail_join(client: FlaskClient, code: str, reason: str = "Invalid invitation"):
        assert check_code(client.get(f"/communities/join/{code}/"), 400)["a"] == reason
        assert check_code(client.post(f"/communities/join/{code}/"), 400)["a"] == reason

    def assert_successful_join(client: FlaskClient, invitation_id: int, code: str):
        for data in list_tester(f"/communities/{community_id}/invitations/index/", {}, INVITATIONS_PER_REQUEST):
            if data["id"] == invitation_id:
                limit_before = data.get("limit", None)
                break
        else:
            assert False, "Invitation not found inside assert_successful_join"

        assert dict_equal(check_code(client.get(f"/communities/join/{code}/")), community_data, *community_data.keys())
        assert dict_equal(check_code(client.post(f"/communities/join/{code}/")), community_data, *community_data.keys())

        if limit_before is None:
            return
        for data in list_tester(f"/communities/{community_id}/invitations/index/", {}, INVITATIONS_PER_REQUEST):
            if data["id"] == invitation_id:
                assert data["limit"] == limit_before - 1
                break
        else:
            assert limit_before == 1

    anatol = multi_client("1@user.user")
    vasil1 = multi_client("2@user.user")
    vasil2 = multi_client("3@user.user")
    vasil3 = multi_client("4@user.user")

    community_id = check_code(anatol.post("/communities/", json=community_data)).get("id", None)
    assert community_id is not None

    # testing joining & errors
    invitation_id1, code1 = create_invitation({"role": "base"})
    assert_fail_join(vasil1, "hey")
    assert_fail_join(anatol, code1, "User has already joined")
    assert_successful_join(vasil1, invitation_id1, code1)
    assert_fail_join(vasil1, code1, "User has already joined")

    # testing counter limit
    invitation_id2, code2 = create_invitation({"role": "base", "limit": 1})
    assert_fail_join(vasil1, code2, "User has already joined")
    assert_successful_join(vasil2, invitation_id2, code2)
    assert_fail_join(vasil2, code2)  # , "User has already joined")
    assert_fail_join(vasil3, code2)

    # testing time limit
    _, code3 = create_invitation({"role": "base", "days": 0})
    assert_fail_join(vasil1, code3, "User has already joined")
    assert_fail_join(vasil2, code3, "User has already joined")
    assert_fail_join(vasil3, code3)

    # testing creating permissions errors
    message = check_code(vasil1.post(f"/communities/{community_id}/invitations/", json={"role": "base"}), 403)["a"]
    assert message == "Permission Denied: Low role"
    message = check_code(vasil3.post(f"/communities/{community_id}/invitations/", json={"role": "base"}), 403)["a"]
    assert message == "Permission Denied: Participant not found"

    # testing deleted invite
    assert check_code(anatol.delete(f"/communities/{community_id}/invitations/{invitation_id1}/"))["a"]
    assert_fail_join(vasil1, code1)  # , "User has already joined")
    assert_fail_join(vasil2, code1)  # , "User has already joined")
    assert_fail_join(vasil3, code1)
