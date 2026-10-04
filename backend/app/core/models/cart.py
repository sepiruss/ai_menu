from datetime import datetime, timezone
from typing import TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, JSON, Index, UniqueConstraint, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.core.models.customer_session import CustomerSession
    from app.core.models.restaurant import Restaurant
    from app.core.models.branch import Branch
    from app.core.models.table import Table
    from app.core.models.menu_item import MenuItem
    from app.core.models.menu_item import MenuItemOption


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_session_id: Mapped[int] = mapped_column(Integer, ForeignKey("customer_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    restaurant_id: Mapped[int] = mapped_column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    table_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tables.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    customer: Mapped["Customer | None"] = relationship("Customer", back_populates="carts")
    customer_session: Mapped["CustomerSession"] = relationship("CustomerSession", back_populates="carts")
    restaurant: Mapped["Restaurant"] = relationship("Restaurant")
    branch: Mapped["Branch"] = relationship("Branch")
    table: Mapped["Table | None"] = relationship("Table")
    items: Mapped[list["CartItem"]] = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_carts_session_active", "customer_session_id", "is_active"),
        Index("ix_carts_restaurant_branch", "restaurant_id", "branch_id"),
        UniqueConstraint("customer_session_id", name="uq_carts_customer_session"),
    )

    def __repr__(self) -> str:
        return f"<Cart(id={self.id}, session_id={self.customer_session_id}, restaurant_id={self.restaurant_id})>"


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True)
    menu_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("menu_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    
    # Price snapshots at time of adding to cart
    unit_price_toman: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    unit_price_rial: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # Selected options snapshot
    selected_options: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    
    # Item name snapshot for display
    item_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Option price adjustments snapshot
    options_price_adjustment_toman: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    options_price_adjustment_rial: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    menu_item: Mapped["MenuItem"] = relationship("MenuItem")

    __table_args__ = ()

    def __repr__(self) -> str:
        return f"<CartItem(id={self.id}, cart_id={self.cart_id}, menu_item_id={self.menu_item_id}, quantity={self.quantity})>"