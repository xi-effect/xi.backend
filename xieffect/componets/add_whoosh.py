from sqlalchemy import select, event
from sqlalchemy.orm.session import Session
from whooshalchemy import Searcher as SearcherBase, IndexService as IndexServiceBase


class IndexService(IndexServiceBase):
    def __init__(self, config=None, session=None, whoosh_base=None):
        super().__init__(config, session, whoosh_base)

        event.listen(Session, "before_flush", lambda session, *_: self.before_commit(session))
        event.listen(Session, "after_flush", lambda session, *_: self.after_commit(session))


class Searcher(SearcherBase):
    def __call__(self, query, limit=None):
        results = self.index.searcher().search(self.parser.parse(query))
        keys = [x[self.primary] for x in results]
        primary_column = getattr(self.model_class, self.primary)

        return select(self.model_class).filter(primary_column.in_(keys))
