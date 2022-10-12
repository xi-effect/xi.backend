from __future__ import annotations

from random import shuffle, choice

from common.testing import SocketIOTestClient
from flask.testing import FlaskClient
from pytest import mark

from __lib__.flask_fullstack import dict_equal, check_code

from communities.services.channels_db import Channel, ChannelType


@mark.order(2010)
def test_channel_categories(client: FlaskClient, socketio_client: SocketIOTestClient):
    def assert_create_channel(data: dict):
        result = socketio_client.assert_emit_ack("new-channel", data)
        result_id = result.get("id")
        assert isinstance(result_id, int)
        assert result["name"] == data["name"]
        assert result["type"] == data["type"].lower()
        return result_id

    def get_communities_list():
        result = check_code(client.get("/home/")).get("communities")
        assert isinstance(result, list)
        return result

    def get_channels_list(entry_id: int):
        result = check_code(
            client.get(f"/communities/{entry_id}/")
        ).get("channels")
        assert isinstance(result, list)
        return result

    community_ids = [d.get("id") for d in get_communities_list()]
    community_data = {"name": "12345", "description": "test"}

    # Assert community creation
    create_data = socketio_client.assert_emit_ack("new-community", community_data)
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

    # Check successfully open channel-room
    socketio_client.assert_emit_success("open-channel", community_id_json)

    # Assert channel creation
    channels_ids = [d.get("id") for d in get_channels_list(community_id)]
    channels_data = dict(name="chan", type="NEWS", **community_id_json)
    channel_id = assert_create_channel(channels_data)
    channels_ids.append(channel_id)

    # Check successfully channel creation
    found_channels = False
    for channel in get_channels_list(community_id):
        assert channel.get("id") in channels_ids
        if channel.get("id") == channel_id:
            assert not found_channels
            assert channel["name"] == channels_data["name"]
            assert channel["type"] == channels_data["type"].lower()
            found_channels = True
    assert found_channels

    # Create channels & check correct sort AL
    channel_data_list = [None, 1, 2, 2, None, 1, None, 5, 4, None]
    channel_type_list = ["NEWS", "TASKS", "CHAT", "ROOM"]
    for channel in channel_data_list:
        channels_data = {
            "name": "cat",
            "type": choice(channel_type_list),
            "community_id": community_id,
            "next_id": channel
        }
    #     if channel is None:
    #         prev_chan = Channel.find_by_next_id(
    #             community_id=community_id,
    #             category_id=None,
    #             next_id=channel,
    #         ).id
    #     else:
    #         prev_chan = Channel.find_by_id(channel).prev_channel_id
    #
        channel_id = assert_create_channel(channels_data)
        channels_ids.append(channel_id)
    #
    #     assert Channel.find_by_id(channel_id).prev_channel_id == prev_chan
    #     assert Channel.find_by_id(channel_id).next_channel_id == channel

    print(get_channels_list(community_id))
