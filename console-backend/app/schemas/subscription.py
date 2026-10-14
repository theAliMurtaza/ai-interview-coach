"""
Pydantic schemas for Stripe checkout and subscription management.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.user import SubscriptionPlan


class CheckoutSessionRequest(BaseModel):
    price_id: str | None = Field(default=None, max_length=255)
    success_url: str | None = Field(default=None, max_length=2048)
    cancel_url: str | None = Field(default=None, max_length=2048)


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class CustomerPortalResponse(BaseModel):
    portal_url: str


class SubscriptionResponse(BaseModel):
    plan: SubscriptionPlan
    status: str
    current_period_end: datetime | None = None
