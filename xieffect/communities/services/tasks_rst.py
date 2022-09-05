from __future__ import annotations

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController, User, counter_parser
from vault.files_db import File
from .tasks_db import Task, TaskEmbed
from ..base.meta_db import Community, Participant, ParticipantRole

# Set Tasks behavior here
FILES_LIMIT = 10
TASKS_PER_PAGE = 48

controller = ResourceController(
    "communities-tasks", path="/communities/<int:community_id>/"
)


def check_user(session, community_id: int, user_id: int, check_role: bool = False):
    """
    Check if user is participant of a community, optionally check user role.
    In case of error will send 403 response with a message.
    :param check_role: (default:False) If true, will also check a user role, should be OWNER.
    """
    if (participant := Participant.find_by_ids(session, community_id, user_id)) is None:
        controller.abort(403, "Permission denied: Not a member")
    if check_role and participant.role != ParticipantRole.OWNER:
        controller.abort(403, "Permission denied: Low role")


def check_files(session, files: list[int]) -> list[int]:
    """
    - Delete duplicates from a list with file ids.
    - Check files limit.
    - Check if file id is existed.

    Return checked list with file ids.
    """
    files = list(set(files))
    if len(files) > FILES_LIMIT:
        controller.abort(400, f"Too many files")
    for file_id in files:
        if File.find_by_id(session, file_id) is None:
            controller.abort(404, File.not_found_text)
    return files


@controller.route("/tasks/")
class Tasks(Resource):
    task_parser: RequestParser = RequestParser()
    task_parser.add_argument("page_id", type=int, required=True)
    task_parser.add_argument("name", required=True)
    task_parser.add_argument("description")
    task_parser.add_argument(
        "files",
        type=int,
        action="append",
        help=f"List with file ids. LIMIT {FILES_LIMIT} files.",
        default={},
    )

    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(counter_parser)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.lister(TASKS_PER_PAGE, Task.IndexModel)
    def get(self, session, user: User, community_id: int, start: int, finish: int):
        check_user(session, community_id, user.id)
        return Task.find_paginated_by_kwargs(
            session,
            start,
            finish - start,
            Task.updated,
            community_id=community_id,
            deleted=False,
        )

    @controller.doc_abort(403, "Permission Denied")
    @controller.doc_abort(400, f"Too many files: LIMIT {FILES_LIMIT} files")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(task_parser)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.marshal_with(Task.FullModel)
    def post(
        self,
        session,
        page_id: int,
        name: str,
        description: str,
        files: list[int],
        user: User,
        community_id: int,
    ):
        check_user(session, community_id, user.id)
        task = Task.create(session, user.id, community_id, page_id, name, description)
        if len(files) != 0:
            TaskEmbed.add_files(session, task.id, check_files(session, files))
        return task


@controller.route("/tasks/<int:task_id>/")
class TaskOperations(Resource):
    update_parser: RequestParser = RequestParser()
    update_parser.add_argument("page_id", store_missing=False)
    update_parser.add_argument("name", store_missing=False)
    update_parser.add_argument("description")
    update_parser.add_argument(
        "files",
        type=int,
        action="append",
        help=f"List with files id. LIMIT {FILES_LIMIT} files.",
        default={},
    )

    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    @controller.database_searcher(Community, check_only=True)
    @controller.database_searcher(Task, error_code="404 ", use_session=True)
    @controller.marshal_with(Task.FullModel)
    def get(self, session, user: User, community_id: int, task: Task):
        if task.community_id != community_id:
            controller.abort(404, Task.not_found_text)
        check_user(session, community_id, user.id)
        return task

    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(update_parser)
    @controller.database_searcher(Community, check_only=True)
    @controller.database_searcher(Task, error_code="404 ", use_session=True)
    @controller.a_response()
    def put(
        self,
        session,
        files: list[int],
        user: User,
        community_id: int,
        task: Task,
        **kwargs,
    ):
        if task.community_id != community_id:
            controller.abort(404, Task.not_found_text)
        check_user(session, community_id, user.id, check_role=True)
        # If received a new list with file ids, then add files.
        # Otherwise, check for task's file and remove old files.
        if len(files) != 0:
            new_files = check_files(session, files)
            old_files = TaskEmbed.get_task_files(session, task.id)
            add_files = list(set(new_files).difference(old_files))
            remove_files = list(set(old_files).difference(new_files))
            TaskEmbed.delete_files(session, task.id, remove_files)
            TaskEmbed.add_files(session, task.id, add_files)
        elif remove_files := TaskEmbed.get_task_files(session, task.id):
            TaskEmbed.delete_files(session, task.id, remove_files)

        Task.update(session, task.id, community_id, **kwargs)

    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    @controller.database_searcher(Community, check_only=True)
    @controller.database_searcher(Task, error_code="404 ", use_session=True)
    @controller.a_response()
    def delete(self, session, user: User, community_id: int, task: Task):
        if task.community_id != community_id:
            controller.abort(404, Task.not_found_text)
        check_user(session, community_id, user.id, check_role=True)
        task.deleted = True
