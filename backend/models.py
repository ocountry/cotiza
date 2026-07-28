"""Pydantic models for Vigil price tracking service."""

from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta


class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    # Notification channels configuration
    notification_email: Optional[str] = None
    notification_whatsapp: Optional[str] = None
    notification_telegram: Optional[str] = None
    notification_sms: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserSession(BaseModel):
    session_id: str
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrackedItem(BaseModel):
    item_id: str = Field(default_factory=lambda: f"item_{uuid.uuid4().hex[:12]}")
    user_id: str
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    current_price: Optional[float] = None
    currency: str = "USD"
    extraction_method: str = "scraping"  # "scraping" or "ai"
    notification_channels: List[str] = Field(default_factory=lambda: ["email"])
    notes: Optional[str] = None  # Optional user notes
    is_active: bool = True
    last_checked: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PriceHistory(BaseModel):
    history_id: str = Field(default_factory=lambda: f"ph_{uuid.uuid4().hex[:12]}")
    item_id: str
    price: float
    currency: str = "USD"
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CreateItemRequest(BaseModel):
    url: str
    extraction_method: str = "scraping"
    notification_channels: List[str] = Field(default_factory=lambda: ["email"])
    notes: Optional[str] = None


class UpdateItemRequest(BaseModel):
    notification_channels: Optional[List[str]] = None
    is_active: Optional[bool] = None
    extraction_method: Optional[str] = None


class UpdateUserProfileRequest(BaseModel):
    notification_email: Optional[str] = None
    notification_whatsapp: Optional[str] = None
    notification_telegram: Optional[str] = None
    notification_sms: Optional[str] = None


class ExtractedData(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: str = "USD"
    image_url: Optional[str] = None