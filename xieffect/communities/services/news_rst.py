from __future__ import annotations

from flask_fullstack import counter_parser
from flask_restx import Resource

from common import ResourceController
from communities.base.meta_db import Community
from communities.base.utils import check_participant
from communities.services.news_db import Post

controller = ResourceController(
    "communities-news", path="/communities/<int:community_id>/news/"
)


@controller.route("/")
@controller.route("/index/")  # TODO: remove after front fix
class NewsLister(Resource):
    @check_participant(controller)
    @controller.argument_parser(counter_parser)
    @controller.lister(20, Post.IndexModel)
    def get(self, community: Community, start: int, finish: int):  # pragma: no coverage
        return Post.find_by_community(community.id, start, finish - start)


@controller.route("/<int:post_id>/")
class NewsGetter(Resource):  # TODO pragma: no coverage
    @check_participant(controller)
    @controller.database_searcher(Post)
    @controller.marshal_with(Post.IndexModel)
    def get(self, community: Community, post: Post):
        if post is None or post.community_id != community.id:
            controller.abort(404, "Post not found")
        return post
