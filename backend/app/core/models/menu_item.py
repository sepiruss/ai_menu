from datetime import datetime, timezone
from typing import TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, JSON, Text, Numeric, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.core.models.category import Category


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_toman: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    price_rial: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_popular: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_new: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    item_metadata: Mapped[dict] = mapped_column("item_metadata", JSON, nullable=False, default=dict)
    allergens_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    category: Mapped["Category"] = relationship("Category", back_populates="items")
    options: Mapped[list["MenuItemOption"]] = relationship("MenuItemOption", back_populates="menu_item", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_menu_items_category_available", "category_id", "is_available"),
        Index("ix_menu_items_category_popular", "category_id", "is_popular"),
        Index("ix_menu_items_category_new", "category_id", "is_new"),
        Index("ix_menu_items_category_order", "category_id", "display_order"),
    )

    def __repr__(self) -> str:
        return f"<MenuItem(id={self.id}, name={self.name}, price_toman={self.price_toman})>"


class MenuItemOption(Base):
    __tablename__ = "menu_item_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    menu_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price_adjustment_toman: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    price_adjustment_rial: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    options_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    menu_item: Mapped["MenuItem"] = relationship("MenuItem", back_populates="options")

    __table_args__ = (
        Index("ix_menu_item_options_item_order", "menu_item_id", "display_order"),
    )

    def __repr__(self) -> str:
        return f"<MenuItemOption(id={self.id}, name={self.name}, menu_item_id={self.menu_item_id})>"