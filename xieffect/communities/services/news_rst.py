from __future__ import annotations

from datetime import datetime

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController, User, counter_parser
from .news_db import Post
from communities.base.meta_db import Community, Participant, ParticipantRole

controller = ResourceController("communities-news", path="/communities/")

# Parser for create and update news
news_parser: RequestParser = RequestParser()
news_parser.add_argument("title", type=str, required=True)
news_parser.add_argument("description", type=str)


@controller.route("/<int:community_id>/news/index/")
class NewsLister(Resource):
    # Get list of news with pagination
    @controller.jwt_authorizer(User, check_only=True)
    @controller.argument_parser(counter_parser)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.lister(20, Post.MainData)
    def get(self, session, community_id: int, start: int, finish: int):
        return Post.find_by_community(session, community_id, start, finish - start)

    # Create news
    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(news_parser)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.marshal_with(Post.MainData)
    def post(self, session, title: str, description: str, user: User, community_id: int):
        # Community membership check
        if (participant := Participant.find_by_ids(session, community_id, user.id)) is None:
            return controller.abort(403, "Permission Denied: Participant not found")
        # Participant role check
        if participant.role == ParticipantRole.OWNER:
            return Post.create(session, title, description, user.id, community_id)
        else:
            return controller.abort(403, "Permission Denied: Low role")


@controller.route("/<int:community_id>/news/<int:entry_id>/")
class NewsChanger(Resource):
    # Create title optionally for update news
    news_parser.replace_argument("title", type=str, required=False)

    # Update news
    @controller.doc_abort(404, "News not found")
    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(news_parser)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.marshal_with(Post.MainData)
    def put(self, session, title: str, description: int, user: User, community_id: int, entry_id: int):
        # News availability check
        if (update_news := Post.find_by_id(session, entry_id)) is None or update_news.community_id != community_id:
            return controller.abort(404, "News not found")
        # Community membership check
        if (participant := Participant.find_by_ids(session, community_id, user.id)) is None:
            return controller.abort(403, "Permission Denied: Participant not found")
        # Participant role check
        if participant.role == ParticipantRole.OWNER:
            update_news.title = update_news.title if title is None else title
            update_news.description = update_news.description if description is None else description
            update_news.change_datetime = datetime.utcnow().replace(microsecond=0)
            return update_news
        else:
            return controller.abort(403, "Permission Denied: Low role")

    # Soft-delete news
    @controller.doc_abort(404, "News not found")
    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    def delete(self, session, community_id: int, entry_id: int, user: User):
        # Deleted news availability check
        if (deleted_news := Post.find_by_id(session, entry_id)) is None or deleted_news.community_id != community_id:
            return controller.abort(404, "News not found")
        # Community membership check
        if (participant := Participant.find_by_ids(session, community_id, user.id)) is None:
            return controller.abort(403, "Permission Denied: Participant not found")
        # Participant role check
        if participant.role == ParticipantRole.OWNER:
            deleted_news.deleted = True
            return {"a": "News was successfully deleted"}, 200
        else:
            return controller.abort(403, "Permission Denied: Low role")
