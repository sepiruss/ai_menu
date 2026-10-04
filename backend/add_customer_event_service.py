import sys

with open('C:/Users/s.daemi/Documents/sepehrProject/backend/app/modules/public/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'class CustomerEventService' in content:
    print('Already exists')
    sys.exit(0)

new_class = '''

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
'''

with open('C:/Users/s.daemi/Documents/sepehrProject/backend/app/modules/public/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'class CustomerEventService' not in content:
    content = content.rstrip() + '\n\n' + new_class
    with open('C:/Users/s.daemi/Documents/sepehrProject/backend/app/modules/public/service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Added CustomerEventService")
else:
    print("Already exists")