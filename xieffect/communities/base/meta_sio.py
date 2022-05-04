from pydantic import BaseModel, Field

from common import EventGroup, EventSpace, DuplexEvent, User
from .meta_db import Community
from .users_ext_db import CommunitiesUser

communities_meta_events = EventGroup(use_kebab_case=True)


class CommunitiesEventSpace(EventSpace):
    new_community = communities_meta_events.bind_sub(Community.IndexModel)

    @communities_meta_events.bind_dup(Community.CreateModel, Community.IndexModel, use_event=True)
    @communities_meta_events.jwt_authorizer(User)
    def create_community(self, event: DuplexEvent, session, user: User, name: str, description: str = None):
        community = Community.create(session, name, description, user)
        cu = CommunitiesUser.find_or_create(session, user.id)
        cu.join_community(community.id)

        CommunitiesEventSpace.new_community.emit(_data=community, _room=f"user-{user.id}", _include_self=False)
        # TODO fix in ffs  # TODO binding should be done on the whole EventSpace via metaclass
        event.emit(_data=community)

    class CommunityIdModel(BaseModel):
        community_id: int

    @communities_meta_events.bind_dup(CommunityIdModel, use_event=True)
    @communities_meta_events.jwt_authorizer(User)
    @communities_meta_events.database_searcher(Community, use_session=True)
    def leave_community(self, event: DuplexEvent, session, user: User, community: Community):
        cu = CommunitiesUser.find_or_create(session, user.id)
        cu.leave_community(session, community.id)
        event.emit(community_id=community.id, _room=f"user-{user.id}", _include_self=False)

    class ReorderModel(BaseModel):
        community_id: int = Field(alias="source-id")
        target_index: int

    @communities_meta_events.bind_dup(ReorderModel, use_event=True)
    @communities_meta_events.jwt_authorizer(User)
    @communities_meta_events.database_searcher(Community, use_session=True)
    def reorder_community(self, event: DuplexEvent, session, user: User, community: Community, target_index: int):
        cu = CommunitiesUser.find_or_create(session, user.id)
        if cu.reorder_community_list(session, community.id, target_index):
            event.emit(community_id=community.id, target_index=target_index,
                       _room=f"user-{user.id}", _include_self=False)
        else:
            communities_meta_events.abort(404, "Community not in the list")
