import asyncio
import os
import sys

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://smart_menu:smart_menu_dev@localhost:5432/smart_menu'
os.environ['SECRET_KEY'] = 'dev-secret-key-for-testing-only-min-32-chars-long'

# Add the backend to path
sys.path.insert(0, '.')

from alembic.config import Config
from alembic import command

# Load alembic config
cfg = Config('alembic/alembic.ini')
cfg.set_main_option('sqlalchemy.url', os.environ['DATABASE_URL'])

# Run migration
command.upgrade(cfg, 'head')
print("Migration completed successfully!")