from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.core.models.restaurant import Restaurant
    from app.core.models.customer_session import CustomerSession
    from app.core.models.customer_event import CustomerEvent
    from app.core.models.cart import Cart
    from app.core.models.order import Order


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)  # For future authenticated customer linking
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="fa")
    preferences: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    restaurant: Mapped["Restaurant"] = relationship("Restaurant")
    sessions: Mapped[list["CustomerSession"]] = relationship("CustomerSession", back_populates="customer", cascade="all, delete-orphan")
    events: Mapped[list["CustomerEvent"]] = relationship("CustomerEvent", back_populates="customer", cascade="all, delete-orphan")
    carts: Mapped[list["Cart"]] = relationship("Cart", back_populates="customer", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_customers_restaurant_active", "restaurant_id", "is_active"),
        Index("ix_customers_restaurant_external", "restaurant_id", "external_id"),
    )

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, restaurant_id={self.restaurant_id}, display_name={self.display_name})>"