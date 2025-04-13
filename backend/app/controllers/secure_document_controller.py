import logging
from datetime import datetime
import hashlib
import json
from typing import Tuple, Optional
from app.services.secure_document_service import SecureDocumentService
from app.config.azure_config import AzureStorageService

class SecureDocumentController:
    def __init__(self, azure_storage: AzureStorageService):
        self.azure_storage = azure_storage
        self.secure_document_service = SecureDocumentService(azure_storage)
        
    @staticmethod
    async def apply_security_to_document(
        content: bytes,
        content_type: str,
        buyer_id: str,
        property_id: str,
        document_index: int
    ) -> Tuple[bytes, Optional[str]]:
        """
        Apply buyer-specific security features to a document.
        Returns the secured content and a digital signature.
        """
        try:
            # Generate a unique document identifier for this buyer
            document_id = hashlib.sha256(
                f"{buyer_id}_{property_id}_{document_index}_{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()
            
            # Create metadata for the document
            metadata = {
                "document_id": document_id,
                "buyer_id": buyer_id,
                "property_id": property_id,
                "document_index": document_index,
                "timestamp": datetime.utcnow().isoformat(),
                "content_type": content_type
            }
            
            # Apply watermark with buyer information
            watermarked_content = await SecureDocumentService.apply_watermark(
                content=content,
                watermark_data=json.dumps(metadata),
                content_type=content_type
            )
            
            # Generate a digital signature
            signature = await SecureDocumentService.generate_signature(
                content=watermarked_content,
                metadata=metadata
            )
            
            return watermarked_content, signature
            
        except Exception as e:
            logging.error(f"Error applying security features to document: {str(e)}")
            raise
            
    async def store_secured_document(
        self,
        content: bytes,
        metadata: dict,
        signature: str
    ) -> str:
        """
        Store a secured document with its metadata and signature.
        Returns the document URL.
        """
        try:
            # Store the document
            document_url = await self.azure_storage.upload_file(
                container_name=self.azure_storage.container_secure_docs,
                file_content=content,
                blob_path=f"{metadata['buyer_id']}/{metadata['property_id']}/documents/{metadata['document_id']}",
                content_type=metadata['content_type']
            )
            
            # Store the metadata
            await self.azure_storage.upload_file(
                container_name=self.azure_storage.container_document_metadata,
                file_content=json.dumps(metadata).encode(),
                blob_path=f"{metadata['buyer_id']}/{metadata['property_id']}/documents/{metadata['document_id']}_metadata.json",
                content_type="application/json"
            )
            
            # Store the signature
            await self.azure_storage.upload_file(
                container_name=self.azure_storage.container_document_metadata,
                file_content=signature.encode(),
                blob_path=f"{metadata['buyer_id']}/{metadata['property_id']}/documents/{metadata['document_id']}_signature.txt",
                content_type="text/plain"
            )
            
            return document_url
            
        except Exception as e:
            logging.error(f"Error storing secured document: {str(e)}")
            raise 