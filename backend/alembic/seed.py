import asyncio
import os
import sys

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://smart_menu:smart_menu_dev@localhost:5432/smart_menu'
os.environ['SECRET_KEY'] = 'dev-secret-key-for-testing-only-min-32-chars-long'

# Add the backend to path
sys.path.insert(0, '..')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.models import (
    User, Restaurant, Branch, Table, Menu, Category, 
    MenuItem, MenuItemOption, QRCode,
    Customer, CustomerSession, CustomerEvent, CustomerEventType
)
from app.core.security import hash_password

async def seed_database():
    database_url = os.environ['DATABASE_URL']
    print(f"Connecting to: {database_url}")
    
    engine = create_async_engine(database_url, echo=False)
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        # Create demo user (superuser)
        demo_user = User(
            email="demo@example.com",
            password_hash=hash_password("demo123456"),
            full_name="Demo User",
            role="superuser",
            is_active=True,
            is_superuser=True,
        )
        db.add(demo_user)
        await db.flush()
        print(f"Created user: {demo_user.email} (id={demo_user.id})")
        
        # Create restaurant
        restaurant = Restaurant(
            name="یک رستوران نمونه",
            slug="demo-restaurant",
            description="رستوران نمونه برای نمایش منوی دیجیتال",
            timezone="Asia/Tehran",
            owner_id=demo_user.id,
            is_active=True,
        )
        db.add(restaurant)
        await db.flush()
        print(f"Created restaurant: {restaurant.name} (id={restaurant.id})")
        
        # Create branch
        branch = Branch(
            restaurant_id=restaurant.id,
            name="شعبه مرکزی",
            code="MAIN",
            address="تهران، خیابان ولیعصر، پلاک ۱۲۳",
            phone="+98 21 1234 5678",
            latitude=35.6892,
            longitude=51.3890,
            is_active=True,
        )
        db.add(branch)
        await db.flush()
        print(f"Created branch: {branch.name} (id={branch.id})")
        
        # Create tables
        tables_data = [
            {"number": "۱", "capacity": 2, "code": "T1"},
            {"number": "۲", "capacity": 4, "code": "T2"},
            {"number": "۳", "capacity": 4, "code": "T3"},
            {"number": "۴", "capacity": 6, "code": "T4"},
            {"number": "۵", "capacity": 2, "code": "T5"},
        ]
        tables = []
        for t in tables_data:
            table = Table(
                branch_id=branch.id,
                name=f"میز {t['number']}",
                code=t['code'],
                capacity=t['capacity'],
                is_active=True,
            )
            db.add(table)
            tables.append(table)
        await db.flush()
        print(f"Created {len(tables)} tables")
        
        # Create menu
        menu = Menu(
            branch_id=branch.id,
            name="منوی اصلی",
            description="منوی پیش‌فرض رستوران",
            is_active=True,
            is_default=True,
        )
        db.add(menu)
        await db.flush()
        print(f"Created menu: {menu.name} (id={menu.id})")
        
        # Create categories
        categories_data = [
            {"name": "پیش‌غذا", "slug": "appetizers", "display_order": 1, "parent_id": None},
            {"name": "غذای اصلی", "slug": "main-courses", "display_order": 2, "parent_id": None},
            {"name": "نوشیدنی", "slug": "beverages", "display_order": 3, "parent_id": None},
            {"name": "دسر", "slug": "desserts", "display_order": 4, "parent_id": None},
        ]
        categories = []
        for c in categories_data:
            cat = Category(
                menu_id=menu.id,
                name=c["name"],
                slug=c["slug"],
                display_order=c["display_order"],
                parent_id=c["parent_id"],
                is_visible=True,
            )
            db.add(cat)
            categories.append(cat)
        await db.flush()
        print(f"Created {len(categories)} categories")
        
        # Create menu items
        items_data = [
            # پیش‌غذا
            {
                "name": "سوپ جو",
                "description": "سوپ سنتی ایرانی با جو، لپه و سبزیجات تازه",
                "price_toman": 80000,
                "price_rial": 800000,
                "category_id": categories[0].id,
                "display_order": 1,
                "is_popular": True,
                "allergens_tags": ["gluten"],
            },
            {
                "name": "کوکو سبزی",
                "description": "کوکو سنتی با سبزیجات تازه و آجیل",
                "price_toman": 95000,
                "price_rial": 950000,
                "category_id": categories[0].id,
                "display_order": 2,
                "is_popular": False,
                "allergens_tags": ["egg"],
            },
            {
                "name": "میرزا قاسمی",
                "description": "بادمجان دودی، گوجه‌فرنگی، سیر و تخم‌مرغ",
                "price_toman": 110000,
                "price_rial": 1100000,
                "category_id": categories[0].id,
                "display_order": 3,
                "is_popular": True,
                "allergens_tags": ["egg"],
            },
            # غذای اصلی
            {
                "name": "قورمه‌سبزی",
                "description": "قورمه‌سبزی اصیل با گوشت گوساله، لپه و سبزی قورمه",
                "price_toman": 250000,
                "price_rial": 2500000,
                "category_id": categories[1].id,
                "display_order": 1,
                "is_popular": True,
                "allergens_tags": [],
            },
            {
                "name": "چلوکباب کوبیده",
                "description": "کباب کوبیده گوساله با برنج چلو و روغن‌زمینه",
                "price_toman": 280000,
                "price_rial": 2800000,
                "category_id": categories[1].id,
                "display_order": 2,
                "is_popular": True,
                "allergens_tags": [],
            },
            {
                "name": "زیرشک‌پلی با مرغ",
                "description": "برنج پخت شده با زرشک، مرغ، آجیل و زعفران",
                "price_toman": 265000,
                "price_rial": 2650000,
                "category_id": categories[1].id,
                "display_order": 3,
                "is_popular": False,
                "allergens_tags": ["nuts"],
            },
            {
                "name": "باقالی‌پلی با ماهی",
                "description": "برنج با باقالی، شلغم و ماهی سفیدرنگ دودی",
                "price_toman": 320000,
                "price_rial": 3200000,
                "category_id": categories[1].id,
                "display_order": 4,
                "is_popular": False,
                "allergens_tags": ["fish"],
            },
            # نوشیدنی
            {
                "name": "دوغ سنتی",
                "description": "دوغ خانوادگی با سبزی خرد و نعنا",
                "price_toman": 40000,
                "price_rial": 400000,
                "category_id": categories[2].id,
                "display_order": 1,
                "is_popular": True,
                "allergens_tags": ["dairy"],
            },
            {
                "name": "شربات تخم‌ šربیت",
                "description": "شربات سنتی با تخم‌ šربیت، لیمو و נעنا",
                "price_toman": 35000,
                "price_rial": 350000,
                "category_id": categories[2].id,
                "display_order": 2,
                "is_popular": False,
                "allergens_tags": [],
            },
            {
                "name": "ماست و خیار",
                "description": "ماست غلیظ با خیار خرد، نعنا و سیر",
                "price_toman": 50000,
                "price_rial": 500000,
                "category_id": categories[2].id,
                "display_order": 3,
                "is_popular": False,
                "allergens_tags": ["dairy"],
            },
            # دسر
            {
                "name": "شله‌زرد",
                "description": "شله‌زرد سنتی با زعفران، گلاب، بادام و پسته",
                "price_toman": 85000,
                "price_rial": 850000,
                "category_id": categories[3].id,
                "display_order": 1,
                "is_popular": True,
                "allergens_tags": ["nuts", "dairy"],
            },
            {
                "name": "بستنی سنتی",
                "description": "بستنی saque‌های سنتی ایرانی با زعفران و پسته",
                "price_toman": 90000,
                "price_rial": 900000,
                "category_id": categories[3].id,
                "display_order": 2,
                "is_popular": True,
                "allergens_tags": ["dairy", "nuts"],
            },
            {
                "name": "فالوده شیرازی",
                "description": "فالوده سنتی شیرازی با سیب‌زمینی، لیمو و شیرابه",
                "price_toman": 75000,
                "price_rial": 750000,
                "category_id": categories[3].id,
                "display_order": 3,
                "is_popular": False,
                "allergens_tags": [],
            },
        ]
        
        items = []
        for item_data in items_data:
            item = MenuItem(
                category_id=item_data["category_id"],
                name=item_data["name"],
                description=item_data["description"],
                price_toman=item_data["price_toman"],
                price_rial=item_data["price_rial"],
                is_available=True,
                is_popular=item_data["is_popular"],
                is_new=False,
                display_order=item_data["display_order"],
                allergens_tags=item_data["allergens_tags"],
                item_metadata={},
            )
            db.add(item)
            items.append(item)
        await db.flush()
        print(f"Created {len(items)} menu items")
        
        # Create options for some items
        # Add options for قورمه‌سبزی
        ghormeh = next(i for i in items if i.name == "قورمه‌سبزی")
        ghormeh_options = [
            {"name": "برنج اضافه", "price_adjustment_toman": 30000, "price_adjustment_rial": 300000, "is_required": False, "display_order": 1},
            {"name": "ماست اضافه", "price_adjustment_toman": 20000, "price_adjustment_rial": 200000, "is_required": False, "display_order": 2},
            {"name": "ترشی اضافه", "price_adjustment_toman": 15000, "price_adjustment_rial": 150000, "is_required": False, "display_order": 3},
        ]
        for opt in ghormeh_options:
            option = MenuItemOption(
                menu_item_id=ghormeh.id,
                name=opt["name"],
                price_adjustment_toman=opt["price_adjustment_toman"],
                price_adjustment_rial=opt["price_adjustment_rial"],
                is_required=opt["is_required"],
                display_order=opt["display_order"],
                options_config={},
            )
            db.add(option)
        
        # Add options for چلوکباب کوبیده
        kabab = next(i for i in items if i.name == "چلوکباب کوبیده")
        kabab_options = [
            {"name": "جوجه کباب اضافه", "price_adjustment_toman": 120000, "price_adjustment_rial": 1200000, "is_required": False, "display_order": 1},
            {"name": "برنج اضافه", "price_adjustment_toman": 30000, "price_adjustment_rial": 300000, "is_required": False, "display_order": 2},
            {"name": "سیر و ترشی", "price_adjustment_toman": 15000, "price_adjustment_rial": 150000, "is_required": False, "display_order": 3},
        ]
        for opt in kabab_options:
            option = MenuItemOption(
                menu_item_id=kabab.id,
                name=opt["name"],
                price_adjustment_toman=opt["price_adjustment_toman"],
                price_adjustment_rial=opt["price_adjustment_rial"],
                is_required=opt["is_required"],
                display_order=opt["display_order"],
                options_config={},
            )
            db.add(option)
        
        await db.flush()
        print("Created menu item options")
        
        # Create QR codes for tables
        qr_codes = []
        for table in tables:
            qr = QRCode(
                restaurant_id=restaurant.id,
                branch_id=branch.id,
                table_id=table.id,
                label=f"میز {table.name}",
                is_active=True,
            )
            db.add(qr)
            qr_codes.append(qr)
        await db.flush()
        print(f"Created {len(qr_codes)} QR codes")
        
        # Print QR tokens for testing
        for qr in qr_codes:
            print(f"QR for {qr.label}: {qr.token}")
        
        await db.commit()
        print("\n✅ Seed completed successfully!")
        
        # Print summary
        print("\n=== DEMO DATA SUMMARY ===")
        print(f"User: demo@example.com / demo123456 (superuser)")
        print(f"Restaurant: {restaurant.name} (slug: {restaurant.slug})")
        print(f"Branch: {branch.name} (code: {branch.code})")
        print(f"Tables: {len(tables)} tables")
        print(f"Categories: {len(categories)}")
        print(f"Menu Items: {len(items)}")
        print(f"QR Codes: {len(qr_codes)}")
        print("\nTest URLs:")
        for qr in qr_codes[:3]:
            print(f"  http://localhost:8000/api/v1/public/qr/{qr.token}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_database())