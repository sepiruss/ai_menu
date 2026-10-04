from datetime import datetime, timezone
from typing import TYPE_CHECKING
import secrets
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, JSON, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.core.models.customer import Customer
    from app.core.models.restaurant import Restaurant
    from app.core.models.branch import Branch
    from app.core.models.table import Table
    from app.core.models.customer_event import CustomerEvent
    from app.core.models.cart import Cart
    from app.core.models.order import Order


class CustomerSession(Base):
    __tablename__ = "customer_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    restaurant_id: Mapped[int] = mapped_column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    table_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tables.id", ondelete="SET NULL"), nullable=True, index=True)
    session_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    device_info: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    customer: Mapped["Customer | None"] = relationship("Customer", back_populates="sessions")
    restaurant: Mapped["Restaurant"] = relationship("Restaurant")
    branch: Mapped["Branch"] = relationship("Branch")
    table: Mapped["Table | None"] = relationship("Table")
    events: Mapped[list["CustomerEvent"]] = relationship("CustomerEvent", back_populates="session", cascade="all, delete-orphan")
    carts: Mapped[list["Cart"]] = relationship("Cart", back_populates="customer_session", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer_session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_customer_sessions_restaurant_branch", "restaurant_id", "branch_id"),
        Index("ix_customer_sessions_token_active", "session_token", "is_active"),
        Index("ix_customer_sessions_customer_active", "customer_id", "is_active"),
        UniqueConstraint("session_token", name="uq_customer_sessions_token"),
    )

    def __repr__(self) -> str:
        return f"<CustomerSession(id={self.id}, token={self.session_token[:8]}..., restaurant_id={self.restaurant_id}, branch_id={self.branch_id})>"

    @classmethod
    def generate_token(cls) -> str:
        return secrets.token_urlsafe(32)