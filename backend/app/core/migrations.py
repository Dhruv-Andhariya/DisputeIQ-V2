"""Programmatic access to Alembic, used by app startup, manage.py and the test suite."""
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _config(database_url: Optional[str]) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.attributes["skip_logging_config"] = True
    if database_url:
        cfg.attributes["database_url"] = database_url
    return cfg


def upgrade_to(revision: str, database_url: Optional[str] = None) -> None:
    command.upgrade(_config(database_url), revision)


def upgrade_to_head(database_url: Optional[str] = None) -> None:
    upgrade_to("head", database_url)


def downgrade_to(revision: str, database_url: Optional[str] = None) -> None:
    command.downgrade(_config(database_url), revision)
