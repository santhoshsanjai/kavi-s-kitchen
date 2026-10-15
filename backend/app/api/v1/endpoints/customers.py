from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy import exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerStatusUpdate,
    CustomerType,
    DietType
)
from app.core.database import get_db
from app.models.customer import Customer, customer_helper
from app.models.order import Order
from app.api.deps import ADMIN_ROLES, parse_uuid, require_roles

router = APIRouter()

# Securing customer routes for Super Admin and Kitchen Admin
admin_access = require_roles(ADMIN_ROLES)


async def _get_customer_or_404(db: AsyncSession, customer_id: str) -> Customer:
    customer = await db.get(Customer, parse_uuid(customer_id, "Customer not found"))
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.get("", response_model=dict)
async def get_customers(
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    customer_type: Optional[CustomerType] = None,
    diet_type: Optional[DietType] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if is_active is not None:
        filters.append(Customer.is_active == is_active)
    if customer_type:
        filters.append(Customer.customer_type == customer_type)
    if diet_type:
        filters.append(Customer.meal_preference["diet_type"].astext == diet_type.value)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(
            Customer.name.ilike(pattern),
            Customer.phone.ilike(pattern),
            Customer.address["area"].astext.ilike(pattern),
            Customer.address["city"].astext.ilike(pattern),
            Customer.address["address_line"].astext.ilike(pattern),
        ))

    total = await db.scalar(select(func.count()).select_from(Customer).where(*filters))
    rows = (await db.execute(
        select(Customer).where(*filters).order_by(Customer.created_at.desc()).offset(skip).limit(limit)
    )).scalars().all()

    return {
        "items": [customer_helper(c) for c in rows],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_in: CustomerCreate,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    clean_phone = customer_in.phone.strip()
    if await db.scalar(select(exists().where(Customer.phone == clean_phone))):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Customer with phone number '{clean_phone}' already exists."
        )

    data = customer_in.model_dump(mode="json")
    data["phone"] = clean_phone
    customer = Customer(**data)
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer_helper(customer)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    return customer_helper(await _get_customer_or_404(db, customer_id))


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    customer_in: CustomerUpdate,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    customer = await _get_customer_or_404(db, customer_id)

    update_data = {k: v for k, v in customer_in.model_dump(mode="json", exclude_unset=True).items() if v is not None}

    if "phone" in update_data:
        new_phone = update_data["phone"].strip()
        taken = await db.scalar(select(exists().where(Customer.phone == new_phone, Customer.id != customer.id)))
        if taken:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phone number '{new_phone}' is already registered to another customer."
            )
        update_data["phone"] = new_phone

    for field, value in update_data.items():
        setattr(customer, field, value)
    await db.commit()
    await db.refresh(customer)
    return customer_helper(customer)


@router.patch("/{customer_id}/status", response_model=CustomerResponse)
async def toggle_customer_status(
    customer_id: str,
    status_in: CustomerStatusUpdate,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    customer = await _get_customer_or_404(db, customer_id)
    customer.is_active = status_in.is_active
    await db.commit()
    await db.refresh(customer)
    return customer_helper(customer)


@router.delete("/{customer_id}", response_model=dict)
async def delete_customer(
    customer_id: str,
    _: dict = Depends(admin_access),
    db: AsyncSession = Depends(get_db),
):
    customer = await _get_customer_or_404(db, customer_id)

    # Order history must survive, so customers with orders can only be deactivated.
    if await db.scalar(select(exists().where(Order.customer_id == customer.id))):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer has order history and cannot be deleted. Deactivate the customer instead."
        )

    await db.delete(customer)
    await db.commit()
    return {"message": "Customer removed successfully", "id": customer_id}
