"""数据库引擎与会话。SQLite（本地）/ Postgres（NAS）通过 DATABASE_URL 切换，模型不变。"""
import datetime as dt

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _connect_args() -> dict:
    # SQLite 多线程访问需要关闭同线程检查；Postgres 不需要
    if settings.database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


engine = create_engine(settings.database_url, connect_args=_connect_args(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def now_utc() -> dt.datetime:
    """统一用 naive UTC 存库，展示层再转本地时间，避免时区混乱。"""
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
