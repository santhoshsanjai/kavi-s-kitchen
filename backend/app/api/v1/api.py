from fastapi import APIRouter
from app.api.v1.endpoints import auth, customers, enquiries, meal_plans, orders, drivers

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
api_router.include_router(enquiries.router, prefix="/enquiries", tags=["Enquiries"])
api_router.include_router(meal_plans.router, prefix="/meal-plans", tags=["Meal Plans"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders & Planner"])
api_router.include_router(drivers.router, prefix="/drivers", tags=["Drivers & Fleet"])
