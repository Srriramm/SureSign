import motor.motor_asyncio
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get MongoDB connection string from environment variables
MONGODB_URL = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGODB_DB_NAME", "suresign_db")

if not MONGODB_URL:
    raise ValueError("MONGODB_URL environment variable is not set")

# Create a client instance
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)

async def get_database():
    """
    Get the MongoDB database instance
    """
    try:
        # Log connection status
        await client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Return the database instance
        return client[DB_NAME]
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise 