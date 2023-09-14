from __future__ import annotations

from flask_fullstack import DuplexEvent, EventSpace
from flask_socketio import join_room, leave_room

from common import EventController, User
from communities.base import check_permission, PermissionType
from communities.tasks.main_db import Task
from communities.tasks.main_sio import TasksEventSpace
from communities.tasks.tasks_answers_db import TaskAnswer, TaskAnswerFile
from vault import File

FILES_LIMIT: int = 10

controller = EventController()


def check_files(files: list[int]) -> set[int]:
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


@controller.route()
class AnswersEventSpace(EventSpace):
    @classmethod
    def room_name(cls, task_id: int) -> str:
        return f"cs-answers-{task_id}"

    class TaskCommunityModel(
        TasksEventSpace.TaskIdModel, TasksEventSpace.CommunityIdModel
    ):
        pass

    @controller.argument_parser(TaskCommunityModel)
    @check_permission(controller, PermissionType.MANAGE_ANSWERS)
    @controller.force_ack()
    def open_answer(self, task: Task):
        join_room(self.room_name(task.id))

    @controller.argument_parser(TaskCommunityModel)
    @check_permission(controller, PermissionType.MANAGE_ANSWERS)
    @controller.force_ack()
    def close_answer(self, task: Task):
        leave_room(self.room_name(task.id))

    class CreationModel(TaskAnswer.CreateModel, TasksEventSpace.CommunityIdModel):
        files: list[int] = []

    @controller.argument_parser(CreationModel)
    @controller.mark_duplex(TaskAnswer.FullModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_ANSWERS, use_user=True)
    @controller.database_searcher(Task)
    @controller.marshal_ack(TaskAnswer.FullModel)
    def new_answer(
        self,
        event: DuplexEvent,
        user: User,
        task: Task,
        page_id: int,
        files: list[int],
    ) -> TaskAnswer:
        checked_files: set[int] = check_files(files)
        answer: TaskAnswer = TaskAnswer.create(
            task.id,
            user.id,
            page_id,
        )

        TaskAnswerFile.add_files(checked_files, task_answer_id=answer.id)
        event.emit_convert(answer, self.room_name(task.id))
        return answer
