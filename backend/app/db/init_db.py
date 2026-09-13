from datetime import datetime, timezone
from app.core import database
from app.core.security import get_password_hash
from app.schemas.user import UserRole
from app.schemas.customer import CustomerType, DietType, MealSession, SpiceLevel
from app.schemas.enquiry import EnquiryStatus


async def init_db():
    """Initializes the database with seed users, meal plans, and customers."""
    if database.db is None:
        print("Database not connected, skipping seed initialization.")
        return

    # 1. Seed Default Users
    users_col = database.db.users
    try:
        await users_col.create_index("username", unique=True)
        await users_col.create_index("email", unique=True, sparse=True)
        await users_col.create_index("phone", unique=True, sparse=True)
    except Exception as e:
        print(f"User index creation note: {e}")

    default_users = [
        {
            "username": "superadmin",
            "email": "admin@kaviskitchen.com",
            "phone": "9876543210",
            "full_name": "Kavi Super Admin",
            "password": "Admin@123",
            "role": UserRole.SUPER_ADMIN,
        },
        {
            "username": "kitchenadmin",
            "email": "kitchen@kaviskitchen.com",
            "phone": "9876543211",
            "full_name": "Main Kitchen Admin",
            "password": "Kitchen@123",
            "role": UserRole.ADMIN,
        },
        {
            "username": "driver1",
            "email": "driver1@kaviskitchen.com",
            "phone": "9876543212",
            "full_name": "Ramesh Kumar (Driver 1)",
            "password": "Driver@123",
            "role": UserRole.DRIVER,
        }
    ]

    for user_data in default_users:
        existing = await users_col.find_one({"username": user_data["username"]})
        if not existing:
            doc = {
                "username": user_data["username"],
                "email": user_data["email"],
                "phone": user_data["phone"],
                "full_name": user_data["full_name"],
                "hashed_password": get_password_hash(user_data["password"]),
                "role": user_data["role"],
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            await users_col.insert_one(doc)
            print(f"Seeded user: {user_data['username']}")

    # 2. Seed Default Meal Plans
    plans_col = database.db.meal_plans
    default_plans = [
        {
            "name": "Veg Full Day",
            "diet_type": DietType.VEG,
            "meal_sessions": [MealSession.BREAKFAST, MealSession.LUNCH, MealSession.DINNER],
            "price": 5499.0,
            "billing_cycle": "MONTHLY",
            "service_days": 26,
            "delivery_eligible": True,
            "is_active": True,
            "description": "Wholesome South Indian vegetarian Breakfast, Lunch, and Dinner (Mon–Sat, 26 days)."
        },
        {
            "name": "Non-Veg Full Day",
            "diet_type": DietType.NON_VEG,
            "meal_sessions": [MealSession.BREAKFAST, MealSession.LUNCH, MealSession.DINNER],
            "price": 6499.0,
            "billing_cycle": "MONTHLY",
            "service_days": 26,
            "delivery_eligible": True,
            "is_active": True,
            "description": "Authentic homestyle non-vegetarian meals with chicken/egg rotation (Mon–Sat, 26 days)."
        },
        {
            "name": "Veg Lunch Delight",
            "diet_type": DietType.VEG,
            "meal_sessions": [MealSession.LUNCH],
            "price": 2799.0,
            "billing_cycle": "MONTHLY",
            "service_days": 26,
            "delivery_eligible": True,
            "is_active": True,
            "description": "Nutritious traditional meals with rice, sambar, rasam, kootu, poriyal & curd."
        },
        {
            "name": "Non-Veg Lunch Club",
            "diet_type": DietType.NON_VEG,
            "meal_sessions": [MealSession.LUNCH],
            "price": 3299.0,
            "billing_cycle": "MONTHLY",
            "service_days": 26,
            "delivery_eligible": True,
            "is_active": True,
            "description": "Hearty lunch box with chicken/fish specialties on designated service days."
        },
        {
            "name": "Veg Breakfast + Lunch",
            "diet_type": DietType.VEG,
            "meal_sessions": [MealSession.BREAKFAST, MealSession.LUNCH],
            "price": 4199.0,
            "billing_cycle": "MONTHLY",
            "service_days": 26,
            "delivery_eligible": True,
            "is_active": True,
            "description": "Hot tiffin breakfast paired with complete homestyle afternoon lunch."
        },
        {
            "name": "Healthy Dinner Box",
            "diet_type": DietType.VEG,
            "meal_sessions": [MealSession.DINNER],
            "price": 2699.0,
            "billing_cycle": "MONTHLY",
            "service_days": 26,
            "delivery_eligible": True,
            "is_active": True,
            "description": "Light, easily digestible dinners like chapati, phulka, and grain-based specials."
        }
    ]

    for plan_data in default_plans:
        existing = await plans_col.find_one({"name": plan_data["name"]})
        if not existing:
            plan_data["created_at"] = datetime.now(timezone.utc)
            plan_data["updated_at"] = datetime.now(timezone.utc)
            await plans_col.insert_one(plan_data)
            print(f"Seeded meal plan: {plan_data['name']}")

    # 3. Seed Sample Customers
    cust_col = database.db.customers
    try:
        await cust_col.create_index("phone", unique=True)
    except Exception as e:
        print(f"Customer index note: {e}")

    sample_customers = [
        {
            "name": "Anitha Sharma",
            "phone": "9840123456",
            "whatsapp_number": "9840123456",
            "customer_type": CustomerType.INDIVIDUAL,
            "is_active": True,
            "address": {
                "address_line": "Flat 4B, Emerald Heights, 2nd Cross Street",
                "area": "Anna Nagar East",
                "landmark": "Near Roundtana Tower",
                "city": "Chennai",
                "pincode": "600102",
                "latitude": 13.0850,
                "longitude": 80.2150,
                "formatted_address": "Anna Nagar East, Chennai, Tamil Nadu 600102"
            },
            "meal_preference": {
                "diet_type": DietType.VEG,
                "sessions": [MealSession.LUNCH],
                "spice_level": SpiceLevel.MILD,
                "rice_preference": "Ponni Rice",
                "food_exclusions": "No Brinjal",
                "allergy_note": "Nut sensitivity",
                "delivery_instructions": "Leave at security desk if door is not answered"
            },
            "notes": "Regular corporate subscriber since 2025."
        },
        {
            "name": "Vikram Sundaram",
            "phone": "9791088776",
            "whatsapp_number": "9791088776",
            "customer_type": CustomerType.FAMILY,
            "is_active": True,
            "address": {
                "address_line": "15, 2nd Main Road, Shenoy Nagar",
                "area": "Shenoy Nagar",
                "landmark": "Opposite Shenoy Nagar Metro Station",
                "city": "Chennai",
                "pincode": "600030",
                "latitude": 13.0780,
                "longitude": 80.2240,
                "formatted_address": "Shenoy Nagar, Chennai, Tamil Nadu 600030"
            },
            "meal_preference": {
                "diet_type": DietType.NON_VEG,
                "sessions": [MealSession.LUNCH, MealSession.DINNER],
                "spice_level": SpiceLevel.NORMAL,
                "rice_preference": "Standard Boiled Rice",
                "food_exclusions": None,
                "allergy_note": None,
                "delivery_instructions": "Ring bell twice, 1st floor."
            },
            "notes": "Family subscription - 2 packs per session."
        },
        {
            "name": "Priya Narayanan",
            "phone": "9884055432",
            "whatsapp_number": "9884055432",
            "customer_type": CustomerType.INDIVIDUAL,
            "is_active": True,
            "address": {
                "address_line": "22/4, Gandhi Road, Kilpauk",
                "area": "Kilpauk",
                "landmark": "Behind Bhavans School",
                "city": "Chennai",
                "pincode": "600010",
                "latitude": 13.0805,
                "longitude": 80.2410,
                "formatted_address": "Kilpauk, Chennai, Tamil Nadu 600010"
            },
            "meal_preference": {
                "diet_type": DietType.VEG,
                "sessions": [MealSession.BREAKFAST, MealSession.LUNCH],
                "spice_level": SpiceLevel.NORMAL,
                "rice_preference": "Brown Rice",
                "food_exclusions": "Less oil preferred",
                "allergy_note": None,
                "delivery_instructions": "Hand over to receptionist"
            },
            "notes": "Office morning delivery requested before 8:30 AM."
        },
        {
            "name": "Rajesh Kanna",
            "phone": "9840299881",
            "whatsapp_number": "9840299881",
            "customer_type": CustomerType.OFFICE,
            "is_active": False,
            "address": {
                "address_line": "45/1 Usman Road, T. Nagar",
                "area": "T. Nagar",
                "landmark": "Near Panagal Park",
                "city": "Chennai",
                "pincode": "600017",
                "latitude": 13.0418,
                "longitude": 80.2341,
                "formatted_address": "Usman Road, T. Nagar, Chennai 600017"
            },
            "meal_preference": {
                "diet_type": DietType.NON_VEG,
                "sessions": [MealSession.LUNCH],
                "spice_level": SpiceLevel.SPICY,
                "rice_preference": "White Rice",
                "food_exclusions": None,
                "allergy_note": None,
                "delivery_instructions": "Office floor 3, IT department"
            },
            "notes": "Temporarily on hold for out of town travel."
        }
    ]

    for cust_data in sample_customers:
        existing = await cust_col.find_one({"phone": cust_data["phone"]})
        if not existing:
            cust_data["created_at"] = datetime.now(timezone.utc)
            cust_data["updated_at"] = datetime.now(timezone.utc)
            await cust_col.insert_one(cust_data)
            print(f"Seeded customer: {cust_data['name']}")

    # 4. Seed Sample Enquiries
    enq_col = database.db.enquiries
    sample_enquiries = [
        {
            "customer_name": "Suresh Babu",
            "phone": "9841122334",
            "requested_meal": "Lunch Only (Veg)",
            "number_of_persons": 1,
            "diet_type": DietType.VEG,
            "subscription_type": "SUBSCRIPTION",
            "delivery_location": "Nungambakkam High Road, Chennai",
            "quoted_price": 2799.0,
            "notes": "Requested trial for 3 days before monthly commitment.",
            "status": EnquiryStatus.NEW,
            "enquiry_date": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "customer_name": "Deepa Sundar",
            "phone": "9940055667",
            "requested_meal": "Dinner (Veg & Non-Veg)",
            "number_of_persons": 2,
            "diet_type": DietType.NON_VEG,
            "subscription_type": "SUBSCRIPTION",
            "delivery_location": "Chetpet, Harrington Road",
            "quoted_price": 5398.0,
            "notes": "Spoke on phone, sent meal menu via WhatsApp. Follow-up scheduled.",
            "status": EnquiryStatus.CONTACTED,
            "enquiry_date": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
    ]

    for enq_data in sample_enquiries:
        existing = await enq_col.find_one({"phone": enq_data["phone"]})
        if not existing:
            await enq_col.insert_one(enq_data)
            print(f"Seeded enquiry: {enq_data['customer_name']}")
