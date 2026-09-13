from fastapi import APIRouter, HTTPException, status, Depends, Query
from bson import ObjectId
from typing import List, Optional
from datetime import datetime, timezone

from app.schemas.enquiry import (
    EnquiryCreate,
    EnquiryUpdate,
    EnquiryResponse,
    EnquiryConvertRequest,
    EnquiryStatus
)
from app.schemas.customer import (
    CustomerCreate,
    AddressSchema,
    MealPreferenceSchema,
    DietType
)
from app.schemas.user import UserRole
from app.core import database
from app.models.enquiry import enquiry_helper
from app.models.customer import customer_helper
from app.api.deps import require_roles

router = APIRouter()

admin_access = require_roles([UserRole.SUPER_ADMIN, UserRole.ADMIN])


@router.get("", response_model=dict)
async def get_enquiries(
    search: Optional[str] = None,
    status_filter: Optional[EnquiryStatus] = None,
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
    if status_filter:
        query["status"] = status_filter
    if diet_type:
        query["diet_type"] = diet_type
    if search:
        search_regex = {"$regex": search.strip(), "$options": "i"}
        query["$or"] = [
            {"customer_name": search_regex},
            {"phone": search_regex},
            {"delivery_location": search_regex},
            {"notes": search_regex}
        ]

    enquiries_collection = database.db.enquiries
    total = await enquiries_collection.count_documents(query)

    cursor = enquiries_collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
    items = []
    async for doc in cursor:
        items.append(enquiry_helper(doc))

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("", response_model=EnquiryResponse, status_code=status.HTTP_201_CREATED)
async def create_enquiry(
    enquiry_in: EnquiryCreate,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    doc = enquiry_in.model_dump()
    doc["phone"] = enquiry_in.phone.strip()
    doc["enquiry_date"] = datetime.now(timezone.utc)
    doc["created_at"] = datetime.now(timezone.utc)
    doc["updated_at"] = datetime.now(timezone.utc)

    result = await database.db.enquiries.insert_one(doc)
    doc["_id"] = result.inserted_id

    return enquiry_helper(doc)


@router.get("/{enquiry_id}", response_model=EnquiryResponse)
async def get_enquiry(
    enquiry_id: str,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    try:
        query = {"_id": ObjectId(enquiry_id)}
    except Exception:
        query = {"id": enquiry_id}

    enquiry = await database.db.enquiries.find_one(query)
    if not enquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enquiry not found"
        )

    return enquiry_helper(enquiry)


@router.put("/{enquiry_id}", response_model=EnquiryResponse)
async def update_enquiry(
    enquiry_id: str,
    enquiry_in: EnquiryUpdate,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    try:
        query = {"_id": ObjectId(enquiry_id)}
    except Exception:
        query = {"id": enquiry_id}

    existing = await database.db.enquiries.find_one(query)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enquiry not found"
        )

    update_data = {k: v for k, v in enquiry_in.model_dump(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)

    await database.db.enquiries.update_one(query, {"$set": update_data})
    updated = await database.db.enquiries.find_one(query)
    return enquiry_helper(updated)


@router.post("/{enquiry_id}/convert", response_model=dict)
async def convert_enquiry_to_customer(
    enquiry_id: str,
    convert_in: EnquiryConvertRequest,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    try:
        query = {"_id": ObjectId(enquiry_id)}
    except Exception:
        query = {"id": enquiry_id}

    enquiry = await database.db.enquiries.find_one(query)
    if not enquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enquiry not found"
        )

    phone = enquiry["phone"].strip()

    # Check if a customer already exists with this phone
    existing_customer = await database.db.customers.find_one({"phone": phone})

    if existing_customer:
        customer_id = existing_customer["_id"]
        customer_doc = existing_customer
    else:
        # Create new customer record from enquiry
        new_customer_doc = {
            "name": enquiry["customer_name"],
            "phone": phone,
            "whatsapp_number": phone,
            "customer_type": "INDIVIDUAL",
            "is_active": True,
            "address": {
                "address_line": convert_in.address_line,
                "area": convert_in.area,
                "city": convert_in.city,
                "landmark": convert_in.landmark,
                "pincode": convert_in.pincode,
                "latitude": convert_in.latitude,
                "longitude": convert_in.longitude
            },
            "meal_preference": {
                "diet_type": enquiry.get("diet_type", "VEG"),
                "sessions": ["LUNCH"],
                "spice_level": "NORMAL",
                "food_exclusions": None,
                "delivery_instructions": enquiry.get("notes")
            },
            "notes": f"Converted from Enquiry #{enquiry_id}",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        res = await database.db.customers.insert_one(new_customer_doc)
        new_customer_doc["_id"] = res.inserted_id
        customer_id = res.inserted_id
        customer_doc = new_customer_doc

    # Mark enquiry as CONVERTED and link customer_id
    await database.db.enquiries.update_one(
        query,
        {
            "$set": {
                "status": EnquiryStatus.CONVERTED,
                "customer_id": customer_id,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    updated_enquiry = await database.db.enquiries.find_one(query)
    return {
        "enquiry": enquiry_helper(updated_enquiry),
        "customer": customer_helper(customer_doc)
    }


@router.delete("/{enquiry_id}", response_model=dict)
async def delete_enquiry(
    enquiry_id: str,
    _: dict = Depends(admin_access)
):
    if database.db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable"
        )

    try:
        query = {"_id": ObjectId(enquiry_id)}
    except Exception:
        query = {"id": enquiry_id}

    result = await database.db.enquiries.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enquiry not found"
        )

    return {"message": "Enquiry deleted successfully", "id": enquiry_id}
