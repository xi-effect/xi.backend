from __future__ import annotations

import pytest
from pydantic_marshals.contains import assert_contains

from pages.pages_db import Page


@pytest.mark.skip()
def test_pages_crud(test_page_id: int, test_page_data: dict[str, str | dict]):
    page: Page = Page.find_by_id(test_page_id)
    assert page is not None

    assert_contains({"title": page.title, "content": page.content}, test_page_data)

    page.soft_delete()
    assert page.find_by_id(test_page_id) is None
    assert page.find_first_by_kwargs(id=test_page_id) is not None
