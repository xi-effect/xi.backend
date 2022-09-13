from __future__ import annotations

from flask_restx import Resource

from common import ResourceController, User, counter_parser
from .news_db import Post
from ..base.meta_db import Participant

controller = ResourceController(
    "communities-news", path="/communities/<int:community_id>/news/"
)


@controller.route("/index/")
class NewsLister(Resource):
    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    @controller.argument_parser(counter_parser)
    @controller.lister(20, Post.IndexModel)
    def get(self, session, community_id: int, user: User, start: int, finish: int):
        # Community membership check
        if Participant.find_by_ids(session, community_id, user.id) is None:
            controller.abort(403, "Permission Denied: Participant not found")
        return Post.find_by_community(session, community_id, start, finish - start)


@controller.route("/<int:post_id>/")
class NewsGetter(Resource):
    @controller.doc_abort(403, "Permission Denied")
    @controller.jwt_authorizer(User)
    @controller.database_searcher(Post, use_session=True)
    @controller.marshal_with(Post.IndexModel)
    def get(self, session, community_id: int, post: Post, user: User):
        # Community membership check
        if Participant.find_by_ids(session, community_id, user.id) is None:
            controller.abort(403, "Permission Denied: Participant not found")
        # News availability check
        if post is None or post.community_id != community_id:
            controller.abort(404, "Post not found")
        return post
