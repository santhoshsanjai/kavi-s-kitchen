from datetime import datetime, timezone
from typing import Dict, Any


def customer_helper(customer: Dict[str, Any]) -> Dict[str, Any]:
    """Formats a MongoDB customer document into a standardized dictionary."""
    if not customer:
        return {}
    return {
        "id": str(customer["_id"]) if "_id" in customer else str(customer.get("id", "")),
        "name": customer.get("name", ""),
        "phone": customer.get("phone", ""),
        "alternate_phone": customer.get("alternate_phone"),
        "whatsapp_number": customer.get("whatsapp_number"),
        "customer_type": customer.get("customer_type", "INDIVIDUAL"),
        "is_active": customer.get("is_active", True),
        "address": customer.get("address", {}),
        "meal_preference": customer.get("meal_preference", {}),
        "notes": customer.get("notes"),
        "created_at": customer.get("created_at", datetime.now(timezone.utc)),
        "updated_at": customer.get("updated_at")
    }
