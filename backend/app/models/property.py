from pydantic import BaseModel, ConfigDict, Field, field_serializer, BeforeValidator
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
import uuid

def convert_to_str(value: int | float | str) -> str:
    return str(value)

class PropertyModel(BaseModel):
    """
    Represents a property listing in the system.
    """
    # Change from ObjectId to UUID
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), alias="_id")
    
    seller_id: str = Field(..., description="ID of the seller listing the property")
    
    # Land-specific fields
    survey_number: str = Field(..., description="Survey number of the land")
    plot_size: str = Field(..., description="Size of the plot in square feet")
    address: str = Field(..., description="Complete address of the land")
    price: str = Field(..., description="Price of the land in rupees")
    
    # Document types for land
    document_types: List[str] = Field(
        default_factory=list,
        description="Types of documents uploaded (Mother Deed, EC, Tax Receipt, etc.)"
    )
    
    # Media and document management
    images: List[str] = Field(default_factory=list, description="List of encrypted image URLs")
    documents: List[dict] = Field(default_factory=list, description="List of document information")
    document_hashes: List[str] = Field(default_factory=list, description="List of blockchain-stored document hashes")
    
    # Metadata and status
    status: str = Field(default="LIVE", description="Current status of the listing (LIVE, DRAFT, SOLD, etc.)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the property was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the property was last updated")

    # Pydantic configuration
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            datetime: lambda dt: dt.isoformat(),
            ObjectId: str
        }
    )

    # Serialization methods
    @field_serializer("id")
    def serialize_id(self, v: Optional[str], _info) -> Optional[str]:
        """Ensure ID is converted to a string for JSON serialization."""
        return str(v) if v else None

    def to_dict(self, exclude_unset: bool = False) -> dict:
        """
        Convert the model instance to a dictionary, ensuring consistent ID formatting.
        
        :param exclude_unset: Whether to exclude fields that were not set
        :return: Dictionary representation of the model
        """
        # Use model_dump with by_alias to handle both id and _id
        dump_dict = self.model_dump(exclude_unset=exclude_unset, by_alias=True)
        
        # Ensure '_id' is set to the same value as 'id'
        dump_dict['_id'] = dump_dict.get('id') or dump_dict.get('_id')
        
        return dump_dict

    @classmethod
    def from_dict(cls, data: dict):
        """
        Create a PropertyModel instance from a dictionary, 
        handling both 'id' and '_id' fields.
        
        :param data: Dictionary of property data
        :return: PropertyModel instance
        """
        # Normalize the ID field
        if '_id' in data and 'id' not in data:
            data['id'] = data['_id']
        
        return cls(**data)