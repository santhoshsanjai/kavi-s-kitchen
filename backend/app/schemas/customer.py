from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CustomerType(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"
    FAMILY = "FAMILY"
    OFFICE = "OFFICE"
    OTHER = "OTHER"


class DietType(str, Enum):
    VEG = "VEG"
    NON_VEG = "NON_VEG"
    EGG = "EGG"
    CUSTOM = "CUSTOM"


class MealSession(str, Enum):
    BREAKFAST = "BREAKFAST"
    LUNCH = "LUNCH"
    DINNER = "DINNER"


class SpiceLevel(str, Enum):
    MILD = "MILD"
    NORMAL = "NORMAL"
    SPICY = "SPICY"


class AddressSchema(BaseModel):
    address_line: str = Field(..., description="Street address / door number")
    area: str = Field(..., description="Area / locality (e.g. Anna Nagar)")
    landmark: Optional[str] = None
    city: str = Field(default="Chennai")
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    google_place_id: Optional[str] = None
    formatted_address: Optional[str] = None


class MealPreferenceSchema(BaseModel):
    diet_type: DietType = DietType.VEG
    sessions: List[MealSession] = Field(default_factory=lambda: [MealSession.LUNCH])
    spice_level: SpiceLevel = SpiceLevel.NORMAL
    rice_preference: Optional[str] = None
    food_exclusions: Optional[str] = None
    allergy_note: Optional[str] = None
    delivery_instructions: Optional[str] = None


class CustomerBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=8, max_length=20)
    alternate_phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    customer_type: CustomerType = CustomerType.INDIVIDUAL
    is_active: bool = True
    address: AddressSchema
    meal_preference: MealPreferenceSchema = Field(default_factory=MealPreferenceSchema)
    notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    whatsapp_number: Optional[str] = None
    customer_type: Optional[CustomerType] = None
    is_active: Optional[bool] = None
    address: Optional[AddressSchema] = None
    meal_preference: Optional[MealPreferenceSchema] = None
    notes: Optional[str] = None


class CustomerStatusUpdate(BaseModel):
    is_active: bool


class CustomerResponse(CustomerBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
