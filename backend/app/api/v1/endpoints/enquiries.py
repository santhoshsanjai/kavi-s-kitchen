from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.schemas.enquiry import (
    EnquiryCreate,
    EnquiryUpdate,
    EnquiryResponse,
    EnquiryConvertRequest,
    EnquiryStatus
)
from app.schemas.customer import CustomerType, DietType, MealSession, SpiceLevel
from app.core.database import get_db
from app.models.enquiry import Enquiry, enquiry_helper
from app.models.customer import Customer, customer_helper
from app.api.deps import ADMIN_ROLES, parse_uuid, require_roles

router = APIRouter()

admin_access = require_roles(ADMIN_ROLES)


async def _get_enquiry_or_404(db: AsyncSession, enquiry_id: str) -> Enquiry:
    enquiry = await db.get(Enquiry, parse_uuid(enquiry_id, "Enquiry not found"))
    if not enquiry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enquiry not found")
    return enquiry


@router.get("", response_model=dict)
async def get_enquiries(
    search: Optional[str] = None,
    status_filter: Optional[EnquiryStatus] = None,
    diet_type: Optional[DietType] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if status_filter:
        filters.append(Enquiry.status == status_filter)
    if diet_type:
        filters.append(Enquiry.diet_type == diet_type)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(
            Enquiry.customer_name.ilike(pattern),
            Enquiry.phone.ilike(pattern),
            Enquiry.delivery_location.ilike(pattern),
            Enquiry.notes.ilike(pattern),
        ))

    total = await db.scalar(select(func.count()).select_from(Enquiry).where(*filters))
    rows = (await db.execute(
        select(Enquiry).where(*filters).order_by(Enquiry.created_at.desc()).offset(skip).limit(limit)
    )).scalars().all()

    return {
        "items": [enquiry_helper(e) for e in rows],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("", response_model=EnquiryResponse, status_code=status.HTTP_201_CREATED)
async def create_enquiry(
    enquiry_in: EnquiryCreate,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    data = enquiry_in.model_dump(mode="json")
    data["phone"] = enquiry_in.phone.strip()
    enquiry = Enquiry(**data)
    db.add(enquiry)
    await db.commit()
    await db.refresh(enquiry)
    return enquiry_helper(enquiry)


@router.get("/{enquiry_id}", response_model=EnquiryResponse)
async def get_enquiry(
    enquiry_id: str,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    return enquiry_helper(await _get_enquiry_or_404(db, enquiry_id))


@router.put("/{enquiry_id}", response_model=EnquiryResponse)
async def update_enquiry(
    enquiry_id: str,
    enquiry_in: EnquiryUpdate,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    enquiry = await _get_enquiry_or_404(db, enquiry_id)
    update_data = {k: v for k, v in enquiry_in.model_dump(mode="json", exclude_unset=True).items() if v is not None}
    for field, value in update_data.items():
        setattr(enquiry, field, value)
    await db.commit()
    await db.refresh(enquiry)
    return enquiry_helper(enquiry)


@router.post("/{enquiry_id}/convert", response_model=dict)
async def convert_enquiry_to_customer(
    enquiry_id: str,
    convert_in: EnquiryConvertRequest,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    enquiry = await _get_enquiry_or_404(db, enquiry_id)
    phone = enquiry.phone.strip()

    # Reuse an existing customer with this phone instead of creating a duplicate
    customer = (await db.execute(select(Customer).where(Customer.phone == phone))).scalars().first()

    if customer is None:
        customer = Customer(
            name=enquiry.customer_name,
            phone=phone,
            whatsapp_number=phone,
            customer_type=CustomerType.INDIVIDUAL,
            is_active=True,
            address=convert_in.model_dump(mode="json"),
            meal_preference={
                "diet_type": enquiry.diet_type.value,
                "sessions": [MealSession.LUNCH.value],
                "spice_level": SpiceLevel.NORMAL.value,
                "food_exclusions": None,
                "delivery_instructions": enquiry.notes,
            },
            notes=f"Converted from Enquiry #{enquiry_id}",
        )
        db.add(customer)
        await db.flush()

    enquiry.status = EnquiryStatus.CONVERTED
    enquiry.customer_id = customer.id
    await db.commit()
    await db.refresh(enquiry)
    await db.refresh(customer)

    return {
        "enquiry": enquiry_helper(enquiry),
        "customer": customer_helper(customer)
    }


@router.delete("/{enquiry_id}", response_model=dict)
async def delete_enquiry(
    enquiry_id: str,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    enquiry = await _get_enquiry_or_404(db, enquiry_id)
    await db.delete(enquiry)
    await db.commit()
    return {"message": "Enquiry deleted successfully", "id": enquiry_id}
