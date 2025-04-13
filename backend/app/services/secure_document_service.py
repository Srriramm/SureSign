import os
import hashlib
import base64
import json
from typing import Dict, Tuple, Optional
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from app.config.azure_config import AzureStorageService
from app.core.config import settings
import logging
import uuid
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

class SecureDocumentService:
    def __init__(self, azure_storage: AzureStorageService):
        self.azure_storage = azure_storage
        self.salt_length = 16  # 128 bits
        self.iteration_count = 100000  # High iteration count for PBKDF2
        self.key_length = 32  # 256 bits for AES-256
        
        # Use container names from settings
        self.property_documents_container = settings.AZURE_CONTAINER_PROPERTY_DOCUMENTS
        self.secure_documents_container = settings.AZURE_CONTAINER_SECURE_DOCUMENTS
        self.document_metadata_container = settings.AZURE_CONTAINER_DOCUMENT_METADATA
        
        # We need to use a consistent encryption key - this one should come from environment variables
        # or be stored securely elsewhere, but for now we'll use a fixed key for consistency
        self.encryption_key = self._get_encryption_key()

    def _get_encryption_key(self) -> bytes:
        """
        Get the encryption key from environment or generate a new one.
        In production, this should retrieve the key from a secure key vault.
        """
        # Check if encryption key exists in environment
        env_key = os.getenv('DOCUMENT_ENCRYPTION_KEY')
        if env_key:
            try:
                # Ensure the key is properly formatted for Fernet
                if len(base64.urlsafe_b64decode(env_key)) == 32:
                    return env_key
            except:
                logging.warning("Invalid encryption key format in environment, generating new key")
        
        # Generate a new key with Fernet
        key = Fernet.generate_key()
        logging.warning("Generated new encryption key. In production, this should be stored securely.")
        return key

    def _generate_salt(self) -> bytes:
        """Generate a random salt for key derivation."""
        return os.urandom(self.salt_length)

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.key_length,
            salt=salt,
            iterations=self.iteration_count,
            backend=default_backend()
        )
        # Use a consistent system key for derivation
        system_key = base64.urlsafe_b64decode(self.encryption_key)
        return kdf.derive(system_key)

    def _add_watermark(self, document_data: bytes, owner_id: str, timestamp: str, doc_id: str) -> bytes:
        """
        Add invisible watermark to document.
        For binary files, we should not modify the content directly as it will corrupt the file.
        """
        # For binary files (PDF, images, etc.), we should NOT modify the content directly
        # Instead, the watermark info should be stored in metadata
        # We'll return the original document data unchanged
        return document_data

    def _encrypt_document(self, document_data: bytes, key: bytes) -> Tuple[bytes, bytes]:
        """Encrypt document using AES-256 in CBC mode."""
        # Generate a random IV
        iv = os.urandom(16)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        
        # Pad the data to be a multiple of 16 bytes (AES block size)
        padder = self._pad_content(document_data)
        
        # Encrypt
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(padder) + encryptor.finalize()
        
        return encrypted_data, iv

    async def process_document(
        self,
        document_data: bytes,
        document_name: str,
        owner_id: str,
        content_type: str,
        property_id: str,
        blockchain_service=None  # Optional blockchain service for verification
    ) -> Dict[str, str]:
        """
        Process and store a document with encryption and watermarking.
        """
        try:
            # Generate unique document ID
            doc_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            # Calculate document hash
            document_hash = hashlib.sha256(document_data).hexdigest()
            
            # Update path structure to include property_id
            original_blob_name = f"{owner_id}/{property_id}/documents/{document_name}"
            
            # Upload original document first
            logging.info(f"Uploading original document: {original_blob_name}")
            original_url = await self.azure_storage.upload_file(
                container_name=self.property_documents_container,
                file_name=original_blob_name,
                file_content=document_data,
                content_type=content_type
            )
            
            # Generate salt and derive key
            salt = self._generate_salt()
            key = self._derive_key(salt)
            
            # Encrypt document WITHOUT adding watermark to the binary data
            encrypted_data, iv = self._encrypt_document(document_data, key)
            
            # If blockchain service is provided, register document hash
            blockchain_tx_hash = None
            if blockchain_service:
                try:
                    blockchain_tx_hash = await blockchain_service.register_document(
                        document_hash=document_hash,
                        owner_id=owner_id,
                        document_id=doc_id,
                        timestamp=timestamp
                    )
                except Exception as e:
                    logger.error(f"Failed to register document on blockchain: {str(e)}")
            
            # Create metadata with watermark info, blockchain hash and property_id
            metadata = {
                "document_name": document_name,
                "salt": base64.b64encode(salt).decode(),
                "iv": base64.b64encode(iv).decode(),
                "document_hash": document_hash,
                "owner_id": owner_id,
                "property_id": property_id,
                "timestamp": timestamp,
                "document_id": doc_id,
                "encryption_algorithm": "AES-256-CBC",
                "key_derivation": {
                    "algorithm": "PBKDF2-HMAC-SHA256",
                    "iterations": self.iteration_count
                },
                "content_type": content_type,
                "watermark": {
                    "owner_id": owner_id,
                    "timestamp": timestamp,
                    "document_id": doc_id
                },
                "blockchain_verification": {
                    "tx_hash": blockchain_tx_hash,
                    "network": "sepolia",
                    "verification_url": f"https://sepolia.etherscan.io/tx/{blockchain_tx_hash}" if blockchain_tx_hash else None
                }
            }
            
            # Update path structure for encrypted document
            encrypted_blob_name = f"{owner_id}/{property_id}/documents/{doc_id}_{document_name}"
            logging.info(f"Uploading encrypted document: {encrypted_blob_name}")
            encrypted_url = await self.azure_storage.upload_file(
                container_name=self.secure_documents_container,
                file_name=encrypted_blob_name,
                file_content=encrypted_data,
                content_type=content_type,
                metadata=metadata
            )
            
            # Update path structure for metadata
            metadata_blob_name = f"{owner_id}/{property_id}/documents/{doc_id}_metadata.json"
            logging.info(f"Uploading document metadata: {metadata_blob_name}")
            metadata_content = json.dumps(metadata).encode()
            await self.azure_storage.upload_file(
                container_name=self.document_metadata_container,
                file_name=metadata_blob_name,
                file_content=metadata_content,
                content_type="application/json"
            )
            
            return {
                "document_id": doc_id,
                "property_id": property_id,
                "original_url": original_url,
                "encrypted_url": encrypted_url,
                "document_hash": document_hash,
                "blockchain_tx_hash": blockchain_tx_hash,
                "owner_id": owner_id,
                "timestamp": timestamp,
                "content_type": content_type,
                "document_name": document_name
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise

    async def retrieve_document(self, document_id: str, owner_id: str, property_id: str) -> bytes:
        """
        Retrieve a document from secure storage.
        """
        try:
            logging.info(f"Retrieving document: ID={document_id}, owner={owner_id}, property={property_id}")
            
            # Try to fetch the original document first as a fallback
            try:
                # Get metadata to find the document name
                metadata_blob_name = f"{owner_id}/{property_id}/documents/{document_id}_metadata.json"
                logging.info(f"Fetching metadata from path: {metadata_blob_name}")
                
                metadata_content = await self.azure_storage.download_file(
                    container_name=self.document_metadata_container,
                    blob_path=metadata_blob_name
                )
                
                if metadata_content:
                    metadata = json.loads(metadata_content)
                    document_name = metadata.get('document_name')
                    content_type = metadata.get('content_type')
                    
                    # First attempt: Try to get the original unencrypted document
                    original_blob_name = f"{owner_id}/{property_id}/documents/{document_name}"
                    logging.info(f"Attempting to fetch original document: {original_blob_name}")
                    
                    original_content = await self.azure_storage.download_file(
                        container_name=self.property_documents_container,
                        blob_path=original_blob_name
                    )
                    
                    if original_content and len(original_content) > 0:
                        logging.info(f"Successfully retrieved original document ({len(original_content)} bytes)")
                        return original_content
                    
                    # Second attempt: Try to get the encrypted document and decrypt it
                    encrypted_blob_name = f"{owner_id}/{property_id}/documents/{document_id}_{document_name}"
                    logging.info(f"Fetching encrypted document: {encrypted_blob_name}")
                    
                    encrypted_content = await self.azure_storage.download_file(
                        container_name=self.secure_documents_container,
                        blob_path=encrypted_blob_name
                    )
                    
                    if encrypted_content and len(encrypted_content) > 0:
                        # Extract decryption parameters from metadata
                        salt = base64.b64decode(metadata.get('salt', ''))
                        iv = base64.b64decode(metadata.get('iv', ''))
                        
                        if salt and iv:
                            try:
                                # Derive the same key used for encryption
                                key = self._derive_key(salt)
                                
                                # Create cipher for decryption
                                cipher = Cipher(
                                    algorithms.AES(key),
                                    modes.CBC(iv),
                                    backend=default_backend()
                                )
                                
                                # Decrypt
                                decryptor = cipher.decryptor()
                                decrypted_padded = decryptor.update(encrypted_content) + decryptor.finalize()
                                
                                # Remove padding
                                decrypted_content = self._unpad_content(decrypted_padded)
                                
                                if len(decrypted_content) > 0:
                                    logging.info(f"Successfully decrypted document ({len(decrypted_content)} bytes)")
                                    return decrypted_content
                            except Exception as e:
                                logging.error(f"Error during decryption: {str(e)}")
                
                # Last resort: attempt to find a document with the document_id in the filename
                logging.warning("Trying alternative method to locate document")
                fallback_blob_name = f"{owner_id}/{property_id}/documents/{document_id}_*"
                
                # This would require implementing a list_blobs method in AzureStorageService
                # For now, we'll raise an exception
                raise ValueError("Document not found through standard retrieval methods")
                
            except Exception as inner_e:
                logging.error(f"Error in document retrieval process: {str(inner_e)}")
                raise
                
        except Exception as e:
            logging.error(f"Error retrieving document: {str(e)}")
            raise
            
    def _pad_content(self, content: bytes) -> bytes:
        """Add PKCS7 padding to the content."""
        block_size = 16
        padding_length = block_size - (len(content) % block_size)
        padding = bytes([padding_length] * padding_length)
        return content + padding
        
    def _unpad_content(self, content: bytes) -> bytes:
        """Remove PKCS7 padding from the content."""
        try:
            padding_length = content[-1]
            # Validate padding
            if padding_length > 16:
                # Invalid padding, return as is
                return content
            for i in range(1, padding_length + 1):
                if content[-i] != padding_length:
                    # Invalid padding, return as is
                    return content
            return content[:-padding_length]
        except IndexError:
            # Handle empty content
            return content
            
    async def decrypt_document(self, encrypted_content: bytes, iv: bytes, salt: bytes) -> bytes:
        """
        Decrypt a document using the provided parameters.
        """
        try:
            # Derive the key using the same salt
            key = self._derive_key(salt)
            
            # Create cipher for decryption
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend()
            )
            
            # Decrypt the content
            decryptor = cipher.decryptor()
            decrypted_content = decryptor.update(encrypted_content) + decryptor.finalize()
            
            # Remove padding
            return self._unpad_content(decrypted_content)
            
        except Exception as e:
            logging.error(f"Decryption error: {str(e)}")
            raise

    @staticmethod
    async def apply_watermark(
        content: bytes,
        watermark_data: str,
        content_type: str
    ) -> bytes:
        """
        Apply an invisible digital watermark to the document.
        The watermark contains metadata about the document and buyer.
        """
        try:
            # For PDF documents
            if content_type == "application/pdf":
                # Add watermark as metadata
                # This is a simplified example - in production, use a proper PDF library
                watermark = f"<!-- {watermark_data} -->"
                return content + watermark.encode()
                
            # For image documents
            elif content_type in ["image/jpeg", "image/png"]:
                # Add watermark in image metadata
                # This is a simplified example - in production, use a proper image library
                watermark = f"<!-- {watermark_data} -->"
                return content + watermark.encode()
                
            # For other document types
            else:
                # Add watermark as a comment or metadata
                watermark = f"<!-- {watermark_data} -->"
                return content + watermark.encode()
                
        except Exception as e:
            logging.error(f"Error applying watermark: {str(e)}")
            raise
            
    @staticmethod
    async def generate_signature(
        content: bytes,
        metadata: dict
    ) -> str:
        """
        Generate a digital signature for the document.
        The signature is based on the document content and metadata.
        """
        try:
            # Create a hash of the document content
            content_hash = hashlib.sha256(content).hexdigest()
            
            # Create a hash of the metadata
            metadata_hash = hashlib.sha256(
                json.dumps(metadata, sort_keys=True).encode()
            ).hexdigest()
            
            # Combine hashes and create final signature
            combined_hash = hashlib.sha256(
                f"{content_hash}{metadata_hash}".encode()
            ).hexdigest()
            
            return combined_hash
            
        except Exception as e:
            logging.error(f"Error generating signature: {str(e)}")
            raise
            
    async def encrypt_document(self, content: bytes) -> bytes:
        """
        Encrypt the document using AES-256.
        """
        try:
            # Generate a random IV
            iv = os.urandom(16)
            
            # Create cipher with the correct key size
            key = base64.urlsafe_b64decode(self.encryption_key)
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend()
            )
            
            # Encrypt the content
            encryptor = cipher.encryptor()
            padded_content = self._pad_content(content)
            encrypted_content = encryptor.update(padded_content) + encryptor.finalize()
            
            # Return IV + encrypted content
            return iv + encrypted_content
            
        except Exception as e:
            logging.error(f"Error encrypting document: {str(e)}")
            raise
            
    async def repair_document(self, content: bytes, content_type: str) -> bytes:
        """
        Repair a document by removing invalid watermarks or metadata that may have been incorrectly added.
        This ensures the document will open properly in viewers.
        """
        try:
            # For PDF files, ensure they start with %PDF
            if content_type == 'application/pdf':
                # Check if file starts with PDF signature
                if not content.startswith(b'%PDF'):
                    # Try to find PDF signature
                    pdf_start = content.find(b'%PDF')
                    if pdf_start > 0:
                        logging.info(f"Repairing PDF - removing {pdf_start} bytes from start")
                        content = content[pdf_start:]
                
                # Remove any HTML comments that might be appended at the end
                html_comment_start = content.find(b'<!--')
                if html_comment_start > 0:
                    logging.info(f"Repairing PDF - removing HTML comments from end")
                    content = content[:html_comment_start]
                    
            # For JPEG images
            elif content_type == 'image/jpeg':
                # JPEG should start with SOI marker FF D8
                if not content.startswith(b'\xFF\xD8'):
                    jpeg_start = content.find(b'\xFF\xD8')
                    if jpeg_start > 0:
                        logging.info(f"Repairing JPEG - removing {jpeg_start} bytes from start")
                        content = content[jpeg_start:]
                
                # Remove any HTML comments that might be appended at the end
                html_comment_start = content.find(b'<!--')
                if html_comment_start > 0:
                    logging.info(f"Repairing JPEG - removing HTML comments from end")
                    content = content[:html_comment_start]
                    
            # For PNG images
            elif content_type == 'image/png':
                # PNG should start with the PNG signature
                png_signature = b'\x89PNG\r\n\x1a\n'
                if not content.startswith(png_signature):
                    png_start = content.find(png_signature)
                    if png_start > 0:
                        logging.info(f"Repairing PNG - removing {png_start} bytes from start")
                        content = content[png_start:]
                
                # Remove any HTML comments that might be appended at the end
                html_comment_start = content.find(b'<!--')
                if html_comment_start > 0:
                    logging.info(f"Repairing PNG - removing HTML comments from end")
                    content = content[:html_comment_start]
            
            return content
        except Exception as e:
            logging.error(f"Error repairing document: {str(e)}")
            # Return the original content if repair fails
            return content 
            raise 