"""Engine + session factory. Supports Postgres (deploy) and SQLite (local/tests)."""
from __future__ import annotations

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from infra.db_models import Base
from packages.common.config import get_settings

_engine = None
_SessionLocal = None


def _make_url() -> str:
    s = get_settings()
    if s.db_backend == "sqlite":
        return f"sqlite:///{s.sqlite_path}"
    return s.postgres_dsn


def get_engine():
    global _engine
    if _engine is None:
        url = _make_url()
        kwargs = {"future": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
            # ensure the parent directory of the sqlite file exists
            path = get_settings().sqlite_path
            parent = os.path.dirname(os.path.abspath(path))
            os.makedirs(parent, exist_ok=True)
        _engine = create_engine(url, **kwargs)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), class_=Session, expire_on_commit=False)
    return _SessionLocal


@contextmanager
def session_scope():
    factory = get_session_factory()
    s = factory()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def init_db() -> None:
    """Create all tables. Idempotent."""
    Base.metadata.create_all(get_engine())
