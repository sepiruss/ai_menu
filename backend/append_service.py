with open('/Users/s.daemi/Documents/sepehrProject/backend/app/modules/public/service.py', 'r') as f:
    content = f.read()

if 'class CartService' in content:
    print('Already exists')
else:
    new_classes = '''

class CartService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_cart(
        self,
        session_id: int,
        restaurant_id: int,
        branch_id: int,
        table_id: Optional[int] = None,
    ) -> Cart:
        result = await self.db.execute(
            select(Cart).where(
                Cart.customer_session_id == session_id,
                Cart.is_active == True
            )
        )
        cart = result.scalar_one_or_none()
        
        if cart:
            if table_id and not cart.table_id:
                cart.table_id = table_id
                await self.db.commit()
                await self.db.refresh(cart)
            return cart
        
        cart = Cart(
            customer_session_id=session_id,
            restaurant_id=restaurant_id,
            branch_id=branch_id,
            table_id=table_id,
        )
        self.db.add(cart)
        await self.db.commit()
        await self.db.refresh(cart)
        return cart

    async def get_cart(self, session_id: int) -> Cart | None:
        result = await self.db.execute(
            select(Cart)
            .options(selectinload(Cart.items).selectinload(CartItem.menu_item))
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
        table_id: Optional[int] = None,
    ) -> CartItem:
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
        
        result = await self.db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.menu_item_id == menu_item_id
            )
        )
        existing_item = result.scalar_one_or_none()
        
        if existing_item:
            existing_item.quantity += quantity
            existing_item.updated_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(existing_item)
            return existing_item
        
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
                        "is_required": option.is_required,
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
        await self.db.commit()
        await self.db.refresh(cart_item)
        
        return cart_item

    async def update_item(
        self,
        session_id: int,
        cart_item_id: int,
        quantity: Optional[int] = None,
        selected_options: Optional[list[dict]] = None,
    ) -> CartItem:
        cart = await self.get_cart(session_id)
        if not cart:
            raise ValidationException("Cart not found")
        
        result = await self.db.execute(
            select(CartItem).where(CartItem.id == cart_item_id, CartItem.cart_id == cart.id)
        )
        cart_item = result.scalar_one_or_none()
        if not cart_item:
            raise NotFoundException("CartItem", cart_item_id)
        
        if quantity is not None:
            if quantity <= 0:
                raise ValidationException("Quantity must be greater than 0")
            cart_item.quantity = quantity
        
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
                            "is_required": option.is_required,
                        })
            
            cart_item.selected_options = selected_options_snapshot
            cart_item.options_price_adjustment_toman = options_price_toman
            cart_item.options_price_adjustment_rial = options_price_rial
        
        cart_item.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(cart_item)
        return cart_item

    async def remove_item(self, session_id: int, cart_item_id: int) -> None:
        cart = await self.get_cart(session_id)
        if not cart:
            raise ValidationException("Cart not found")
        
        result = await self.db.execute(
            select(CartItem).where(CartItem.id == cart_item_id, CartItem.cart_id == cart.id)
        )
        cart_item = result.scalar_one_or_none()
        if not cart_item:
            raise NotFoundException("CartItem", cart_item_id)
        
        await self.db.delete(cart_item)
        await self.db.commit()

    async def clear_cart(self, session_id: int) -> None:
        cart = await self.get_cart(session_id)
        if not cart:
            return
        
        cart.is_active = False
        await self.db.commit()

    async def calculate_cart_totals(self, cart: Cart) -> tuple[Decimal, Decimal]:
        subtotal_toman = Decimal("0")
        subtotal_rial = Decimal("0")
        
        for item in cart.items:
            item_subtotal_toman = item.unit_price_toman * item.quantity + item.options_price_adjustment_toman * item.quantity
            item_subtotal_rial = item.unit_price_rial * item.quantity + item.options_price_adjustment_rial * item.quantity
            subtotal_toman += item_subtotal_toman
            subtotal_rial += item_subtotal_rial
        
        return subtotal_toman, subtotal_rial


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_order_number(self) -> str:
        import uuid
        return f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

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
            .options(selectinload(Cart.items).selectinload(CartItem.menu_item))
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
            order_number=f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(__import__('uuid').uuid4())[:8].upper()}",
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

    async def get_order(self, order_id: int, session_id: Optional[int] = None) -> Order:
        query = select(Order).options(
            selectinload(Order.items).selectinload(OrderItem.menu_item)
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
        session_id: int,
        page: int = 1,
        page_size: int = 20,
        status: Optional[OrderStatus] = None,
    ) -> tuple[list[Order], int]:
        query = select(Order).where(Order.customer_session_id == session_id)
        
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
        order_id: int,
        new_status: OrderStatus,
        internal_note: Optional[str] = None,
        restaurant_id: Optional[int] = None,
    ) -> Order:
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
            raise ValidationException(f"Cannot transition from {order.status} to {new_status}")
        
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
        order_id: int,
        session_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Order:
        order = await self.get_order(order_id, session_id)
        
        if order.status in [OrderStatus.SERVED, OrderStatus.CANCELLED]:
            raise ValidationException(f"Cannot cancel order in {order.status} status")
        
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.now(timezone.utc)
        order.cancellation_reason = reason
        
        await self.db.commit()
        await self.db.refresh(order)
        return order
"

with open('/Users/s.daemi/Documents/sepehrProject/backend/app/modules/public/service.py', 'r') as f:
    content = f.read()

if 'class CartService' not in content:
    content = content.rstrip() + new_classes
    with open('/Users/s.daemi/Documents/sepehrProject/backend/app/modules/public/service.py', 'w') as f:
        f.write(content)
    print("Added CartService and OrderService")
else:
    print("Already exists")