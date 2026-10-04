from datetime import datetime, timezone
from typing import TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, JSON, Index, Numeric, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum

if TYPE_CHECKING:
    from app.core.models.customer import Customer
    from app.core.models.customer_session import CustomerSession
    from app.core.models.restaurant import Restaurant
    from app.core.models.branch import Branch
    from app.core.models.table import Table


class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY = "READY"
    SERVED = "SERVED"
    CANCELLED = "CANCELLED"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_session_id: Mapped[int] = mapped_column(Integer, ForeignKey("customer_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    restaurant_id: Mapped[int] = mapped_column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    table_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tables.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Order reference number
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    
    # Status
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, name="order_status"), nullable=False, default=OrderStatus.PENDING, index=True)
    
    # Financial
    subtotal_toman: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    subtotal_rial: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    discount_toman: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    discount_rial: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    total_toman: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    total_rial: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    
    # Currency
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="IRR")
    
    # Notes
    customer_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    internal_note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    
    # Idempotency
    idempotency_key: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    
    # Status timestamps
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preparing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    served_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Cancellation reason
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    customer: Mapped["Customer | None"] = relationship("Customer", back_populates="orders")
    customer_session: Mapped["CustomerSession"] = relationship("CustomerSession", back_populates="orders")
    restaurant: Mapped["Restaurant"] = relationship("Restaurant")
    branch: Mapped["Branch"] = relationship("Branch")
    table: Mapped["Table | None"] = relationship("Table")
    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_orders_session_status", "customer_session_id", "status"),
        Index("ix_orders_restaurant_branch_status", "restaurant_id", "branch_id", "status"),
        Index("ix_orders_created_at", "created_at"),
        UniqueConstraint("order_number", name="uq_orders_order_number"),
    )

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, order_number={self.order_number}, status={self.status}, total_toman={self.total_toman})>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("menu_items.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Item info snapshot at time of order
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    item_description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    
    # Quantity
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Price snapshots
    unit_price_toman: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    unit_price_rial: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # Selected options snapshot
    selected_options: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    
    # Option price adjustments snapshot
    options_price_adjustment_toman: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    options_price_adjustment_rial: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    
    # Subtotal
    subtotal_toman: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    subtotal_rial: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    menu_item: Mapped["MenuItem | None"] = relationship("MenuItem")

    __table_args__ = ()

    def __repr__(self) -> str:
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, item_name={self.item_name}, quantity={self.quantity})>"