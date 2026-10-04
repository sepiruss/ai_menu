import asyncio
import os
import sys

# Set environment variables BEFORE importing anything
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://smart_menu:smart_menu_dev@localhost:5432/smart_menu'
os.environ['SECRET_KEY'] = 'dev-secret-key-for-testing-only-min-32-chars-long'

# Add the backend to path
sys.path.insert(0, '..')

from sqlalchemy.ext.asyncio import create_async_engine
from app.core.database import Base
from app.core.models import (
    User, Restaurant, Branch, Table, Menu, Category, 
    MenuItem, MenuItemOption, RefreshToken,
    QRCode, Customer, CustomerSession, CustomerEvent,
    Cart, CartItem, Order, OrderItem
)

async def create_tables():
    # Use the DATABASE_URL from environment
    database_url = os.environ['DATABASE_URL']
    print(f"Connecting to: {database_url}")
    
    engine = create_async_engine(
        database_url,
        echo=True,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("All tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_tables())