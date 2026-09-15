from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.customer import DietType, MealSession, SpiceLevel, AddressSchema


class OrderStatus(str, Enum):
    PLANNED = "PLANNED"
    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    READY = "READY"
    ASSIGNED = "ASSIGNED"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


class OrderType(str, Enum):
    SUBSCRIPTION = "SUBSCRIPTION"
    AD_HOC = "AD_HOC"
    BULK = "BULK"


class OrderBase(BaseModel):
    order_date: str = Field(..., description="Date in YYYY-MM-DD format")
    customer_id: str
    customer_name: str
    customer_phone: str
    delivery_address: AddressSchema
    meal_session: MealSession = MealSession.LUNCH
    diet_type: DietType = DietType.VEG
    quantity: int = Field(default=1, ge=1)
    order_type: OrderType = OrderType.SUBSCRIPTION
    spice_level: SpiceLevel = SpiceLevel.NORMAL
    rice_preference: Optional[str] = None
    special_notes: Optional[str] = None
    status: OrderStatus = OrderStatus.PLANNED
    assigned_driver_id: Optional[str] = None
    assigned_driver_name: Optional[str] = None
    sequence_number: Optional[int] = None
    delivery_notes: Optional[str] = None
    delivery_charge: float = 0.0
    total_price: float = 0.0


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    quantity: Optional[int] = None
    meal_session: Optional[MealSession] = None
    diet_type: Optional[DietType] = None
    spice_level: Optional[SpiceLevel] = None
    rice_preference: Optional[str] = None
    special_notes: Optional[str] = None
    status: Optional[OrderStatus] = None
    assigned_driver_id: Optional[str] = None
    assigned_driver_name: Optional[str] = None
    sequence_number: Optional[int] = None
    delivery_notes: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    reason: Optional[str] = None


class CompleteDeliveryRequest(BaseModel):
    recipient_name: Optional[str] = None
    delivery_note: Optional[str] = None
    proof_photo_url: Optional[str] = None


class FailDeliveryRequest(BaseModel):
    reason: str  # CUSTOMER_UNAVAILABLE, WRONG_ADDRESS, PHONE_UNREACHABLE, CUSTOMER_CANCELLED, LOCATION_INACCESSIBLE, OTHER
    notes: Optional[str] = None


class BulkStatusUpdate(BaseModel):
    order_ids: List[str]
    status: OrderStatus


class DriverAssignmentItem(BaseModel):
    order_id: str
    sequence_number: int


class BulkAssignDriver(BaseModel):
    driver_id: str
    driver_name: str
    assignments: List[DriverAssignmentItem]


class GenerateDailyOrdersRequest(BaseModel):
    date: str = Field(..., description="Target date in YYYY-MM-DD format")


class OrderResponse(OrderBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SessionStats(BaseModel):
    total: int = 0
    veg: int = 0
    non_veg: int = 0
    ready: int = 0
    delivered: int = 0


class DailySummary(BaseModel):
    date: str
    total_orders: int
    breakfast: SessionStats
    lunch: SessionStats
    dinner: SessionStats


class OrdersListResponse(BaseModel):
    items: List[OrderResponse]
    total: int
    summary: DailySummary
