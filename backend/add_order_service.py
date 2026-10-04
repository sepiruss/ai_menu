import sys

with open('C:/Users/s.daemi/Documents/sepehrProject/backend/app/modules/public/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'class OrderService' in content:
    print('Already exists')
    sys.exit(0)

# Find the end of the file and add OrderService
# First, remove the placeholder comment if it exists
content = content.replace('# Note: Full CartService and OrderService implementations should be added properly\n# This is a minimal placeholder to allow the app to run\n\n', '')

new_classes = '''

class OrderService:
    def __init__(self, db):
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
        session_id,
        page=1,
        page_size=20,
        status=None,
    ):
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
'''

with open('C:/Users/s.daemi/Documents/sepehrProject/backend/app/modules/public/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'class OrderService' not in content:
    # Remove placeholder comment if exists
    content = content.replace('# Note: Full CartService and OrderService implementations should be added properly\n# This is a minimal placeholder to allow the app to run\n\n', '')
    content = content.rstrip() + '\n\n' + new_classes
    with open('C:/Users/s.daemi/Documents/sepehrProject/backend/app/modules/public/service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added OrderService")
else:
    print("Already exists")