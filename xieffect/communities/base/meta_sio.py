from common import EventGroup, EventSpace, DuplexEvent, User
from .meta_db import Community

communities_meta_events = EventGroup(use_kebab_case=True)


class CommunitiesEventSpace(EventSpace):
    use_kebab_case = True

    @communities_meta_events.bind_dup(Community.CreateModel, Community.BaseModel, use_event=True)
    @communities_meta_events.jwt_authorizer(User)
    def create_community(self, event: DuplexEvent, session, user: User, name: str, description: str = None):
        community = Community.create(session, name, description, user)
        event.emit(_data=community)
