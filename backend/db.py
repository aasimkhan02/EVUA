from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

client: AsyncIOMotorClient = None
db = None


async def connect_db():
    global client, db
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]

    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.sessions.create_index("user_id")
    await db.sessions.create_index("created_at")
    await db.session_files.create_index([("session_id", 1), ("file_path", 1)])
    await db.decisions.create_index("session_id")
    await db.decisions.create_index("user_id")


async def close_db():
    global client
    if client:
        client.close()


def get_db():
    return db
