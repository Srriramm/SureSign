import os
import hashlib
from typing import Dict, Tuple, Optional, List
from cryptography.fernet import Fernet
from app.config.azure_config import AzureStorageService
from app.services.blockchain_service import BlockchainService
from app.core.config import settings
import logging
import base64

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self, azure_storage: AzureStorageService, blockchain_service: BlockchainService):
        self.azure_storage = azure_storage
        self.blockchain_service = blockchain_service
        
        # Handle encryption key
        if settings.DOCUMENT_SECURITY_KEY:
            try:
                # Ensure the key is properly padded and encoded
                key = settings.DOCUMENT_SECURITY_KEY
                # Add padding if needed
                padding = len(key) % 4
                if padding:
                    key += '=' * (4 - padding)
                # Decode the base64 key
                self.encryption_key = base64.urlsafe_b64decode(key)
            except Exception as e:
                logger.error(f"Error decoding encryption key: {str(e)}")
                # Generate a new key if decoding fails
                self.encryption_key = Fernet.generate_key()
        else:
            # Generate a new key if none is provided
            self.encryption_key = Fernet.generate_key()
            
        self.fernet = Fernet(self.encryption_key)

    async def process_property_document(
        self,
        document_data: bytes,
        property_id: str,
        document_name: str,
        content_type: str
    ) -> Dict[str, str]:
        """
        Process and store a property document in both original and encrypted formats.
        
        Args:
            document_data: Raw bytes of the document
            property_id: ID of the property
            document_name: Original name of the document
            content_type: MIME type of the document
        
        Returns:
            Dictionary containing document URLs and metadata
        """
        try:
            # Generate unique blob names
            original_blob_name = f"{property_id}/{document_name}"
            encrypted_blob_name = f"{property_id}/encrypted_{document_name}"
            
            # Calculate document hash
            document_hash = hashlib.sha256(document_data).hexdigest()
            
            # Store original document in properties container
            original_url = await self.azure_storage.upload_blob(
                container_name=settings.AZURE_CONTAINER_PROPERTY_DOCUMENTS,
                blob_name=original_blob_name,
                data=document_data,
                content_type=content_type,
                metadata={
                    "property_id": property_id,
                    "document_hash": document_hash,
                    "is_encrypted": "false",
                    "download_limit": str(settings.DOCUMENT_MAX_DOWNLOAD_LIMIT),
                    "expiry_days": str(settings.DOCUMENT_DEFAULT_EXPIRY_DAYS)
                }
            )
            
            # Encrypt and store document in secure container
            encrypted_data = self.fernet.encrypt(document_data)
            encrypted_url = await self.azure_storage.upload_blob(
                container_name=settings.AZURE_CONTAINER_SECURE_DOCUMENTS,
                blob_name=encrypted_blob_name,
                data=encrypted_data,
                content_type=content_type,
                metadata={
                    "property_id": property_id,
                    "document_hash": document_hash,
                    "is_encrypted": "true",
                    "download_limit": str(settings.DOCUMENT_MAX_DOWNLOAD_LIMIT),
                    "expiry_days": str(settings.DOCUMENT_DEFAULT_EXPIRY_DAYS)
                }
            )
            
            # Store document hash in blockchain
            tx_hash = await self.blockchain_service.store_document_hash(document_hash)
            
            # Return document metadata
            return {
                "original_url": original_url,
                "encrypted_url": encrypted_url,
                "document_hash": document_hash,
                "blockchain_tx": tx_hash,
                "document_name": document_name,
                "content_type": content_type,
                "download_limit": settings.DOCUMENT_MAX_DOWNLOAD_LIMIT,
                "expiry_days": settings.DOCUMENT_DEFAULT_EXPIRY_DAYS
            }
            
        except Exception as e:
            logger.error(f"Error processing property document: {str(e)}")
            raise

    async def get_document(
        self,
        property_id: str,
        document_name: str,
        encrypted: bool = False
    ) -> Tuple[bytes, str]:
        """
        Retrieve a property document from storage.
        
        Args:
            property_id: ID of the property
            document_name: Name of the document
            encrypted: Whether to retrieve the encrypted version
        
        Returns:
            Tuple of (document_data, content_type)
        """
        try:
            container_name = settings.AZURE_CONTAINER_SECURE_DOCUMENTS if encrypted else settings.AZURE_CONTAINER_PROPERTY_DOCUMENTS
            blob_name = f"{property_id}/{'encrypted_' if encrypted else ''}{document_name}"
            
            # Download the document
            document_data = await self.azure_storage.download_blob(
                container_name=container_name,
                blob_name=blob_name
            )
            
            # Get document metadata
            metadata = await self.azure_storage.get_blob_metadata(
                container_name=container_name,
                blob_name=blob_name
            )
            
            # Decrypt if necessary
            if encrypted:
                document_data = self.fernet.decrypt(document_data)
            
            return document_data, metadata.get("content_type", "application/octet-stream")
            
        except Exception as e:
            logger.error(f"Error retrieving property document: {str(e)}")
            raise

    async def upload_document(self, property_id: str, document_data: bytes, document_name: str, document_type: str) -> Dict:
        try:
            # Generate a secure filename
            secure_filename = self.azure_storage.generate_secure_filename(document_name)
            
            # Upload the document
            document_url = await self.azure_storage.upload_file(
                container_name='property_documents',
                file_name=secure_filename,
                file_content=document_data,
                content_type='application/pdf',
                metadata={
                    'property_id': property_id,
                    'document_type': document_type,
                    'original_name': document_name
                }
            )
            
            # Register document hash on blockchain
            document_hash = self.blockchain_service.calculate_hash(document_data)
            await self.blockchain_service.register_document(property_id, document_hash, document_type)
            
            return {
                'url': document_url,
                'filename': secure_filename,
                'type': document_type,
                'hash': document_hash
            }
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}")
            raise

    async def download_document(self, property_id: str, document_name: str) -> Optional[bytes]:
        try:
            return await self.azure_storage.download_file(
                container_name='property_documents',
                blob_path=document_name
            )
        except Exception as e:
            logger.error(f"Error downloading document: {str(e)}")
            raise

    async def delete_document(self, property_id: str, document_name: str) -> bool:
        try:
            await self.azure_storage.delete_file(
                container_name='property_documents',
                file_name=document_name
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            raise

    async def get_document_metadata(self, property_id: str, document_name: str) -> Dict:
        try:
            return await self.azure_storage.get_file_metadata(
                container_name='property_documents',
                file_name=document_name
            )
        except Exception as e:
            logger.error(f"Error getting document metadata: {str(e)}")
            raise

    async def list_documents(self, property_id: str) -> List[Dict]:
        try:
            files = await self.azure_storage.list_files(
                container_name='property_documents',
                prefix=property_id
            )
            return [await self.get_document_metadata(property_id, file) for file in files]
        except Exception as e:
            logger.error(f"Error listing documents: {str(e)}")
            raise 