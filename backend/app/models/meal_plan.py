from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.models._types import ev, money, str_enum
from app.schemas.customer import DietType


class MealPlan(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "meal_plans"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    diet_type: Mapped[DietType] = mapped_column(str_enum(DietType, "diet_type"), nullable=False, default=DietType.VEG)
    meal_sessions: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=lambda: ["LUNCH"])
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(20), nullable=False, default="MONTHLY")
    service_days: Mapped[int] = mapped_column(Integer, nullable=False, default=26)
    delivery_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text)


def meal_plan_helper(plan: Optional[MealPlan]) -> Dict[str, Any]:
    """Serializes a MealPlan row into the API's meal plan dictionary."""
    if not plan:
        return {}
    return {
        "id": str(plan.id),
        "name": plan.name,
        "diet_type": ev(plan.diet_type),
        "meal_sessions": plan.meal_sessions,
        "price": money(plan.price),
        "billing_cycle": plan.billing_cycle,
        "service_days": plan.service_days,
        "delivery_eligible": plan.delivery_eligible,
        "is_active": plan.is_active,
        "description": plan.description,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }
