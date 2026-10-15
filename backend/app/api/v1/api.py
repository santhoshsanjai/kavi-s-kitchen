from fastapi import APIRouter
from app.api.v1.endpoints import auth, customers, enquiries, meal_plans, menus_public, orders, drivers, tracking
from app.api.v1.endpoints.admin import config, dispatch, finance, menus, ops, reports, subscriptions
from app.api.v1.endpoints.admin import orders as admin_orders

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
api_router.include_router(enquiries.router, prefix="/enquiries", tags=["Enquiries"])
api_router.include_router(meal_plans.router, prefix="/meal-plans", tags=["Meal Plans"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders & Planner"])
api_router.include_router(drivers.router, prefix="/drivers", tags=["Drivers & Fleet"])
api_router.include_router(tracking.router, prefix="/tracking", tags=["Live Tracking & WebSocket"])
api_router.include_router(menus_public.router, prefix="/menus", tags=["Menus"])

# Admin operations (Phase 2). Every route requires an admin role.
for module, tag in [(ops, "Admin: Dashboard & Alerts"), (config, "Admin: Settings & Calendar"),
                    (subscriptions, "Admin: Subscriptions"), (menus, "Admin: Menus"),
                    (admin_orders, "Admin: One-time Orders"), (dispatch, "Admin: Dispatch & Trips"),
                    (finance, "Admin: Payments & Earnings"), (reports, "Admin: Reports")]:
    api_router.include_router(module.router, prefix="/admin", tags=[tag])
