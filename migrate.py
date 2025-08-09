import sys
import os
from alembic.config import Config
from alembic import command
from app.core.config import settings

def run_migrations():
    # Load alembic.ini config file (adjust path if needed)
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))

    # Convert async DB URL to sync DB URL for Alembic
    sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    alembic_cfg.set_main_option("sqlalchemy.url", sync_db_url)

    # Run upgrade to latest revision ("head")
    command.upgrade(alembic_cfg, "head")

if __name__ == "__main__":
    try:
        run_migrations()
        print("Migrations applied successfully.")
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)
