from __future__ import annotations

from flask_fullstack import ResourceController, EventController

from common.consts import FILES_LIMIT
from vault.files_db import File


def check_files(
    controller: ResourceController | EventController,
    files: list[int],
) -> set[int]:
    """
    - Delete duplicates from a list of file ids.
    - Check list length limit.
    - Check if all files exist.

    Return checked list with file ids.
    """
    files: set[int] = set(files)
    if len(files) > FILES_LIMIT:
        controller.abort(400, "Too many files")
    for file_id in files:
        if File.find_by_id(file_id) is None:
            controller.abort(404, File.not_found_text)
    return files
