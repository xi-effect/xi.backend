from os import getenv

from dotenv import load_dotenv

from common._core import configure_sqlalchemy, configure_whooshee  # , SocketIO  # noqa
from common._whoosh import IndexService  # noqa

load_dotenv("../.env")

db_url: str = getenv("DB_LINK", "sqlite:///app.db")
db_meta, Base, Session = configure_sqlalchemy(db_url)
index_service = configure_whooshee(Session)
