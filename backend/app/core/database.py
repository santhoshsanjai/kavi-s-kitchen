import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import certifi
from app.core.config import settings

client = None
db = None
is_mock_db = False


async def connect_to_mongo():
    global client, db, is_mock_db
    print(f"Connecting to MongoDB ({settings.mongodb_uri[:25]}...)...")

    try:
        # Attempt connection to MongoDB Atlas with a 5-second timeout
        real_client = AsyncIOMotorClient(
            settings.mongodb_uri,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        # Verify connection by running a ping command
        await real_client.admin.command('ping')
        client = real_client
        db = client[settings.mongodb_db_name]
        is_mock_db = False
        print(f"Successfully connected to MongoDB Atlas database: '{settings.mongodb_db_name}'")
    except Exception as e:
        print(f"Notice: Could not connect to MongoDB Atlas cluster ({e}).")
        print("Note: In MongoDB Atlas, ensure your current IP address is added to 'Network Access' (or allow 0.0.0.0/0).")
        print("Falling back to in-memory async MongoDB (mongomock-motor) for seamless local development...")
        
        try:
            from mongomock_motor import AsyncMongoMockClient
            mock_client = AsyncMongoMockClient()
            client = mock_client
            db = client[settings.mongodb_db_name]
            is_mock_db = True
            print(f"In-memory MongoDB initialized successfully for database: '{settings.mongodb_db_name}'")
        except Exception as mock_err:
            print(f"Critical error initializing mock MongoDB: {mock_err}")
            raise e


async def close_mongo_connection():
    global client
    if client and not is_mock_db:
        client.close()
        print("Disconnected from MongoDB")
