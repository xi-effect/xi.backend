from __future__ import annotations

from datetime import datetime

from flask_restx import Resource
from flask_restx.reqparse import RequestParser

from common import ResourceController, User, counter_parser
from .news_db import Post
from ..base.meta_db import Community, Participant, ParticipantRole

controller = ResourceController(
    "communities-news", path="/communities/<int:community_id>/news/"
)


@controller.route("/index/")
class NewsLister(Resource):
    # Parser for create and update news
    parser: RequestParser = RequestParser()
    parser.add_argument("title", type=str, required=True)
    parser.add_argument("description", type=str)

    # Get list of news with pagination
    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(counter_parser)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.lister(20, Post.IndexModel)
    def get(self, session, community_id: int, user: User, start: int, finish: int):
        # Community membership check
        if Participant.find_by_ids(session, community_id, user.id) is None:
            controller.abort(403, "Permission Denied: Participant not found")
        return Post.find_by_community(session, community_id, start, finish - start)

    # Create news
    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.marshal_with(Post.IndexModel)
    def post(
        self,
        session,
        title: str,
        description: str,
        user: User,
        community_id: int,
    ):
        participant = Participant.find_by_ids(session, community_id, user.id)

        # Community membership check
        if participant is None:
            controller.abort(403, "Permission Denied: Participant not found")

        # Participant role check
        if participant.role != ParticipantRole.OWNER:
            controller.abort(403, "Permission Denied: Low role")
        return Post.create(session, title, description, user.id, community_id)


@controller.route("/<int:entry_id>/")
class NewsChanger(Resource):
    # Create title optionally for update news
    parser: RequestParser = RequestParser()
    parser.add_argument("title", type=str)
    parser.add_argument("description", type=str)

    # Get news
    @controller.doc_abort(404, "Post not found")
    @controller.jwt_authorizer(User)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.marshal_with(Post.IndexModel)
    def get(self, session, community_id: int, entry_id: int, user: User):
        post = Post.find_by_id(session, entry_id)

        # Community membership check
        if Participant.find_by_ids(session, community_id, user.id) is None:
            controller.abort(403, "Permission Denied: Participant not found")

        # News availability check
        if post is None or post.community_id != community_id:
            controller.abort(404, "Post not found")
        return post

    # Update news
    @controller.doc_abort(404, "Post not found")
    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(parser)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.marshal_with(Post.IndexModel)
    def put(
        self,
        session,
        title: str,
        description: int,
        user: User,
        community_id: int,
        entry_id: int,
    ):
        update_post = Post.find_by_id(session, entry_id)
        participant = Participant.find_by_ids(session, community_id, user.id)

        # News availability check
        if update_post is None or update_post.community_id != community_id:
            controller.abort(404, "Post not found")

        # Community membership check
        if participant is None:
            controller.abort(403, "Permission Denied: Participant not found")

        # Participant role check
        if participant.role != ParticipantRole.OWNER:
            controller.abort(403, "Permission Denied: Low role")

        if title is not None:
            update_post.title = title
        else:
            update_post.title = update_post.title
        if description is not None:
            update_post.description = description
        else:
            update_post.description = update_post.description
        update_post.changed = datetime.utcnow().replace()
        return update_post

    # Soft-delete news
    @controller.doc_abort(404, "Post not found")
    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    def delete(self, session, community_id: int, entry_id: int, user: User):
        deleted_news = Post.find_by_id(session, entry_id)
        participant = Participant.find_by_ids(session, community_id, user.id)

        # Deleted news availability check
        if deleted_news is None or deleted_news.community_id != community_id:
            controller.abort(404, "Post not found")

        # Community membership check
        if participant is None:
            controller.abort(403, "Permission Denied: Participant not found")

        # Participant role check
        if participant.role != ParticipantRole.OWNER:
            controller.abort(403, "Permission Denied: Low role")
        deleted_news.deleted = True
        return {"a": "Post was successfully deleted"}, 200
