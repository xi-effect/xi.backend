from __future__ import annotations

from collections.abc import Callable

from pydantic_marshals.contains import assert_contains

from common import db
from communities.base.discussion_db import DiscussionMessage, Discussion
from vault.files_db import File


def assert_message(
    message: DiscussionMessage, content: dict[str, str], file_id: int
) -> None:
    assert_contains(
        {"content": message.content, "files": [file.id for file in message.files]},
        {"content": content, "files": [file_id]},
    )


def test_discussion_messages(
    test_discussion_id: int,
    message_content: dict[str, str],
    message_id: int,
    test_file_id: int,
    file_maker: Callable[[str], File],
):
    message: DiscussionMessage = DiscussionMessage.find_by_id(message_id)
    assert Discussion.find_by_id(test_discussion_id) is not None
    assert message is not None

    assert_message(message, message_content, test_file_id)
    messages: list[int] = DiscussionMessage.get_paginated_messages(
        test_discussion_id, 0, 50
    )
    assert len(messages) == 1

    new_content: dict[str, str] = {"update": "content"}
    new_file_id: int = file_maker("test-2.json").id
    message.update(new_content, [new_file_id])
    db.session.commit()
    assert_message(message, new_content, new_file_id)
