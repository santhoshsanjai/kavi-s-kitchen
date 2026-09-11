from datetime import datetime, timezone
from typing import Optional, Dict, Any
from bson import ObjectId


def user_helper(user: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to convert MongoDB user document into a standardized dictionary."""
    if not user:
        return {}
    return {
        "id": str(user["_id"]) if "_id" in user else str(user.get("id", "")),
        "username": user.get("username", ""),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "full_name": user.get("full_name", ""),
        "role": user.get("role", "ADMIN"),
        "is_active": user.get("is_active", True),
        "created_at": user.get("created_at", datetime.now(timezone.utc)),
        "updated_at": user.get("updated_at")
    }
