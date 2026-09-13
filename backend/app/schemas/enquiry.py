from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.customer import DietType


class EnquiryStatus(str, Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    QUOTED = "QUOTED"
    FOLLOW_UP = "FOLLOW_UP"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CONVERTED = "CONVERTED"
    CLOSED = "CLOSED"


class EnquiryBase(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=8, max_length=20)
    requested_meal: Optional[str] = "Lunch & Dinner"
    requested_date: Optional[str] = None
    number_of_persons: int = Field(default=1, ge=1)
    diet_type: DietType = DietType.VEG
    subscription_type: str = "SUBSCRIPTION"
    delivery_location: str = Field(..., description="Delivery address or neighborhood")
    quoted_price: Optional[float] = None
    notes: Optional[str] = None
    follow_up_date: Optional[str] = None
    assigned_admin: Optional[str] = None
    status: EnquiryStatus = EnquiryStatus.NEW


class EnquiryCreate(EnquiryBase):
    pass


class EnquiryUpdate(BaseModel):
    customer_name: Optional[str] = None
    phone: Optional[str] = None
    requested_meal: Optional[str] = None
    requested_date: Optional[str] = None
    number_of_persons: Optional[int] = None
    diet_type: Optional[DietType] = None
    subscription_type: Optional[str] = None
    delivery_location: Optional[str] = None
    quoted_price: Optional[float] = None
    notes: Optional[str] = None
    follow_up_date: Optional[str] = None
    assigned_admin: Optional[str] = None
    status: Optional[EnquiryStatus] = None


class EnquiryConvertRequest(BaseModel):
    address_line: str
    area: str
    city: str = "Chennai"
    landmark: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class EnquiryResponse(EnquiryBase):
    id: str
    enquiry_date: datetime
    customer_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
