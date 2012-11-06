from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, create_session
from sqlalchemy.ext.declarative import declarative_base

# engine = create_engine('sqlite:///roush.db', convert_unicode=True)
engine = None
db_session = scoped_session(lambda: create_session(autocommit=False,
                                                   autoflush=False,
                                                   bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


def init_db(uri, **kwargs):
    global engine
    engine = create_engine(uri, **kwargs)
    Base.metadata.create_all(bind=engine)
