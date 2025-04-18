from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.infrastructure.database import Base, DATABASE_URL

# Connection to the database
config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Setup for migrations
def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    connection = connectable.connect()
    try:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
    finally:
        connection.close()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
