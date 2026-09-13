from datetime import datetime, timezone
from typing import Dict, Any


def enquiry_helper(enquiry: Dict[str, Any]) -> Dict[str, Any]:
    """Formats a MongoDB enquiry document into a standardized dictionary."""
    if not enquiry:
        return {}
    return {
        "id": str(enquiry["_id"]) if "_id" in enquiry else str(enquiry.get("id", "")),
        "customer_name": enquiry.get("customer_name", ""),
        "phone": enquiry.get("phone", ""),
        "enquiry_date": enquiry.get("enquiry_date", datetime.now(timezone.utc)),
        "requested_meal": enquiry.get("requested_meal"),
        "requested_date": enquiry.get("requested_date"),
        "number_of_persons": enquiry.get("number_of_persons", 1),
        "diet_type": enquiry.get("diet_type", "VEG"),
        "subscription_type": enquiry.get("subscription_type", "SUBSCRIPTION"),
        "delivery_location": enquiry.get("delivery_location", ""),
        "quoted_price": enquiry.get("quoted_price"),
        "notes": enquiry.get("notes"),
        "follow_up_date": enquiry.get("follow_up_date"),
        "assigned_admin": enquiry.get("assigned_admin"),
        "status": enquiry.get("status", "NEW"),
        "customer_id": str(enquiry["customer_id"]) if enquiry.get("customer_id") else None,
        "created_at": enquiry.get("created_at", datetime.now(timezone.utc)),
        "updated_at": enquiry.get("updated_at")
    }
