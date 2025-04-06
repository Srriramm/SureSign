from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class DocumentAccessLog(BaseModel):
    """Model for tracking document downloads"""
    id: Optional[str] = None
    buyer_id: str
    property_id: str
    document_index: int
    document_type: Optional[str] = None
    download_date: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    access_token: Optional[str] = None
    is_watermarked: bool = True
    is_signed: bool = False
    signature: Optional[str] = None
    download_expiry: Optional[datetime] = None

class DocumentAccessLimit(BaseModel):
    """Model for document access limits configuration"""
    buyer_id: str
    property_id: str
    document_index: int
    max_downloads: int = 3  # Default limit of 3 downloads per document
    download_count: int = 0
    first_access: Optional[datetime] = None
    last_access: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    is_expired: bool = False 