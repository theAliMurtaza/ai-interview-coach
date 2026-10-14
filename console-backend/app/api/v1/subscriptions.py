"""
Stripe subscription and billing management API routes.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import (
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    CustomerPortalResponse,
    SubscriptionResponse,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post(
    "/checkout-session", response_model=CheckoutSessionResponse, status_code=status.HTTP_200_OK
)
async def create_checkout_session(
    payload: CheckoutSessionRequest,
    user: User = Depends(get_current_active_user),
) -> CheckoutSessionResponse:
    url = await SubscriptionService.create_checkout_session(
        user=user,
        price_id=payload.price_id,
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
    )
    return CheckoutSessionResponse(checkout_url=url)


@router.post("/portal-session", response_model=CustomerPortalResponse)
async def create_portal_session(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerPortalResponse:
    url = await SubscriptionService.create_portal_session(user_id=str(user.id), db=db)
    return CustomerPortalResponse(portal_url=url)


@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionResponse:
    stmt = select(Subscription).where(Subscription.user_id == user.id)
    res = await db.execute(stmt)
    sub = res.scalar_one_or_none()
    if not sub:
        return SubscriptionResponse(plan=user.plan, status="active", current_period_end=None)
    return SubscriptionResponse(
        plan=sub.plan,
        status=sub.status.value,
        current_period_end=sub.current_period_end,
    )
