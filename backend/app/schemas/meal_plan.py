from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.customer import DietType, MealSession


class MealPlanBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    diet_type: DietType = DietType.VEG
    meal_sessions: List[MealSession] = Field(default_factory=lambda: [MealSession.LUNCH])
    price: float = Field(..., ge=0)
    billing_cycle: str = Field(default="MONTHLY")
    service_days: int = Field(default=26, description="Number of service days (e.g. 26 for Mon-Sat)")
    delivery_eligible: bool = True
    is_active: bool = True
    description: Optional[str] = None


class MealPlanCreate(MealPlanBase):
    pass


class MealPlanUpdate(BaseModel):
    name: Optional[str] = None
    diet_type: Optional[DietType] = None
    meal_sessions: Optional[List[MealSession]] = None
    price: Optional[float] = None
    billing_cycle: Optional[str] = None
    service_days: Optional[int] = None
    delivery_eligible: Optional[bool] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class MealPlanResponse(MealPlanBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
