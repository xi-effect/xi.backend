from __future__ import annotations

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController, User, counter_parser
from .news_db import Post
from ..base.meta_db import Community, Participant, ParticipantRole

controller = ResourceController("communities-news", path="/communities/<int:community_id>/news/")

# Parser for create and update news
news_parser: RequestParser = RequestParser()
news_parser.add_argument("title", type=str, required=True)
news_parser.add_argument("description", type=str)


@controller.route("/index/")
class NewsLister(Resource):
    # Get list of news with pagination
    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(counter_parser)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.lister(20, Post.MainData)
    def get(self, session, community_id: int, user: User, start: int, finish: int):
        # Community membership check
        if Participant.find_by_ids(session, community_id, user.id) is None:
            return controller.abort(403, "Permission Denied: Participant not found")
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


@controller.route("/<int:entry_id>/")
class NewsChanger(Resource):
    # Create title optionally for update news
    news_parser.replace_argument("title", type=str, required=False)

    # Get news
    @controller.doc_abort(404, "Post not found")
    @controller.jwt_authorizer(User)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.marshal_with(Post.MainData)
    def get(self, session, community_id: int, entry_id: int, user: User):
        # Community membership check
        if Participant.find_by_ids(session, community_id, user.id) is None:
            return controller.abort(403, "Permission Denied: Participant not found")
        # News availability check
        if (news := Post.find_by_id(session, entry_id)) is None or news.community_id != community_id:
            return controller.abort(404, "Post not found")
        return news

    # Update news
    @controller.doc_abort(404, "Post not found")
    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(news_parser)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.marshal_with(Post.MainData)
    def put(self, session, title: str, description: int, user: User, community_id: int, entry_id: int):
        # News availability check
        update_news = Post.find_by_id(session, entry_id)
        if update_news is None or update_news.community_id != community_id:
            controller.abort(404, "Post not found")
        # Community membership check
        if (participant := Participant.find_by_ids(session, community_id, user.id)) is None:
            controller.abort(403, "Permission Denied: Participant not found")
        # Participant role check
        if participant.role != ParticipantRole.OWNER:
            controller.abort(403, "Permission Denied: Low role")

        if title is not None:
            update_news.title = update_news.title
        if description is not None:
            update_news.description = update_news.description
        return update_news

    # Soft-delete news
    @controller.doc_abort(404, "Post not found")
    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    def delete(self, session, community_id: int, entry_id: int, user: User):
        # Deleted news availability check
        if (deleted_news := Post.find_by_id(session, entry_id)) is None or deleted_news.community_id != community_id:
            return controller.abort(404, "Post not found")
        # Community membership check
        if (participant := Participant.find_by_ids(session, community_id, user.id)) is None:
            return controller.abort(403, "Permission Denied: Participant not found")
        # Participant role check
        if participant.role == ParticipantRole.OWNER:
            deleted_news.deleted = True
            return {"a": "News was successfully deleted"}, 200
        else:
            return controller.abort(403, "Permission Denied: Low role")
