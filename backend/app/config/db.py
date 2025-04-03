from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'real_estate_platform')

# Create a single client instance
client = AsyncIOMotorClient(MONGO_URI)
database = client[DATABASE_NAME]

async def get_database():
    return database