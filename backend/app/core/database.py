"""
SQLAlchemy engine/session for the identity layer (organizations, users).

The legacy dispute pipeline still uses raw sqlite3 in app/database/db.py against the
same database file. Both layers share one schema, managed by Alembic (backend/migrations).
"""
from datetime import datetime, timezone
from typing import Annotated, Generator

from pydantic import AfterValidator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


# SQLite returns naive datetimes; values are always written as UTC, so mark them as such
# in API responses (serialized with +00:00) instead of letting clients guess the zone.
UTCDateTime = Annotated[datetime, AfterValidator(_as_utc)]


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
)

if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        # WAL lets the ORM layer and the raw sqlite3 layer read/write the same file without lock contention.
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
