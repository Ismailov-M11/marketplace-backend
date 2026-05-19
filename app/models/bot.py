from datetime import datetime
from typing import Optional

from sqlalchemy import ARRAY, BigInteger, Boolean, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Bot(TimestampMixin, Base):
    __tablename__ = "bots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    seller_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sellers.id"), nullable=False, index=True
    )
    telegram_bot_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    webhook_secret: Mapped[str] = mapped_column(Text, nullable=False)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_update_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notification_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    seller: Mapped["Seller"] = relationship("Seller", back_populates="bots")
    settings: Mapped[Optional["BotSettings"]] = relationship("BotSettings", back_populates="bot", uselist=False)


class BotSettings(Base):
    __tablename__ = "bot_settings"

    bot_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bots.id"), primary_key=True
    )
    welcome_message_uz: Mapped[str | None] = mapped_column(Text, nullable=True)
    welcome_message_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    about_text_uz: Mapped[str | None] = mapped_column(Text, nullable=True)
    about_text_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    default_language: Mapped[str] = mapped_column(String(10), default="uz", nullable=False)
    enabled_languages: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default="{uz,ru}", nullable=False
    )
    currency: Mapped[str] = mapped_column(String(10), default="UZS", nullable=False)
    payment_methods: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default="{cash}", nullable=False
    )
    delivery_methods: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default="{courier,pickup}", nullable=False
    )
    min_order_amount: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    delivery_fee: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    free_delivery_from: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Branding (Mini App)
    brand_primary_color: Mapped[str | None] = mapped_column(String(10), nullable=True)
    brand_logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand_banner_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand_accent_color: Mapped[str | None] = mapped_column(String(10), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", onupdate="now()", nullable=False
    )

    bot: Mapped["Bot"] = relationship("Bot", back_populates="settings")


from app.models.seller import Seller  # noqa: E402
