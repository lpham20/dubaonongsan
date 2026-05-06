from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine_kwargs = {"connect_args": connect_args, "future": True}
if settings.database_url == "sqlite:///:memory:":
    engine_kwargs["poolclass"] = StaticPool
engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401

    if settings.database_url == "sqlite:///:memory:":
        Base.metadata.create_all(bind=engine)
        return

    from alembic import command
    from alembic.config import Config

    alembic_cfg_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    cfg = Config(str(alembic_cfg_path))
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")
