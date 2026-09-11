from datetime import datetime, timezone
from app.core import database
from app.core.security import get_password_hash
from app.schemas.user import UserRole


async def init_db():
    """Initializes the database with essential seed users if they do not exist."""
    if database.db is None:
        print("Database not connected, skipping seed initialization.")
        return

    users_collection = database.db.users
    
    # Ensure indexes for unique fields
    try:
        await users_collection.create_index("username", unique=True)
        await users_collection.create_index("email", unique=True, sparse=True)
        await users_collection.create_index("phone", unique=True, sparse=True)
    except Exception as e:
        print(f"Index creation note: {e}")

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
        existing = await users_collection.find_one({
            "$or": [
                {"username": user_data["username"]},
                {"email": user_data["email"]},
                {"phone": user_data["phone"]}
            ]
        })
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
            await users_collection.insert_one(doc)
            print(f"Seeded user: {user_data['username']} ({user_data['role']})")
        else:
            print(f"User {user_data['username']} already exists.")
