from datetime import datetime
from bson import ObjectId
from typing import Optional, List
from pydantic import BaseModel, Field

class DocumentRequestBase(BaseModel):
    property_id: str
    buyer_id: str
    seller_id: str
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, approved, rejected
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    expiry_date: Optional[datetime] = None  # When access expires

class DocumentRequestCreate(DocumentRequestBase):
    pass

class DocumentRequestUpdate(BaseModel):
    status: str
    rejection_reason: Optional[str] = None
    expiry_date: Optional[datetime] = None

class DocumentRequestInDB(DocumentRequestBase):
    id: str = Field(alias="_id")

    class Config:
        populate_by_name = True

class DocumentRequestResponse(DocumentRequestBase):
    id: str
    buyer_name: Optional[str] = None
    seller_name: Optional[str] = None
    property_location: Optional[str] = None
    property_reference: Optional[str] = None 