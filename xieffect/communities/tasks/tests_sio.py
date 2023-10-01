from __future__ import annotations

from datetime import datetime

from flask_fullstack import DuplexEvent

from common import EventController
from communities.base.meta_db import Community, PermissionType
from communities.base.utils import check_permission
from communities.tasks.tasks_db import TaskEmbed
from communities.tasks.tasks_sio import check_files, TasksEventSpace
from communities.tasks.tests_db import Test
from communities.tasks.utils import test_finder
from users.users_db import User

controller = EventController()


@controller.route()
class TestsEventSpace(TasksEventSpace):
    class TestIdModel(TasksEventSpace.CommunityIdModel):
        test_id: int

    class CreationModel(Test.CreateModel, TasksEventSpace.CommunityIdModel):
        files: list[int] = []

    @controller.argument_parser(CreationModel)
    @controller.mark_duplex(Test.FullModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_TASKS, use_user=True)
    @controller.marshal_ack(Test.FullModel)
    def new_test(
        self,
        event: DuplexEvent,
        community: Community,
        user: User,
        page_id: int,
        name: str,
        files: list[int],
        description: str | None,
        opened: datetime | None,
        closed: datetime | None,
    ) -> Test:
        checked_files: set[int] = check_files(files)

        test: Test = Test.create(
            user.id, community.id, page_id, name, description, opened, closed
        )

        TaskEmbed.add_files(checked_files, task_id=test.id)
        event.emit_convert(test, TasksEventSpace.room_name(community.id))
        return test

    class UpdateTestModel(TasksEventSpace.UpdateModel, TestIdModel):
        pass

    @controller.argument_parser(UpdateTestModel)
    @controller.mark_duplex(Test.FullModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @test_finder(controller)
    @controller.marshal_ack(Test.FullModel)
    def update_test(
        self,
        event: DuplexEvent,
        test: Test,
        **kwargs,
    ) -> Test:
        files: list[int] | None = kwargs.pop("files", None)
        if files is not None:
            new_files: set[int] = check_files(files)
            old_files: set[int] = set(TaskEmbed.get_file_ids(task_id=test.id))
            TaskEmbed.delete_files(old_files - new_files, task_id=test.id)
            TaskEmbed.add_files(new_files - old_files, task_id=test.id)

        test.update(**kwargs)
        event.emit_convert(test, room=TasksEventSpace.room_name(test.community_id))
        return test

    @controller.argument_parser(TestIdModel)
    @controller.mark_duplex(TestIdModel, use_event=True)
    @check_permission(controller, PermissionType.MANAGE_TASKS)
    @test_finder(controller)
    @controller.force_ack()
    def delete_test(self, event: DuplexEvent, test: Test) -> None:
        test.soft_delete()
        event.emit_convert(
            room=TasksEventSpace.room_name(test.community_id),
            community_id=test.community_id,
            test_id=test.id,
        )
