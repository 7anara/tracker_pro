from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from tracker_pro.config import settings


DATABASE_URL = "postgresql://postgres:040506@127.0.0.1:5432/tracker_pro"
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
