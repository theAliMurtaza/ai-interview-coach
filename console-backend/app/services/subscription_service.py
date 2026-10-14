"""Stripe billing with server-owned prices and authoritative subscription synchronization."""

import uuid
from datetime import UTC, datetime
from urllib.parse import urlsplit

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.exceptions import ConflictError, ServiceUnavailableError, ValidationAppError
from app.models.subscription import Subscription, SubscriptionStatus, WebhookEvent
from app.models.user import SubscriptionPlan, User

stripe.default_http_client = stripe.RequestsClient(timeout=15)
stripe.max_network_retries = 2


def validate_return_url(url: str) -> str:
    parsed = urlsplit(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if parsed.username or parsed.password or origin not in settings.BACKEND_CORS_ORIGINS:
        raise ValidationAppError("Billing return URL must use an allowed frontend origin")
    return url


async def stripe_call(method, *args, **kwargs):
    if not settings.STRIPE_SECRET_KEY:
        raise ServiceUnavailableError("Billing is not configured")
    try:
        return await run_in_threadpool(method, *args, api_key=settings.STRIPE_SECRET_KEY, **kwargs)
    except stripe.StripeError as exc:
        raise ServiceUnavailableError("Billing provider is unavailable") from exc


class SubscriptionService:
    @classmethod
    async def create_checkout_session(
        cls,
        user: User,
        price_id: str | None = None,
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> str:
        if not settings.STRIPE_PRICE_ID_PRO:
            raise ServiceUnavailableError("Billing price is not configured")
        if price_id and price_id != settings.STRIPE_PRICE_ID_PRO:
            raise ValidationAppError("Unknown subscription price")
        if user.plan == SubscriptionPlan.PRO:
            raise ConflictError("Use the customer portal to manage the existing subscription")
        session = await stripe_call(
            stripe.checkout.Session.create,
            mode="subscription",
            line_items=[{"price": settings.STRIPE_PRICE_ID_PRO, "quantity": 1}],
            customer_email=user.email,
            client_reference_id=str(user.id),
            subscription_data={"metadata": {"user_id": str(user.id)}},
            success_url=validate_return_url(
                success_url or settings.BILLING_RETURN_URL + "?status=success"
            ),
            cancel_url=validate_return_url(
                cancel_url or settings.BILLING_RETURN_URL + "?status=canceled"
            ),
            idempotency_key=f"checkout:{user.id}:{int(datetime.now(UTC).timestamp()) // 3600}",
        )
        return session.url

    @classmethod
    async def create_portal_session(cls, user_id: str, db: AsyncSession) -> str:
        sub = await db.scalar(
            select(Subscription).where(Subscription.user_id == uuid.UUID(user_id))
        )
        if not sub or not sub.stripe_customer_id:
            raise ConflictError("No billing customer exists for this account")
        portal = await stripe_call(
            stripe.billing_portal.Session.create,
            customer=sub.stripe_customer_id,
            return_url=validate_return_url(settings.BILLING_RETURN_URL),
        )
        return portal.url

    @classmethod
    async def handle_event(cls, event: dict, db: AsyncSession) -> None:
        if await db.get(WebhookEvent, event["id"]):
            return
        event_type = event["type"]
        data = event["data"]["object"]
        subscription_id = None
        if event_type == "checkout.session.completed" and data.get("mode") == "subscription":
            subscription_id = data.get("subscription")
        elif event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            subscription_id = data.get("id")
        if subscription_id:
            # Stripe retries and reorders events: always fetch current state.
            current = await stripe_call(stripe.Subscription.retrieve, subscription_id)
            if hasattr(current, "to_dict"):
                current = current.to_dict()
            user_id = current.get("metadata", {}).get("user_id")
            existing = await db.scalar(
                select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
            )
            if not user_id and existing:
                user_id = str(existing.user_id)
            if user_id:
                try:
                    uid = uuid.UUID(user_id)
                except ValueError as exc:
                    raise ValidationAppError("Invalid billing user reference") from exc
                user = await db.scalar(
                    select(User)
                    .where(User.id == uid)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
                if user:
                    # Re-read after acquiring the owner lock: a competing webhook may
                    # have committed a newer Stripe state while this request waited.
                    current = await stripe_call(stripe.Subscription.retrieve, subscription_id)
                    if hasattr(current, "to_dict"):
                        current = current.to_dict()
                    sub = await db.scalar(
                        select(Subscription)
                        .where(Subscription.user_id == uid)
                        .execution_options(populate_existing=True)
                    )
                    if sub and sub.stripe_subscription_id != subscription_id:
                        # An old canceled subscription must never revoke a newer one.
                        if int(current.get("created", 0)) <= sub.stripe_created_at:
                            db.add(WebhookEvent(id=event["id"]))
                            await db.commit()
                            return
                    if not sub:
                        sub = Subscription(user_id=uid)
                        db.add(sub)
                    status = current.get("status", "unpaid")
                    sub.status = SubscriptionStatus(status)
                    sub.stripe_subscription_id = subscription_id
                    sub.stripe_customer_id = current["customer"]
                    sub.stripe_created_at = int(current.get("created", 0))
                    items = current.get("items", {}).get("data", [])
                    eligible = any(
                        item.get("price", {}).get("id") == settings.STRIPE_PRICE_ID_PRO
                        for item in items
                    )
                    paid = eligible and status in {"active", "trialing"}
                    sub.plan = user.plan = SubscriptionPlan.PRO if paid else SubscriptionPlan.FREE
                    period_end = current.get("current_period_end") or max(
                        (item.get("current_period_end", 0) for item in items), default=0
                    )
                    sub.current_period_end = (
                        datetime.fromtimestamp(period_end, UTC) if period_end else None
                    )
        db.add(WebhookEvent(id=event["id"]))
        await db.commit()
