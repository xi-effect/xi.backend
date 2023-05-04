from __future__ import annotations

from collections.abc import Callable

from flask_fullstack import assert_contains

from common import db
from communities.base.discussion_db import DiscussionMessage, Discussion
from vault.files_db import File


def assert_message(
    message: DiscussionMessage, content: dict[str, str], file_id: int
) -> None:
    assert_contains(
        {"content": message.content, "files": message.files},
        {"content": content, "files": [File.find_by_id(file_id)]},
    )


def test_discussion_messages(
    test_discussion_id: int,
    test_message_content: dict[str, str],
    test_message_id: int,
    test_file_id: int,
    file_maker: Callable[File],
):
    message: DiscussionMessage = DiscussionMessage.find_by_id(test_message_id)
    assert Discussion.find_by_id(test_discussion_id) is not None
    assert message is not None

    assert_message(message, test_message_content, test_file_id)
    discussion: list[int] = Discussion.get_discussion(entry_id=test_discussion_id)
    assert len(discussion) == 1

    new_content: dict[str, str] = {"update": "content"}
    new_file_id: int = file_maker("test-2.json").id
    message.update(new_content, [new_file_id])
    db.session.commit()
    assert_message(message, new_content, new_file_id)
