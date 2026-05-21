from datetime import datetime
from decimal import Decimal

from sqlalchemy import ARRAY, BigInteger, Boolean, DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import SoftDeleteMixin, TimestampMixin


class SellerApplication(TimestampMixin, Base):
    __tablename__ = "seller_applications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    inn: Mapped[str] = mapped_column(String(20), nullable=False)
    business_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    desired_usernames: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    monthly_orders: Mapped[str | None] = mapped_column(String(50), nullable=True)
    referrer: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("admin_users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    seller_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sellers.id"), nullable=True)
    # Legal & auth fields set during application
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    legal_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    mfo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    oked: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Initial catalog + product submitted with application
    initial_catalog_name_uz: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_catalog_name_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_product_name_uz: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_product_name_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_product_description_uz: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_product_description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_product_sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    initial_product_is_featured: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False)
    initial_product_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_product_variants: Mapped[list | None] = mapped_column(JSON, nullable=True)


class Seller(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    inn: Mapped[str] = mapped_column(String(20), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    commission_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    suspended_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    application_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("seller_applications.id"), nullable=True
    )

    users: Mapped[list["SellerUser"]] = relationship("SellerUser", back_populates="seller")
    bots: Mapped[list["Bot"]] = relationship("Bot", back_populates="seller")


class SellerUser(TimestampMixin, Base):
    __tablename__ = "seller_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    seller_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sellers.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # owner | manager | warehouse
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invited_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("seller_users.id"), nullable=True
    )

    seller: Mapped["Seller"] = relationship("Seller", back_populates="users")


# Import Bot here to avoid circular imports
from app.models.bot import Bot  # noqa: E402
