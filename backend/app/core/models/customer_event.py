from datetime import datetime, timezone
from typing import TYPE_CHECKING
from enum import Enum as PyEnum
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON, Index, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.core.models.customer import Customer
    from app.core.models.customer_session import CustomerSession
    from app.core.models.restaurant import Restaurant
    from app.core.models.branch import Branch
    from app.core.models.menu_item import MenuItem
    from app.core.models.category import Category


class CustomerEventType(str, PyEnum):
    MENU_VIEW = "MENU_VIEW"
    CATEGORY_VIEW = "CATEGORY_VIEW"
    ITEM_VIEW = "ITEM_VIEW"
    ITEM_SEARCH = "ITEM_SEARCH"
    ADD_TO_CART = "ADD_TO_CART"
    REMOVE_FROM_CART = "REMOVE_FROM_CART"
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_CANCELLED = "ORDER_CANCELLED"


class CustomerEvent(Base):
    __tablename__ = "customer_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("customer_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    restaurant_id: Mapped[int] = mapped_column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    table_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tables.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[CustomerEventType] = mapped_column(Enum(CustomerEventType, name="customer_event_type"), nullable=False, index=True)
    menu_item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("menu_items.id", ondelete="SET NULL"), nullable=True, index=True)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    event_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationships
    customer: Mapped["Customer | None"] = relationship("Customer", back_populates="events")
    session: Mapped["CustomerSession | None"] = relationship("CustomerSession", back_populates="events")
    restaurant: Mapped["Restaurant"] = relationship("Restaurant")
    branch: Mapped["Branch"] = relationship("Branch")
    table: Mapped["Table | None"] = relationship("Table")
    menu_item: Mapped["MenuItem | None"] = relationship("MenuItem")
    category: Mapped["Category | None"] = relationship("Category")

    __table_args__ = (
        Index("ix_customer_events_restaurant_branch_created", "restaurant_id", "branch_id", "created_at"),
        Index("ix_customer_events_session_created", "session_id", "created_at"),
        Index("ix_customer_events_type_created", "event_type", "created_at"),
        Index("ix_customer_events_item_created", "menu_item_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<CustomerEvent(id={self.id}, type={self.event_type}, restaurant_id={self.restaurant_id}, session_id={self.session_id})>"