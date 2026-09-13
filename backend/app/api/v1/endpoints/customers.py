from fastapi import APIRouter, HTTPException, status, Depends, Query
from bson import ObjectId
from typing import List, Optional
from datetime import datetime, timezone

from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerStatusUpdate,
    CustomerType,
    DietType
)
from app.schemas.user import UserRole
from app.core import database
from app.models.customer import customer_helper
from app.api.deps import require_roles

router = APIRouter()

# Securing customer routes for Super Admin and Kitchen Admin
admin_access = require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN])


@router.get("", response_model=dict)
async def get_customers(
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    customer_type: Optional[CustomerType] = None,
    diet_type: Optional[DietType] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )
        
    query = {}
    
    if is_active is not None:
        query["is_active"] = is_active
        
    if customer_type:
        query["customer_type"] = customer_type
        
    if diet_type:
        query["meal_preference.diet_type"] = diet_type
        
    if search:
        search_regex = {"$regex": search.strip(), "$options": "i"}
        query["$or"] = [
            {"name": search_regex},
            {"phone": search_regex},
            {"address.area": search_regex},
            {"address.city": search_regex},
            {"address.address_line": search_regex}
        ]

    customers_collection = database.db.customers
    total = await customers_collection.count_documents(query)
    
    cursor = customers_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
    items = []
    async for doc in cursor:
        items.append(customer_helper(doc))
        
    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_in: CustomerCreate,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )
        
    clean_phone = customer_in.phone.strip()
    existing = await database.db.customers.find_one({"phone": clean_phone})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Customer with phone number '{clean_phone}' already exists."
        )

    doc = customer_in.model_dump()
    doc["phone"] = clean_phone
    doc["created_at"] = datetime.now(timezone.utc)
    doc["updated_at"] = datetime.now(timezone.utc)
    
    result = await database.db.customers.insert_one(doc)
    doc["_id"] = result.inserted_id
    
    return customer_helper(doc)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )
        
    try:
        query = {"_id": ObjectId(customer_id)}
    except Exception:
        query = {"id": customer_id}
        
    customer = await database.db.customers.find_one(query)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
        
    return customer_helper(customer)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    customer_in: CustomerUpdate,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )
        
    try:
        query = {"_id": ObjectId(customer_id)}
    except Exception:
        query = {"id": customer_id}
        
    existing = await database.db.customers.find_one(query)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    update_data = {k: v for k, v in customer_in.model_dump(exclude_unset=True).items() if v is not None}
    
    if "phone" in update_data:
        new_phone = update_data["phone"].strip()
        phone_match = await database.db.customers.find_one({"phone": new_phone, "_id": {"$ne": existing["_id"]}})
        if phone_match:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phone number '{new_phone}' is already registered to another customer."
            )
        update_data["phone"] = new_phone

    update_data["updated_at"] = datetime.now(timezone.utc)
    
    await database.db.customers.update_one(query, {"$set": update_data})
    updated = await database.db.customers.find_one(query)
    return customer_helper(updated)


@router.patch("/{customer_id}/status", response_model=CustomerResponse)
async def toggle_customer_status(
    customer_id: str,
    status_in: CustomerStatusUpdate,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )
        
    try:
        query = {"_id": ObjectId(customer_id)}
    except Exception:
        query = {"id": customer_id}
        
    customer = await database.db.customers.find_one(query)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    await database.db.customers.update_one(
        query,
        {"$set": {"is_active": status_in.is_active, "updated_at": datetime.now(timezone.utc)}}
    )
    updated = await database.db.customers.find_one(query)
    return customer_helper(updated)


@router.delete("/{customer_id}", response_model=dict)
async def delete_customer(
    customer_id: str,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )
        
    try:
        query = {"_id": ObjectId(customer_id)}
    except Exception:
        query = {"id": customer_id}
        
    result = await database.db.customers.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return {"message": "Customer removed successfully", "id": customer_id}
