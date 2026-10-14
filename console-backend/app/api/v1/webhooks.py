"""Signed, replay-safe payment and automation callbacks."""

import hashlib
import hmac
import time

import stripe
from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.core.exceptions import ServiceUnavailableError, UnauthorizedError, ValidationAppError
from app.models.subscription import WebhookEvent
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise ServiceUnavailableError("Stripe webhook is not configured")
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise ValidationAppError("Missing Stripe signature")
    try:
        event = stripe.Webhook.construct_event(
            await request.body(), signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise ValidationAppError("Invalid Stripe signature") from exc
    event = event.to_dict()
    if not event.get("id") or not event.get("type") or not isinstance(event.get("data"), dict):
        raise ValidationAppError("Invalid Stripe event")
    try:
        await SubscriptionService.handle_event(event, db)
    except IntegrityError:
        await db.rollback()
        if not await db.get(WebhookEvent, event["id"]):
            raise
    return {"received": True}


@router.post("/n8n")
async def n8n_callback(request: Request) -> dict:
    if not settings.N8N_WEBHOOK_SECRET:
        raise ServiceUnavailableError("Automation callbacks are not configured")
    timestamp = request.headers.get("x-webhook-timestamp", "")
    signature = request.headers.get("x-webhook-signature", "")
    try:
        if abs(time.time() - int(timestamp)) > 300:
            raise ValueError("Expired signature")
    except ValueError as exc:
        raise UnauthorizedError("Invalid callback timestamp") from exc
    body = await request.body()
    expected = hmac.new(
        settings.N8N_WEBHOOK_SECRET.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise UnauthorizedError("Invalid callback signature")
    return {"status": "ok", "acknowledged": True}
