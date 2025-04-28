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
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

    # Database settings
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "suresign")

    # Email settings
    EMAIL_HOST: str = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USER: str = os.getenv("EMAIL_USER", "your-email@gmail.com")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "your-app-password")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "SureSign <your-email@gmail.com>")

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

    # AI Model Configuration
    EMOTION_MODEL_NAME: str = os.getenv("EMOTION_MODEL_NAME", "j-hartmann/emotion-english-distilroberta-base")
    SPEECH_RECOGNITION_MODEL: str = os.getenv("SPEECH_RECOGNITION_MODEL", "facebook/wav2vec2-base-960h")
    FACE_DETECTION_CONFIDENCE: float = float(os.getenv("FACE_DETECTION_CONFIDENCE", "0.5"))
    FACE_TRACKING_CONFIDENCE: float = float(os.getenv("FACE_TRACKING_CONFIDENCE", "0.5"))

    # Audio Processing Configuration
    AUDIO_FORMAT: str = os.getenv("AUDIO_FORMAT", "pyaudio.paInt16")
    AUDIO_CHANNELS: int = int(os.getenv("AUDIO_CHANNELS", "1"))
    AUDIO_RATE: int = int(os.getenv("AUDIO_RATE", "16000"))
    AUDIO_CHUNK: int = int(os.getenv("AUDIO_CHUNK", "1024"))
    AUDIO_RECORD_SECONDS: int = int(os.getenv("AUDIO_RECORD_SECONDS", "2"))
    FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "C:/ffmpeg/bin/ffmpeg.exe")

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 