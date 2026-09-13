from datetime import datetime, timezone
from typing import Dict, Any


def order_helper(order: Dict[str, Any]) -> Dict[str, Any]:
    """Formats a MongoDB order document into a standardized dictionary."""
    if not order:
        return {}
    return {
        "id": str(order["_id"]) if "_id" in order else str(order.get("id", "")),
        "order_date": order.get("order_date", ""),
        "customer_id": str(order.get("customer_id", "")),
        "customer_name": order.get("customer_name", ""),
        "customer_phone": order.get("customer_phone", ""),
        "delivery_address": order.get("delivery_address", {}),
        "meal_session": order.get("meal_session", "LUNCH"),
        "diet_type": order.get("diet_type", "VEG"),
        "quantity": order.get("quantity", 1),
        "order_type": order.get("order_type", "SUBSCRIPTION"),
        "spice_level": order.get("spice_level", "NORMAL"),
        "rice_preference": order.get("rice_preference"),
        "special_notes": order.get("special_notes"),
        "status": order.get("status", "PLANNED"),
        "assigned_driver_id": str(order.get("assigned_driver_id")) if order.get("assigned_driver_id") else None,
        "assigned_driver_name": order.get("assigned_driver_name"),
        "sequence_number": order.get("sequence_number"),
        "delivery_notes": order.get("delivery_notes"),
        "delivery_charge": float(order.get("delivery_charge", 0.0)),
        "total_price": float(order.get("total_price", 0.0)),
        "created_at": order.get("created_at", datetime.now(timezone.utc)),
        "updated_at": order.get("updated_at")
    }
