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

class LawyerVerification(BaseModel):
    """Model for lawyer verification of property documents"""
    id: Optional[str] = None
    property_id: str
    buyer_id: str
    lawyer_name: str
    lawyer_email: str
    lawyer_phone: str
    access_token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    verification_status: str = "pending"  # pending, verified, issues_found
    verification_notes: Optional[str] = None
    issues_details: Optional[str] = None
    is_active: bool = True  # To deactivate old verifications if buyer changes lawyer
    documents_accessed: List[int] = []  # List of document indices that have been accessed 