from logging.config import fileConfig
import os # <--- Add this
import sys
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add the parent directory of 'alembic' (which should be /code, your project root in the container)
# to sys.path. This allows Python to find the 'app' module.
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

# Now this import should work:
from app.db.models import Base
target_metadata = Base.metadata
# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
# Ensure this path is correct relative to where alembic is run,
# or adjust sys.path if needed.
# If alembic/ is at the root with app/, this might need adjustment
# Example:
# import sys
# sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))
from app.db.models import Base # Make sure this import works from the context alembic runs in.
target_metadata = Base.metadata


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_url():
    """
    Return the database URL.
    Prioritizes DATABASE_URL environment variable (used in Docker)
    Falls back to sqlalchemy.url from alembic.ini (used for local commands)
    """
    env_db_url = os.getenv("DATABASE_URL")
    if env_db_url:
        # If the DATABASE_URL from the environment is for asyncpg,
        # and Alembic's default offline/online mode runs synchronously,
        # you might need to adapt it.
        # However, for `engine_from_config`, it often handles SQLAlchemy URLs.
        # If issues arise, convert 'postgresql+asyncpg' to 'postgresql+psycopg2' or 'postgresql'
        # if Alembic is performing synchronous operations.
        # For now, let's assume the SQLAlchemy URL format is compatible.
        # If you use `psycopg` (v3) for migrations:
        if "asyncpg" in env_db_url:
             return env_db_url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
        return env_db_url
    return config.get_main_option("sqlalchemy.url")

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url() # <--- Use the helper function
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Get the section from alembic.ini
    configuration = config.get_section(config.config_ini_section)
    # Override sqlalchemy.url with our dynamic URL
    configuration["sqlalchemy.url"] = get_url() # <--- Use the helper function

    connectable = engine_from_config(
        configuration, # <--- Use the modified configuration
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()