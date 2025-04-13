from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "SureSign"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    DEBUG: bool = False

    # Security settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database settings
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "suresign")

    # Azure Storage settings
    AZURE_STORAGE_ACCOUNT_NAME: str = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")
    AZURE_STORAGE_ACCOUNT_KEY: str = os.getenv("AZURE_STORAGE_ACCOUNT_KEY", "")
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
    AZURE_CONTAINER_USER_SELFIES: str = os.getenv("AZURE_CONTAINER_USER_SELFIES", "sec-user-kyc-images")
    AZURE_CONTAINER_PROPERTY_DOCUMENTS: str = os.getenv("AZURE_CONTAINER_PROPERTY_DOCUMENTS", "property-documents")
    AZURE_CONTAINER_PROPERTY_IMAGES: str = os.getenv("AZURE_CONTAINER_PROPERTY_IMAGES", "property-images")
    AZURE_CONTAINER_PUBLIC_ACCESS: str = os.getenv("AZURE_CONTAINER_PUBLIC_ACCESS", "false")
    AZURE_BLOB_ENCRYPTION_ENABLED: str = os.getenv("AZURE_BLOB_ENCRYPTION_ENABLED", "true")
    AZURE_CONTAINER_DEFAULT_POLICY: str = os.getenv("AZURE_CONTAINER_DEFAULT_POLICY", "private")
    AZURE_CONTAINER_SECURE_DOCUMENTS: str = os.getenv("AZURE_CONTAINER_SECURE_DOCUMENTS", "secure-documents")
    AZURE_CONTAINER_DOCUMENT_METADATA: str = os.getenv("AZURE_CONTAINER_DOCUMENT_METADATA", "document-metadata")

    # Blockchain settings
    INFURA_URL: str = os.getenv("INFURA_URL", "")
    CONTRACT_ADDRESS: str = os.getenv("CONTRACT_ADDRESS", "")
    ETHEREUM_PRIVATE_KEY: str = os.getenv("ETHEREUM_PRIVATE_KEY", "")

    # Encryption settings
    FILE_ENCRYPTION_KEY: str = os.getenv("FILE_ENCRYPTION_KEY", "")
    ENCRYPTION_SALT: str = os.getenv("ENCRYPTION_SALT", "")
    DOCUMENT_SECURITY_KEY: str = os.getenv("DOCUMENT_SECURITY_KEY", "")

    # Document settings
    MAX_DOCUMENT_SIZE_MB: int = 10
    ALLOWED_DOCUMENT_TYPES: list = ["application/pdf"]
    DOCUMENT_DEFAULT_EXPIRY_DAYS: int = int(os.getenv("DOCUMENT_DEFAULT_EXPIRY_DAYS", "7"))
    DOCUMENT_MAX_DOWNLOAD_LIMIT: int = int(os.getenv("DOCUMENT_MAX_DOWNLOAD_LIMIT", "3"))
    
    # Image settings
    MAX_IMAGE_SIZE_MB: int = 5
    ALLOWED_IMAGE_TYPES: list = ["image/jpeg", "image/png"]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 