from datetime import datetime
from pydantic import BaseModel


class BotOut(BaseModel):
    id: int
    seller_id: int
    telegram_bot_id: int
    username: str
    title: str
    webhook_url: str
    is_active: bool
    last_health_check: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BotSettingsOut(BaseModel):
    welcome_message_uz: str | None
    welcome_message_ru: str | None
    about_text_uz: str | None
    about_text_ru: str | None
    contact_phone: str | None
    contact_address: str | None
    work_hours: dict | None
    default_language: str
    enabled_languages: list[str]
    currency: str
    payment_methods: list[str]
    delivery_methods: list[str]
    min_order_amount: int
    delivery_fee: int
    free_delivery_from: int | None
    brand_primary_color: str | None
    brand_logo_url: str | None
    brand_banner_url: str | None
    brand_accent_color: str | None

    model_config = {"from_attributes": True}


class BotSettingsUpdate(BaseModel):
    welcome_message_uz: str | None = None
    welcome_message_ru: str | None = None
    about_text_uz: str | None = None
    about_text_ru: str | None = None
    contact_phone: str | None = None
    contact_address: str | None = None
    work_hours: dict | None = None
    default_language: str | None = None
    enabled_languages: list[str] | None = None
    payment_methods: list[str] | None = None
    delivery_methods: list[str] | None = None
    min_order_amount: int | None = None
    delivery_fee: int | None = None
    free_delivery_from: int | None = None
    brand_primary_color: str | None = None
    brand_logo_url: str | None = None
    brand_banner_url: str | None = None
    brand_accent_color: str | None = None
