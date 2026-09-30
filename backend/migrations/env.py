from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import settings
from app.core.database import Base
import app.organizations.models  # noqa: F401  (registers identity models on Base.metadata)
import app.domain.models  # noqa: F401  (registers Phase 2 domain models on Base.metadata)
import app.evidence.models  # noqa: F401  (registers Phase 3 evidence models on Base.metadata)
import app.document_intelligence.models  # noqa: F401  (registers Phase 4 processing models on Base.metadata)

config = context.config

# Only configure logging when invoked from the alembic CLI; when run in-process (app startup,
# tests) the host application owns logging.
if config.config_file_name is not None and not config.attributes.get("skip_logging_config"):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata

# Legacy dispute tables are managed by hand-written migrations, not ORM models;
# keep autogenerate from proposing to drop them.
def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and reflected and compare_to is None:
        return False
    return True


def _database_url() -> str:
    return config.attributes.get("database_url") or settings.DATABASE_URL


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_database_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite cannot ALTER most constraints in place
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
