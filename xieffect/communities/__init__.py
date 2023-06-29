from .base import (
    CommunitiesUser,
    communities_namespace,
    participants_events,
    invitation_namespace,
    role_namespace,
    role_events,
    communities_meta_events,
    invitation_events,
)
from .services import news_namespace, news_events, videochat_namespace, videochat_events
from .tasks import (
    teacher_tasks_namespace,
    student_tasks_namespace,
    task_discussions_namespace,
    tasks_events,
    task_discussions_events,
)
