from __future__ import annotations

from random import shuffle

from flask_socketio import SocketIOTestClient
from flask.testing import FlaskClient
from pytest import mark

from __lib__.flask_fullstack import dict_equal, check_code

from communities.services.channels_db import ChannelCategory


@mark.order(2000)
def test_channel_categories(client: FlaskClient, socketio_client: SocketIOTestClient):
    def assert_create_category(data: dict):
        create_ack = socketio_client.emit("new-category", data, callback=True)
        create_events = socketio_client.get_received()
        assert len(create_events) == 0
        assert create_ack.get("code") == 200

        result = create_ack.get("data")
        result_id = result.get("id")
        assert isinstance(result_id, int)
        assert dict_equal(result, data, "name", "description")

        return result_id

    def get_communities_list():
        result = check_code(client.get("/home/")).get("communities")
        assert isinstance(result, list)
        return result

    def get_categories_list(entry_id: int):
        result = check_code(
            client.get(f"/communities/{entry_id}/")
        ).get("categories")
        assert isinstance(result, list)
        return result

    community_ids = [d.get("id") for d in get_communities_list()]
    community_data = {"name": "12345", "description": "test"}

    # Assert community creation
    ack = socketio_client.emit("new-community", community_data, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200

    create_data = ack.get("data")
    community_id = create_data.get("id")
    assert isinstance(community_id, int)
    assert dict_equal(create_data, community_data, *community_data.keys())

    community_ids.append(community_id)

    # Check successfully community creation
    found_community = False
    for community in get_communities_list():
        assert community.get("id") in community_ids
        if community.get("id") == community_id:
            assert not found_community
            assert dict_equal(community, community_data, "name", "description")
            found_community = True
    assert found_community

    community_id_json = {"community_id": community_id}

    # Check successfully open category-room
    ack = socketio_client.emit("open-category", community_id_json, callback=True)
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200
    assert ack.get("message") == "Success"

    categories_ids = [d.get("id") for d in get_categories_list(community_id)]
    categories_data = dict(name="cat", description="desc", **community_id_json)
    category_id = assert_create_category(categories_data)
    categories_ids.append(category_id)

    # Check successfully category creation
    found_categories = False
    for category in get_categories_list(community_id):
        assert category.get("id") in categories_ids
        if category.get("id") == category_id:
            assert not found_categories
            assert dict_equal(category, categories_data, "name", "description")
            found_categories = True
    assert found_categories

    # Create categories & check correct sort AL
    category_data_list = [None, 1, 2, 2, None, 1, None, 5, 4, None]
    for category in category_data_list:
        category_data = dict(next_id=category, **categories_data)
        if category is None:
            prev_cat = ChannelCategory.find_by_next_id(
                community_id,
                category,
            ).id
        else:
            prev_cat = ChannelCategory.find_by_id(category).prev_category_id

        category_id = assert_create_category(category_data)
        categories_ids.append(category_id)

        assert ChannelCategory.find_by_id(category_id).prev_category_id == prev_cat
        assert ChannelCategory.find_by_id(category_id).next_category_id == category

    # Check correct update categories
    update_data = dict(category_id=category_id, **community_id_json)
    category_data_list = [
        {},
        {"name": "new_name", "description": "new_description"},
        {"description": "the_newest_description"},
    ]
    for category_update in category_data_list:
        category_update = dict(category_update, **update_data)
        old_data = ChannelCategory.find_by_id(category_id)
        ack = socketio_client.emit("update-category", category_update, callback=True)
        events = socketio_client.get_received()
        assert len(events) == 0
        assert ack.get("code") == 200

        result_data = ack.get("data")
        assert result_data.get("id") == category_id
        assert result_data.get("name") == category_update.get(
            "name"
        ) or old_data.name
        assert result_data.get("description") == category_update.get(
            "description"
        ) or old_data.description

    # Check correct reordering categories
    category_data_list = [
        {"category_id": 2, "next_id": 4},
        {"category_id": 9},
    ]
    for category_move in category_data_list:
        category_move = dict(category_move, **community_id_json)
        category = ChannelCategory.find_by_id(category_move.get("category_id"))
        next_cat = category_move.get("next_id")
        old_prev = category.prev_category_id
        old_next = category.next_category_id
        if next_cat is None:
            prev_cat = ChannelCategory.find_by_next_id(
                community_id,
                next_cat,
            ).id
        else:
            prev_cat = ChannelCategory.find_by_id(next_cat).prev_category_id

        ack = socketio_client.emit("move-category", category_move, callback=True)
        events = socketio_client.get_received()
        assert len(events) == 0
        assert ack.get("code") == 200

        result_data = ack.get("data")
        res_id = result_data.get("id")
        next_id = category_move.get("next_id")
        assert res_id == category_move.get("category_id")
        assert ChannelCategory.find_by_id(res_id).next_category_id == next_id

        if next_id is not None:
            assert ChannelCategory.find_by_id(next_id).prev_category_id == res_id

        assert category.prev_category_id == prev_cat
        assert category.next_category_id == category_move.get("next_id")
        assert ChannelCategory.find_by_id(old_prev).next_category_id == old_next
        assert ChannelCategory.find_by_id(old_next).prev_category_id == old_prev

    # Check correct delete categories
    count = len(categories_ids)
    shuffle(categories_ids)

    for category_id in categories_ids:
        prev_cat = ChannelCategory.find_by_id(category_id).prev_category_id
        next_cat = ChannelCategory.find_by_id(category_id).next_category_id

        ack = socketio_client.emit(
            "delete-category",
            dict(category_id=category_id, **community_id_json),
            callback=True,
        )
        count -= 1
        events = socketio_client.get_received()
        assert len(events) == 0
        assert ack.get("code") == 200
        assert ack.get("message") == "Success"
        assert len(get_categories_list(community_id)) == count

        if prev_cat is not None:
            assert ChannelCategory.find_by_id(
                prev_cat
            ).next_category_id == next_cat
        if next_cat is not None:
            assert ChannelCategory.find_by_id(
                next_cat
            ).prev_category_id == prev_cat

    # Check successfully open category-room
    ack = socketio_client.emit(
        "close-category",
        community_id_json,
        callback=True,
    )
    events = socketio_client.get_received()
    assert len(events) == 0
    assert ack.get("code") == 200
    assert ack.get("message") == "Success"

    # Check out community
    ack = socketio_client.emit(
        "leave-community",
        community_id_json,
        callback=True,
    )
    assert dict_equal(
        ack,
        {"code": 200, "message": "Success"},
        ("code", "message"),
    )
    assert len(socketio_client.get_received()) == 0
