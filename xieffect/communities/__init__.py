from .base import (
    communities_namespace,
    invitation_namespace,
    role_namespace,
    role_events,
    communities_meta_events,
    invitation_events,
    CommunitiesUser,
)
from .services import news_namespace, news_events, videochat_namespace, videochat_events
from .tasks import teacher_tasks_namespace, student_tasks_namespace, tasks_events
