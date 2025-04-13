from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Global database connection
_client = None
_db = None

async def get_database():
    """
    Get the database connection.
    Creates a new connection if one doesn't exist.
    """
    global _client, _db
    
    if _db is None:
        try:
            # Create client
            _client = AsyncIOMotorClient(settings.MONGO_URI)
            
            # Get database
            _db = _client[settings.DATABASE_NAME]
            
            # Test connection
            await _client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    return _db

async def close_database():
    """
    Close the database connection.
    """
    global _client, _db
    
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        logger.info("Closed MongoDB connection") 