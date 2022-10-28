from __future__ import annotations

from flask.testing import FlaskClient
from flask_fullstack import check_code, dict_equal
from pytest import mark

from .users_mub_test import assert_error

base_url = "/mub/invites/"


@mark.order(50)
def test_mub_invites(client: FlaskClient, mod_client: FlaskClient, list_tester):
    invite_data = {"name": "test", "limit": -1, "accepted": 0}

    # Check getting list of invites
    url, base_status, base_message = f"{base_url}index/", 403, "Permission denied"
    counter = len(list(list_tester(url, {}, 50, use_post=False)))
    assert_error(client, url, base_status, base_message, method="GET", offset=0)

    # Check creating
    new_invite = check_code(mod_client.post(base_url, json=invite_data))
    assert (invite_id := new_invite.get("id")) is not None
    counter += 1
    assert_error(client, base_url, base_status, base_message, **invite_data)
    assert counter == len(list(list_tester(url, {}, 50, use_post=False)))

    # Check getting by id
    id_url = f"{base_url}{invite_id}/"
    invite = check_code(mod_client.get(id_url))
    assert dict_equal(invite, invite_data, *invite_data.keys())
    assert_error(client, id_url, base_status, base_message, method="GET")

    # Check updating invite
    update_data = [("test2", None), ("test3", 5), (None, 15), (None, None)]
    for name, limit in update_data:
        data = dict(name=name, limit=limit)
        old_invite = check_code(mod_client.get(id_url))
        assert check_code(mod_client.put(id_url, json=data))["a"] is True
        changed_invite = check_code(mod_client.get(id_url))
        check_name = name or old_invite.get("name")
        assert changed_invite.get("name") == check_name
        check_limit = limit or old_invite.get("limit")
        assert changed_invite.get("limit") == check_limit
    base_data = {"name": "test2"}
    assert_error(client, id_url, base_status, base_message, method="PUT", **base_data)

    # Check deleting invite
    assert_error(client, id_url, base_status, base_message, method="DELETE")
    assert check_code(mod_client.delete(id_url))["a"] is True
    counter -= 1
    assert_error(mod_client, id_url, 404, "Invite not found", method="GET")
    assert counter == len(list(list_tester(url, {}, 50, use_post=False)))
