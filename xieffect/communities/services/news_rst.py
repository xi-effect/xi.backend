from __future__ import annotations

from functools import wraps

from datetime import datetime

from flask_restx import Resource, inputs
from flask_restx.reqparse import RequestParser

from sqlalchemy import select

from common import ResourceController, PydanticModel, User, get_or_pop, counter_parser
from .news_db import News
from communities.base.meta_db import Community, Participant, ParticipantRole

controller = ResourceController("communities-news", path="/communities/")

news_parser: RequestParser = RequestParser()
news_parser.add_argument("title", type=str, required=True)
news_parser.add_argument("description", type=str)
news_parser.add_argument("create_datetime", type=inputs.datetime)
news_parser.add_argument("change_datetime", type=inputs.datetime)
news_parser.add_argument("deleted", type=bool)



@controller.route("/<int:community_id>/news/index/")
class NewsList(Resource):
    @controller.jwt_authorizer(User, check_only=True)
    @controller.marshal_list_with(News.MainData)
    def get(self, session, community_id: int):
        return News.find_by_community(session, community_id)
    # @controller.jwt_authorizer(User, check_only=True)
    # @controller.argument_parser(counter_parser)
    # @controller.database_searcher(Community, check_only=True, use_session=True)
    # @controller.lister(20, News.MainData)
    # def get(self, session, community_id: int, start: int, finish: int):
    #     return News.find_by_community(session, community_id, start, finish - start)

    @controller.jwt_authorizer(User)
    @controller.argument_parser(news_parser)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.marshal_with(News.MainData)
    def post(self, session, title: str, description: str, create_datetime: inputs.datetime,
             change_datetime: inputs.datetime, deleted: bool, user: User, community_id: int):
        user_id = user.id
        # Проверка юзера на причастность к сообществу
        if (participant := session.get_first(select(Participant).filter_by(user_id=user_id))) is None:
            # return {"a": "Participant does not exist"}
            return ResourceController.abort(session, 400, "Participant does not exist")
        # Проверка участника на роль
        if participant.role == ParticipantRole.OWNER:
            return News.create(session, title, description, create_datetime, change_datetime, deleted, user_id,
                           community_id)
        else:
            return ResourceController.abort(session, 403, "Must have the rights of the OWNER")

@controller.route("/<int:community_id>/news/<int:entry_id>/")
class NewsID(Resource):
    @controller.jwt_authorizer(User)
    @controller.argument_parser(news_parser)
    @controller.database_searcher(Community, check_only=True, use_session=True)
    @controller.marshal_with(News.MainData)
    def put(self, session, title: str, description: int, user: User, create_datetime: inputs.datetime,
            change_datetime: inputs.datetime, deleted: bool, community_id: int, entry_id: int):
        user_id = user.id
        # Проверка наличия изменяемой новости
        if (update_news := News.find_by_id(session, community_id, entry_id)) is None:
            return ResourceController.abort(session, 400, "News does not exist")
        # Проверка юзера на причастность к сообществу
        if (participant := session.get_first(select(Participant).filter_by(user_id=user_id))) is None:
            return ResourceController.abort(session, 400, "Participant does not exist")
        # Проверка участника на роль
        if participant.role == ParticipantRole.OWNER:
            update_news.title = update_news.title if (title is None) else title
            update_news.description = update_news.description if (description is None) else description
            update_news.change_datetime = datetime.utcnow().replace(microsecond=0)
            return update_news
        else:
            return ResourceController.abort(session, 403, "Must have the rights of the OWNER")

    @controller.jwt_authorizer(User)
    @controller.marshal_with(News.MainData)
    def delete(self, session, community_id: int, entry_id: int, user: User):
        user_id = user.id
        # Проверка наличия удаляемой новости
        if (deleted_news := News.find_by_id(session, community_id, entry_id)) is None:
            return ResourceController.abort(session, 400, "News does not exist")
        # Проверка юзера на причастность к сообществу
        if (participant := session.get_first(select(Participant).filter_by(user_id=user_id))) is None:
            return ResourceController.abort(session, 400, "Participant does not exist")
        # Проверка участника на роль
        if participant.role == ParticipantRole.OWNER:
            deleted_news.deleted = True
            return deleted_news
        else:
            return ResourceController.abort(session, 403, "Must have the rights of the OWNER")
