from datetime import datetime, timezone
from typing import TYPE_CHECKING
import secrets
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.core.models.restaurant import Restaurant
    from app.core.models.branch import Branch
    from app.core.models.table import Table


class QRCode(Base):
    __tablename__ = "qr_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    branch_id: Mapped[int] = mapped_column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False, index=True)
    table_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tables.id", ondelete="SET NULL"), nullable=True, index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    restaurant: Mapped["Restaurant"] = relationship("Restaurant")
    branch: Mapped["Branch"] = relationship("Branch")
    table: Mapped["Table | None"] = relationship("Table")

    __table_args__ = (
        Index("ix_qr_codes_restaurant_branch", "restaurant_id", "branch_id"),
        Index("ix_qr_codes_token_active", "token", "is_active"),
        UniqueConstraint("token", name="uq_qr_codes_token"),
    )

    def __repr__(self) -> str:
        return f"<QRCode(id={self.id}, token={self.token[:8]}..., restaurant_id={self.restaurant_id}, branch_id={self.branch_id})>"

    @classmethod
    def generate_token(cls) -> str:
        return secrets.token_urlsafe(32)