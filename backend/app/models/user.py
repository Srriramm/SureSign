from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_serializer
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic validation and serialization."""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")

class BaseUser(BaseModel):
    """Base model for users with common attributes."""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str = Field(..., min_length=2, max_length=50)
    mobile_number: str = Field(..., min_length=10, max_length=15)
    email: EmailStr
    password: str
    selfie_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_verified: bool = False

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        from_attributes=True
    )

    @field_serializer("id")
    def serialize_objectid(self, v: Optional[ObjectId], _info) -> Optional[str]:
        """Ensure ObjectId is converted to string for JSON serialization."""
        return str(v) if v else None

    def to_dict(self, exclude_unset: bool = False) -> Dict[str, Any]:
        """
        Convert model instance to dictionary with optional exclusion of unset fields.
        """
        dump_dict = self.model_dump(exclude_unset=exclude_unset, by_alias=True)
        dump_dict["_id"] = str(self.id) if self.id else None
        dump_dict["type"] = self.type  # Explicitly set the type attribute
        return dump_dict

class Seller(BaseUser):
    """Seller model extending BaseUser."""
    type: Literal["seller"] = "seller"

class Buyer(BaseUser):
    """Buyer model extending BaseUser."""
    type: Literal["buyer"] = "buyer"
