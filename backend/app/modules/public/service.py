from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from decimal import Decimal
from app.core.exceptions import NotFoundException, ValidationException
from app.core.models import (
    QRCode, Customer, CustomerSession, CustomerEvent, 
    Restaurant, Branch, Table, Menu, Category, MenuItem, MenuItemOption,
    Cart, CartItem, Order, OrderItem, OrderStatus
)
from app.modules.public.schemas import (
    QRCodeCreate, QRCodeUpdate, CustomerCreate, CustomerUpdate,
    CustomerSessionCreate, QRResolveRequest, PublicSearchRequest,
    CustomerEventCreate, CustomerEventType
)


class QRCodeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: QRCodeCreate) -> QRCode:
        # Verify restaurant and branch exist
        restaurant = await self.db.get(Restaurant, data.restaurant_id)
        if not restaurant:
            raise NotFoundException("Restaurant", data.restaurant_id)
        
        branch = await self.db.get(Branch, data.branch_id)
        if not branch or branch.restaurant_id != data.restaurant_id:
            raise NotFoundException("Branch", data.branch_id)
        
        if data.table_id:
            table = await self.db.get(Table, data.table_id)
            if not table or table.branch_id != data.branch_id:
                raise NotFoundException("Table", data.table_id)
        
        qr_code = QRCode(
            restaurant_id=data.restaurant_id,
            branch_id=data.branch_id,
            table_id=data.table_id,
            token=QRCode.generate_token(),
            label=data.label,
            expires_at=data.expires_at,
        )
        self.db.add(qr_code)
        await self.db.commit()
        await self.db.refresh(qr_code)
        return qr_code

    async def get_by_token(self, token: str) -> QRCode:
        result = await self.db.execute(
            select(QRCode)
            .options(
                selectinload(QRCode.restaurant),
                selectinload(QRCode.branch),
                selectinload(QRCode.table)
            )
            .where(QRCode.token == token)
        )
        qr_code = result.scalar_one_or_none()
        if not qr_code:
            raise NotFoundException("QRCode", token)
        return qr_code

    async def get_by_id(self, qr_id: int, restaurant_id: int) -> QRCode:
        result = await self.db.execute(
            select(QRCode).where(QRCode.id == qr_id, QRCode.restaurant_id == restaurant_id)
        )
        qr_code = result.scalar_one_or_none()
        if not qr_code:
            raise NotFoundException("QRCode", qr_id)
        return qr_code

    async def list(
        self,
        restaurant_id: int,
        branch_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
    ) -> tuple[list[QRCode], int]:
        query = select(QRCode).where(QRCode.restaurant_id == restaurant_id)
        
        if branch_id:
            query = query.where(QRCode.branch_id == branch_id)
        if is_active is not None:
            query = query.where(QRCode.is_active == is_active)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0
        
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(QRCode.created_at.desc())
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total

    async def update(self, qr_id: int, data: QRCodeUpdate, restaurant_id: int) -> QRCode:
        qr_code = await self.get_by_id(qr_id, restaurant_id)
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(qr_code, field, value)
        
        await self.db.commit()
        await self.db.refresh(qr_code)
        return qr_code

    async def delete(self, qr_id: int, restaurant_id: int) -> None:
        qr_code = await self.get_by_id(qr_id, restaurant_id)
        qr_code.is_active = False
        await self.db.commit()


class CustomerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: CustomerCreate, restaurant_id: int) -> Customer:
        customer = Customer(
            restaurant_id=restaurant_id,
            external_id=data.external_id,
            display_name=data.display_name,
            language=data.language,
            preferences=data.preferences,
        )
        self.db.add(customer)
        await self.db.commit()
        await self.db.refresh(customer)
        return customer

    async def get_by_id(self, customer_id: int, restaurant_id: int) -> Customer:
        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id, Customer.restaurant_id == restaurant_id)
        )
        customer = result.scalar_one_or_none()
        if not customer:
            raise NotFoundException("Customer", customer_id)
        return customer

    async def get_by_external_id(self, external_id: str, restaurant_id: int) -> Customer | None:
        result = await self.db.execute(
            select(Customer).where(
                Customer.external_id == external_id,
                Customer.restaurant_id == restaurant_id
            )
        )
        return result.scalar_one_or_none()

    async def update(self, customer_id: int, data: CustomerUpdate, restaurant_id: int) -> Customer:
        customer = await self.get_by_id(customer_id, restaurant_id)
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(customer, field, value)
        
        await self.db.commit()
        await self.db.refresh(customer)
        return customer

    async def list(
        self,
        restaurant_id: int,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
    ) -> tuple[list[Customer], int]:
        query = select(Customer).where(Customer.restaurant_id == restaurant_id)
        
        if is_active is not None:
            query = query.where(Customer.is_active == is_active)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0
        
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Customer.created_at.desc())
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total


class CustomerSessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_or_get(
        self,
        restaurant_id: int,
        branch_id: int,
        table_id: Optional[int] = None,
        session_token: Optional[str] = None,
        customer_id: Optional[int] = None,
        device_info: Optional[dict] = None,
    ) -> CustomerSession:
        # If session token provided, try to find existing session
        if session_token:
            result = await self.db.execute(
                select(CustomerSession)
                .options(selectinload(CustomerSession.customer))
                .where(CustomerSession.session_token == session_token)
            )
            session = result.scalar_one_or_none()
            if session and session.is_active and session.restaurant_id == restaurant_id:
                # Update last activity
                session.last_activity_at = datetime.now(timezone.utc)
                if table_id and not session.table_id:
                    session.table_id = table_id
                if device_info:
                    session.device_info = device_info
                await self.db.commit()
                await self.db.refresh(session)
                return session
        
        # Create new session
        if not customer_id:
            # Create anonymous customer
            customer = Customer(
                restaurant_id=restaurant_id,
                display_name=None,
            )
            self.db.add(customer)
            await self.db.flush()
            customer_id = customer.id
        
        session = CustomerSession(
            customer_id=customer_id,
            restaurant_id=restaurant_id,
            branch_id=branch_id,
            table_id=table_id,
            session_token=CustomerSession.generate_token(),
            device_info=device_info or {},
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.db.add(session)
        await self.db.commit()
        
        # Reload with customer relationship
        result = await self.db.execute(
            select(CustomerSession)
            .options(selectinload(CustomerSession.customer))
            .where(CustomerSession.id == session.id)
        )
        return result.scalar_one()

    async def get_by_token(self, session_token: str) -> CustomerSession | None:
        result = await self.db.execute(
            select(CustomerSession)
            .options(
                selectinload(CustomerSession.customer),
                selectinload(CustomerSession.restaurant),
                selectinload(CustomerSession.branch),
                selectinload(CustomerSession.table)
            )
            .where(CustomerSession.session_token == session_token)
        )
        session = result.scalar_one_or_none()
        if session and session.is_active:
            # Check if session is expired
            expires_at = session.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                session.is_active = False
                await self.db.commit()
                return None
        return session

    async def refresh(self, session_token: str) -> CustomerSession | None:
        session = await self.get_by_token(session_token)
        if session and session.is_active:
            if session.expires_at > datetime.now(timezone.utc):
                session.last_activity_at = datetime.now(timezone.utc)
                session.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
                await self.db.commit()
                await self.db.refresh(session)
                return session
            else:
                session.is_active = False
                await self.db.commit()
        return None


class PublicMenuService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_public_menu(self, branch_id: int, restaurant_id: int) -> Menu | None:
        """Get the active/default public menu for a branch"""
        result = await self.db.execute(
            select(Menu)
            .options(
                selectinload(Menu.categories)
                .selectinload(Category.items)
                .selectinload(MenuItem.options)
            )
            .where(
                Menu.branch_id == branch_id,
                Menu.is_active == True,
                Menu.is_default == True
            )
        )
        menu = result.scalar_one_or_none()
        
        if not menu:
            # Fallback to any active menu
            result = await self.db.execute(
                select(Menu)
                .options(
                    selectinload(Menu.categories)
                    .selectinload(Category.items)
                    .selectinload(MenuItem.options)
                )
                .where(Menu.branch_id == branch_id, Menu.is_active == True)
                .order_by(Menu.is_default.desc(), Menu.created_at.desc())
            )
            menu = result.scalar_one_or_none()
        
        if not menu:
            return None
        
        # Filter categories to only visible ones
        menu.categories = [c for c in menu.categories if c.is_visible]
        
        # Filter items to only available ones
        for category in menu.categories:
            category.items = [item for item in category.items if item.is_available]
        
        return menu

    async def get_categories(self, menu_id: int, parent_id: Optional[int] = None) -> list[Category]:
        query = select(Category).where(
            Category.menu_id == menu_id,
            Category.is_visible == True
        )
        if parent_id is not None:
            query = query.where(Category.parent_id == parent_id)
        else:
            query = query.where(Category.parent_id.is_(None))
        
        query = query.order_by(Category.display_order, Category.id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_category_tree(self, menu_id: int) -> list[Category]:
        result = await self.db.execute(
            select(Category)
            .where(Category.menu_id == menu_id, Category.is_visible == True)
            .order_by(Category.display_order, Category.id)
        )
        all_categories = result.scalars().all()
        
        # Build tree using a separate dict to avoid lazy loading issues
        children_map: dict[int, list[Category]] = {cat.id: [] for cat in all_categories}
        
        for cat in all_categories:
            if cat.parent_id is not None:
                children_map[cat.parent_id].append(cat)
        
        # Return root categories
        root_categories = [cat for cat in all_categories if cat.parent_id is None]
        
        # Attach children map to ALL categories for the response builder
        for cat in all_categories:
            cat._children_map = children_map
        
        return root_categories

    async def get_items(
        self,
        category_id: int,
        page: int = 1,
        page_size: int = 20,
        is_available: bool | None = True,
        is_popular: bool | None = None,
        is_new: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[MenuItem], int]:
        query = select(MenuItem).options(
            selectinload(MenuItem.options)
        ).where(MenuItem.category_id == category_id)
        
        if is_available is not None:
            query = query.where(MenuItem.is_available == is_available)
        if is_popular is not None:
            query = query.where(MenuItem.is_popular == is_popular)
        if is_new is not None:
            query = query.where(MenuItem.is_new == is_new)
        if search:
            query = query.where(MenuItem.name.ilike(f"%{search}%"))
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0
        
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(
            MenuItem.display_order, MenuItem.id
        )
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total

    async def get_item_by_id(self, item_id: int, category_id: Optional[int] = None) -> MenuItem | None:
        query = select(MenuItem).options(
            selectinload(MenuItem.options)
        ).where(MenuItem.id == item_id, MenuItem.is_available == True)
        
        if category_id:
            query = query.where(MenuItem.category_id == category_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def search_items(
        self,
        branch_id: int,
        query: str,
        category_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[MenuItem], int]:
        # Get active menu for branch
        menu_result = await self.db.execute(
            select(Menu.id).where(Menu.branch_id == branch_id, Menu.is_active == True)
        )
        menu_ids = [row[0] for row in menu_result.all()]
        
        if not menu_ids:
            return [], 0
        
        # Get categories in these menus
        cat_result = await self.db.execute(
            select(Category.id).where(Category.menu_id.in_(menu_ids), Category.is_visible == True)
        )
        category_ids = [row[0] for row in cat_result.all()]
        
        if category_id:
            if category_id not in category_ids:
                return [], 0
            category_ids = [category_id]
        
        if not category_ids:
            return [], 0
        
        # Search items
        base_query = select(MenuItem).options(
            selectinload(MenuItem.options)
        ).where(
            MenuItem.category_id.in_(category_ids),
            MenuItem.is_available == True,
            MenuItem.name.ilike(f"%{query}%")
        )
        
        count_query = select(func.count()).select_from(base_query.subquery())
        total = await self.db.scalar(count_query) or 0
        
        base_query = base_query.offset((page - 1) * page_size).limit(page_size).order_by(
            MenuItem.display_order, MenuItem.id
        )
        result = await self.db.execute(base_query)
        items = result.scalars().all()
        
        return list(items), total


class CartService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_cart(self, session_id: int, restaurant_id: int, branch_id: int, table_id: int | None = None) -> Cart:
        from sqlalchemy import select
        from app.core.models import Cart
        result = await self.db.execute(select(Cart).where(Cart.customer_session_id == session_id, Cart.is_active == True))
        cart = result.scalar_one_or_none()
        if cart:
            return cart
        cart = Cart(customer_session_id=session_id, restaurant_id=restaurant_id, branch_id=branch_id, table_id=table_id)
        self.db.add(cart)
        await self.db.flush()
        await self.db.refresh(cart)
        return cart

    async def get_cart(self, session_id: int) -> Cart | None:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.core.models import Cart, CartItem, MenuItem, MenuItemOption
        result = await self.db.execute(
            select(Cart)
            .options(
                selectinload(Cart.items)
                .selectinload(CartItem.menu_item)
                .selectinload(MenuItem.options)
            )
            .where(Cart.customer_session_id == session_id, Cart.is_active == True)
        )
        return result.scalar_one_or_none()

    async def add_item(
        self,
        session_id: int,
        menu_item_id: int,
        quantity: int,
        selected_options: list[dict],
        restaurant_id: int,
        branch_id: int,
        table_id: int | None = None,
    ) -> CartItem:
        from app.core.models import MenuItem, CartItem, CustomerSession, MenuItemOption
        from app.core.exceptions import NotFoundException, ValidationException
        from decimal import Decimal
        
        menu_item = await self.db.get(MenuItem, menu_item_id)
        if not menu_item:
            raise NotFoundException("MenuItem", menu_item_id)
        if not menu_item.category:
            raise ValidationException("Menu item has no category")
        if not menu_item.category.menu:
            raise ValidationException("Menu item category has no menu")
        if menu_item.category.menu.branch_id != branch_id:
            raise ValidationException("Menu item does not belong to this branch")
        if menu_item.category.menu.branch.restaurant_id != restaurant_id:
            raise ValidationException("Menu item does not belong to this restaurant")
        if not menu_item.is_available:
            raise ValidationException("Menu item is not available")
        if quantity <= 0:
            raise ValidationException("Quantity must be greater than 0")
        
        session = await self.db.get(CustomerSession, session_id)
        if not session or not session.is_active:
            raise ValidationException("Invalid or expired session")
        
        cart = await self.get_or_create_cart(session_id, restaurant_id, branch_id, table_id)
        
        # Check if item already exists in cart
        result = await self.db.execute(
            select(CartItem).where(CartItem.cart_id == cart.id, CartItem.menu_item_id == menu_item_id)
        )
        existing_item = result.scalar_one_or_none()
        if existing_item:
            existing_item.quantity += quantity
            existing_item.updated_at = datetime.now(timezone.utc)
            await self.db.flush()
            await self.db.refresh(existing_item)
            # Eagerly load relationships for serialization
            await self.db.refresh(existing_item, attribute_names=['menu_item'])
            if existing_item.menu_item:
                await self.db.refresh(existing_item.menu_item, attribute_names=['options'])
            return existing_item
        
        # Calculate option price adjustments
        options_price_toman = Decimal("0")
        options_price_rial = Decimal("0")
        selected_options_snapshot = []
        
        for opt_data in selected_options:
            option_id = opt_data.get("option_id")
            if option_id:
                option = await self.db.get(MenuItemOption, option_id)
                if option and option.menu_item_id == menu_item_id:
                    options_price_toman += option.price_adjustment_toman
                    options_price_rial += option.price_adjustment_rial
                    selected_options_snapshot.append({
                        "option_id": option.id,
                        "name": option.name,
                        "price_adjustment_toman": str(option.price_adjustment_toman),
                        "price_adjustment_rial": str(option.price_adjustment_rial),
                        "is_required": option.is_required
                    })
        
        cart_item = CartItem(
            cart_id=cart.id,
            menu_item_id=menu_item_id,
            quantity=quantity,
            unit_price_toman=menu_item.price_toman,
            unit_price_rial=menu_item.price_rial,
            selected_options=selected_options_snapshot,
            item_name_snapshot=menu_item.name,
            options_price_adjustment_toman=options_price_toman,
            options_price_adjustment_rial=options_price_rial,
        )
        self.db.add(cart_item)
        await self.db.flush()
        await self.db.refresh(cart_item)
        # Eagerly load relationships for serialization
        await self.db.refresh(cart_item, attribute_names=['menu_item'])
        if cart_item.menu_item:
            await self.db.refresh(cart_item.menu_item, attribute_names=['options'])
        return cart_item

    async def update_item(
        self,
        session_id: int,
        cart_item_id: int,
        quantity: int | None = None,
        selected_options: list[dict] | None = None,
    ) -> CartItem:
        from app.core.models import CartItem, Cart, MenuItemOption
        from app.core.exceptions import NotFoundException, ValidationException
        from decimal import Decimal
        
        # Get cart
        cart = await self.get_cart(session_id)
        if not cart:
            raise NotFoundException("Cart", "not found")
        
        # Get cart item
        result = await self.db.execute(
            select(CartItem).where(CartItem.id == cart_item_id, CartItem.cart_id == cart.id)
        )
        cart_item = result.scalar_one_or_none()
        if not cart_item:
            raise NotFoundException("CartItem", cart_item_id)
        
        # Update quantity if provided
        if quantity is not None:
            if quantity <= 0:
                raise ValidationException("Quantity must be greater than 0")
            cart_item.quantity = quantity
        
        # Update selected options if provided
        if selected_options is not None:
            options_price_toman = Decimal("0")
            options_price_rial = Decimal("0")
            selected_options_snapshot = []
            
            for opt_data in selected_options:
                option_id = opt_data.get("option_id")
                if option_id:
                    option = await self.db.get(MenuItemOption, option_id)
                    if option and option.menu_item_id == cart_item.menu_item_id:
                        options_price_toman += option.price_adjustment_toman
                        options_price_rial += option.price_adjustment_rial
                        selected_options_snapshot.append({
                            "option_id": option.id,
                            "name": option.name,
                            "price_adjustment_toman": str(option.price_adjustment_toman),
                            "price_adjustment_rial": str(option.price_adjustment_rial),
                            "is_required": option.is_required
                        })
            
            cart_item.options_price_adjustment_toman = options_price_toman
            cart_item.options_price_adjustment_rial = options_price_rial
            cart_item.selected_options = selected_options_snapshot
        
        cart_item.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(cart_item)
        # Eagerly load relationships for serialization
        await self.db.refresh(cart_item, attribute_names=['menu_item'])
        if cart_item.menu_item:
            await self.db.refresh(cart_item.menu_item, attribute_names=['options'])
        return cart_item

    async def remove_item(self, session_id: int, cart_item_id: int) -> None:
        from app.core.models import CartItem, Cart
        from app.core.exceptions import NotFoundException
        
        cart = await self.get_cart(session_id)
        if not cart:
            raise NotFoundException("Cart", "not found")
        
        result = await self.db.execute(
            select(CartItem).where(CartItem.id == cart_item_id, CartItem.cart_id == cart.id)
        )
        cart_item = result.scalar_one_or_none()
        if not cart_item:
            raise NotFoundException("CartItem", cart_item_id)
        
        await self.db.delete(cart_item)
        await self.db.flush()

    async def clear_cart(self, session_id: int) -> None:
        from app.core.models import CartItem, Cart
        from app.core.exceptions import NotFoundException
        
        cart = await self.get_cart(session_id)
        if not cart:
            raise NotFoundException("Cart", "not found")
        
        # Delete all cart items
        from sqlalchemy import delete
        await self.db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        
        # Deactivate cart
        cart.is_active = False
        await self.db.flush()

# Note: Full CartService and OrderService implementations should be added properly
# This is a minimal placeholder to allow the app to run



class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_order_number(self):
        import uuid
        return "ORD-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + str(__import__("uuid").uuid4())[:8].upper()

    async def create_order(
        self,
        session_id: int,
        idempotency_key: Optional[str] = None,
        customer_note: Optional[str] = None,
    ) -> Order:
        if idempotency_key:
            existing = await self.db.execute(
                select(Order).where(Order.idempotency_key == idempotency_key)
            )
            existing_order = existing.scalar_one_or_none()
            if existing_order:
                return existing_order
        
        session = await self.db.get(CustomerSession, session_id)
        if not session or not session.is_active:
            raise ValidationException("Invalid or expired session")
        
        cart_result = await self.db.execute(
            select(Cart)
            .options(
                selectinload(Cart.items)
                .selectinload(CartItem.menu_item)
                .selectinload(MenuItem.options)
            )
            .where(Cart.customer_session_id == session_id, Cart.is_active == True)
        )
        cart = cart_result.scalar_one_or_none()
        if not cart or not cart.items:
            raise ValidationException("Cart is empty")
        
        for item in cart.items:
            menu_item = await self.db.get(MenuItem, item.menu_item_id)
            if not menu_item or not menu_item.is_available:
                raise ValidationException(f"Item '{item.item_name_snapshot}' is no longer available")
            
            for opt_data in item.selected_options:
                opt_id = opt_data.get("option_id")
                if opt_id:
                    option = await self.db.get(MenuItemOption, opt_id)
                    if not option or option.menu_item_id != item.menu_item_id:
                        raise ValidationException("Selected option is no longer valid")
        
        subtotal_toman = Decimal("0")
        subtotal_rial = Decimal("0")
        
        for item in cart.items:
            item_subtotal_toman = item.unit_price_toman * item.quantity + item.options_price_adjustment_toman * item.quantity
            item_subtotal_rial = item.unit_price_rial * item.quantity + item.options_price_adjustment_rial * item.quantity
            subtotal_toman += item_subtotal_toman
            subtotal_rial += item_subtotal_rial
        
        order = Order(
            customer_id=session.customer_id,
            customer_session_id=session_id,
            restaurant_id=session.restaurant_id,
            branch_id=session.branch_id,
            table_id=session.table_id,
            order_number="ORD-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + str(__import__("uuid").uuid4())[:8].upper(),
            status=OrderStatus.PENDING,
            subtotal_toman=subtotal_toman,
            subtotal_rial=subtotal_rial,
            total_toman=subtotal_toman,
            total_rial=subtotal_rial,
            currency="IRR",
            customer_note=customer_note,
            idempotency_key=idempotency_key,
        )
        
        self.db.add(order)
        await self.db.flush()
        
        for item in cart.items:
            item_subtotal_toman = item.unit_price_toman * item.quantity + item.options_price_adjustment_toman * item.quantity
            item_subtotal_rial = item.unit_price_rial * item.quantity + item.options_price_adjustment_rial * item.quantity
            
            options_snapshot = []
            for opt_data in item.selected_options:
                options_snapshot.append({
                    "option_id": opt_data.get("option_id"),
                    "name": opt_data.get("name"),
                    "price_adjustment_toman": opt_data.get("price_adjustment_toman"),
                    "price_adjustment_rial": opt_data.get("price_adjustment_rial"),
                    "is_required": opt_data.get("is_required"),
                })
            
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item.menu_item_id,
                item_name=item.item_name_snapshot,
                item_description=item.menu_item.description if item.menu_item else None,
                quantity=item.quantity,
                unit_price_toman=item.unit_price_toman,
                unit_price_rial=item.unit_price_rial,
                selected_options=options_snapshot,
                options_price_adjustment_toman=item.options_price_adjustment_toman,
                options_price_adjustment_rial=item.options_price_adjustment_rial,
                subtotal_toman=item_subtotal_toman,
                subtotal_rial=item_subtotal_rial,
            )
            self.db.add(order_item)
        
        cart.is_active = False
        
        await self.db.commit()
        await self.db.refresh(order)
        
        return order

    async def get_order(self, order_id, session_id=None):
        query = select(Order).options(
            selectinload(Order.items)
            .selectinload(OrderItem.menu_item)
            .selectinload(MenuItem.options)
        ).where(Order.id == order_id)
        
        if session_id:
            query = query.where(Order.customer_session_id == session_id)
        
        result = await self.db.execute(query)
        order = result.scalar_one_or_none()
        if not order:
            raise NotFoundException("Order", order_id)
        return order

    async def list_orders(
        self,
        session_id,
        page=1,
        page_size=20,
        status=None,
    ):
        query = select(Order).options(
            selectinload(Order.items)
            .selectinload(OrderItem.menu_item)
            .selectinload(MenuItem.options)
        ).where(Order.customer_session_id == session_id)
        
        if status:
            query = query.where(Order.status == status)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0
        
        query = query.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total

    async def update_order_status(
        self,
        order_id,
        new_status,
        internal_note=None,
        restaurant_id=None,
    ):
        order = await self.get_order(order_id)
        
        if restaurant_id and order.restaurant_id != restaurant_id:
            raise ValidationException("Order does not belong to this restaurant")
        
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
            OrderStatus.PREPARING: [OrderStatus.READY, OrderStatus.CANCELLED],
            OrderStatus.READY: [OrderStatus.SERVED, OrderStatus.CANCELLED],
            OrderStatus.SERVED: [],
            OrderStatus.CANCELLED: [],
        }
        
        if new_status not in valid_transitions.get(order.status, []):
            raise ValidationException("Cannot transition from " + str(order.status) + " to " + str(new_status))
        
        order.status = new_status
        
        now = datetime.now(timezone.utc)
        if new_status == OrderStatus.CONFIRMED:
            order.confirmed_at = now
        elif new_status == OrderStatus.PREPARING:
            order.preparing_at = now
        elif new_status == OrderStatus.READY:
            order.ready_at = now
        elif new_status == OrderStatus.SERVED:
            order.served_at = now
        elif new_status == OrderStatus.CANCELLED:
            order.cancelled_at = now
        
        if internal_note:
            order.internal_note = internal_note
        
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def cancel_order(
        self,
        order_id,
        session_id=None,
        reason=None,
    ):
        order = await self.get_order(order_id, session_id)
        
        if order.status in [OrderStatus.SERVED, OrderStatus.CANCELLED]:
            raise ValidationException("Cannot cancel order in " + str(order.status) + " status")
        
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.now(timezone.utc)
        order.cancellation_reason = reason
        
        await self.db.commit()
        await self.db.refresh(order)
        return order



class CustomerEventService:
    def __init__(self, db):
        self.db = db

    async def track_event(
        self,
        event_data,
        restaurant_id,
        branch_id,
        session_id=None,
        customer_id=None,
        table_id=None,
    ):
        from app.core.models import CustomerEvent
        event = CustomerEvent(
            customer_id=customer_id,
            session_id=session_id,
            restaurant_id=restaurant_id,
            branch_id=branch_id,
            table_id=table_id,
            event_type=event_data.event_type,
            menu_item_id=event_data.menu_item_id,
            category_id=event_data.category_id,
            event_metadata=event_data.metadata,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def list_events(
        self,
        restaurant_id,
        branch_id,
        session_id=None,
        customer_id=None,
        event_type=None,
        page=1,
        page_size=50,
    ):
        from sqlalchemy import select, func
        from app.core.models import CustomerEvent
        query = select(CustomerEvent).where(
            CustomerEvent.restaurant_id == restaurant_id,
            CustomerEvent.branch_id == branch_id,
        )
        
        if session_id:
            query = query.where(CustomerEvent.session_id == session_id)
        if customer_id:
            query = query.where(CustomerEvent.customer_id == customer_id)
        if event_type:
            query = query.where(CustomerEvent.event_type == event_type)
        
        from sqlalchemy import select as sa_select, func
        count_query = sa_select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0
        
        query = query.order_by(CustomerEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total
