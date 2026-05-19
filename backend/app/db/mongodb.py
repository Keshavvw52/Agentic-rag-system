from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config.settings import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo():
    global _client, _db
    print("Connecting to MongoDB...")
    _client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
    )
    _db = _client[settings.MONGODB_DB_NAME]
    print(f"MongoDB client created for database: {settings.MONGODB_DB_NAME}")
    print("Creating MongoDB indexes...")
    await _create_indexes()
    print(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")


async def close_mongo_connection():
    global _client
    if _client:
        _client.close()
        print("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not initialized. Call connect_to_mongo() first.")
    return _db


async def _create_indexes():
    """Create database indexes for performance."""
    db = get_database()
    print("Creating index: users.email")
    # Users
    await db.users.create_index("email", unique=True)
    print("Creating index: users.username")
    await db.users.create_index("username", unique=True)
    # Documents
    print("Creating index: documents(user_id, created_at)")
    await db.documents.create_index([("user_id", 1), ("created_at", -1)])
    # Queries
    print("Creating index: queries(user_id, created_at)")
    await db.queries.create_index([("user_id", 1), ("created_at", -1)])
    # Traces
    print("Creating index: traces.query_id")
    await db.traces.create_index("query_id", unique=True)
    # Evaluations
    print("Creating index: evaluations(user_id, created_at)")
    await db.evaluations.create_index([("user_id", 1), ("created_at", -1)])
