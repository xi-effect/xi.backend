from __future__ import annotations

from pytest import mark

from test.conftest import FlaskTestClient


@mark.order(50)
def test_mub_invites(client: FlaskTestClient, mod_client: FlaskTestClient):
    base_url = "/mub/invites/"
    invite_data = {"name": "test", "limit": -1, "accepted": 0}

    # Check getting list of invites
    counter: int = len(list(mod_client.paginate(base_url)))
    client.get(
        base_url,
        expected_status=403,
        expected_a="Permission denied",
        json={"offset": 0},
    )

    # Check creating
    invite_id = mod_client.post(
        base_url,
        json=invite_data,
        expected_json={"id": int},
    )["id"]
    counter += 1
    client.post(
        base_url,
        expected_status=403,
        expected_a="Permission denied",
        json=invite_data,
    )
    assert counter == len(list(mod_client.paginate(base_url)))

    # Check getting by id
    id_url = f"{base_url}{invite_id}/"
    mod_client.get(id_url, expected_json=invite_data)
    client.get(id_url, expected_status=403, expected_a="Permission denied")

    # Check updating invite
    update_data = [("test2", None), ("test3", 5), (None, 15), (None, None)]
    for name, limit in update_data:
        old_invite = mod_client.get(id_url)
        mod_client.put(id_url, json={"name": name, "limit": limit}, expected_a=True)
        mod_client.get(
            id_url,
            expected_json={
                "name": name or old_invite.get("name"),
                "limit": limit or old_invite.get("limit"),
            },
        )
    base_data = {"name": "test2"}
    client.put(
        id_url, expected_status=403, expected_a="Permission denied", json=base_data
    )

    # Check deleting invite
    client.delete(id_url, expected_status=403, expected_a="Permission denied")
    mod_client.delete(id_url, expected_a=True)
    counter -= 1
    mod_client.get(id_url, expected_status=404, expected_a="Invite not found")
    assert counter == len(list(mod_client.paginate(base_url)))
