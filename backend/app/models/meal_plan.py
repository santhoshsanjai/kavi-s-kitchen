from datetime import datetime, timezone
from typing import Dict, Any


def meal_plan_helper(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Formats a MongoDB meal plan document into a standardized dictionary."""
    if not plan:
        return {}
    return {
        "id": str(plan["_id"]) if "_id" in plan else str(plan.get("id", "")),
        "name": plan.get("name", ""),
        "diet_type": plan.get("diet_type", "VEG"),
        "meal_sessions": plan.get("meal_sessions", ["LUNCH"]),
        "price": plan.get("price", 0.0),
        "billing_cycle": plan.get("billing_cycle", "MONTHLY"),
        "service_days": plan.get("service_days", 26),
        "delivery_eligible": plan.get("delivery_eligible", True),
        "is_active": plan.get("is_active", True),
        "description": plan.get("description"),
        "created_at": plan.get("created_at", datetime.now(timezone.utc)),
        "updated_at": plan.get("updated_at")
    }
