# backend/database/mongodb_client.py
import os
from pymongo import MongoClient
from typing import Optional, Any
from config.settings import MONGODB_URI, DB_NAME

mongo_client: Optional[MongoClient] = None
db: Optional[Any] = None # Will hold the database object

async def connect_to_mongodb():
    """Establishes connection to MongoDB."""
    global mongo_client, db
    if mongo_client is None:
        try:
            mongo_client = MongoClient(MONGODB_URI)
            db = mongo_client[DB_NAME]
            # The ismaster command is cheap and does not require auth.
            mongo_client.admin.command('ismaster')
            print(f"Connected to MongoDB database: {DB_NAME}")
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
            # Re-raise the exception or handle appropriately in main.py
            raise

async def close_mongodb_connection():
    """Closes the MongoDB connection."""
    global mongo_client
    if mongo_client:
        mongo_client.close()
        mongo_client = None
        print("MongoDB connection closed.")

def get_db_collection(collection_name: str):
    """
    Returns a specific MongoDB collection.
    Raises an error if the database connection is not established.
    """
    global db
    if db is None:
        raise Exception("MongoDB database connection not established.")
    return db[collection_name]