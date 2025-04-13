import os
import base64
import json
import logging
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import gray
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

class DocumentHandler:
    def __init__(self, connection_string: str):
        """Initialize the document handler with Azure connection string."""
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.secure_container = "secure-documents"
        self.keys_container = "encryption-keys"
        self.metadata_container = "document-metadata"
        self.downloads_container = "document-downloads"
        
        # Create containers if they don't exist
        self._ensure_containers_exist()
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _ensure_containers_exist(self):
        """Ensure all required containers exist in Azure Blob Storage."""
        containers = [
            self.secure_container,
            self.keys_container,
            self.metadata_container,
            self.downloads_container
        ]
        for container_name in containers:
            try:
                self.blob_service_client.create_container(container_name)
            except Exception as e:
                self.logger.warning(f"Container {container_name} already exists or error: {str(e)}")

    def _generate_encryption_key(self) -> bytes:
        """Generate a new Fernet encryption key."""
        return Fernet.generate_key()

    def _generate_rsa_keys(self):
        """Generate RSA key pair for digital signatures."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem, public_pem

    def _add_watermark(self, pdf_content: bytes, watermark_text: str) -> bytes:
        """Add watermark to PDF content."""
        # Create a temporary PDF with watermark
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        # Create watermark
        for page in doc:
            page.insert_text((50, 50), watermark_text, fontsize=12, color=(0.5, 0.5, 0.5))
        
        # Save to bytes
        return doc.write()

    def _sign_document(self, content: bytes, private_key: bytes) -> bytes:
        """Digitally sign the document content."""
        private_key_obj = serialization.load_pem_private_key(private_key, password=None)
        signature = private_key_obj.sign(
            content,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature

    def _verify_signature(self, content: bytes, signature: bytes, public_key: bytes) -> bool:
        """Verify the document signature."""
        try:
            public_key_obj = serialization.load_pem_public_key(public_key)
            public_key_obj.verify(
                signature,
                content,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception as e:
            self.logger.error(f"Signature verification failed: {str(e)}")
            return False

    def _encrypt_file(self, content: bytes, key: bytes) -> bytes:
        """Encrypt file content using Fernet."""
        f = Fernet(key)
        return f.encrypt(content)

    def _decrypt_file(self, encrypted_content: bytes, key: bytes) -> bytes:
        """Decrypt file content using Fernet."""
        f = Fernet(key)
        return f.decrypt(encrypted_content)

    async def upload_document(self, file_content: bytes, original_filename: str, seller_info: dict) -> dict:
        """Upload and process a document with encryption and watermarking."""
        try:
            # Generate keys
            encryption_key = self._generate_encryption_key()
            private_key, public_key = self._generate_rsa_keys()
            
            # Generate document ID
            document_id = base64.urlsafe_b64encode(os.urandom(16)).decode()
            
            # Sign the document
            signature = self._sign_document(file_content, private_key)
            
            # Encrypt the document
            encrypted_content = self._encrypt_file(file_content, encryption_key)
            
            # Store encrypted document
            blob_name = f"{document_id}/{original_filename}"
            blob_client = self.blob_service_client.get_blob_client(
                container=self.secure_container,
                blob=blob_name
            )
            blob_client.upload_blob(encrypted_content, overwrite=True)
            
            # Store keys
            keys_blob_name = f"{document_id}/keys.json"
            keys_data = {
                "encryption_key": base64.b64encode(encryption_key).decode(),
                "public_key": base64.b64encode(public_key).decode(),
                "signature": base64.b64encode(signature).decode()
            }
            keys_blob_client = self.blob_service_client.get_blob_client(
                container=self.keys_container,
                blob=keys_blob_name
            )
            keys_blob_client.upload_blob(json.dumps(keys_data), overwrite=True)
            
            # Store metadata
            metadata = {
                "document_id": document_id,
                "original_filename": original_filename,
                "upload_date": datetime.utcnow().isoformat(),
                "seller_info": seller_info,
                "content_type": "application/pdf"  # Assuming PDF for now
            }
            metadata_blob_client = self.blob_service_client.get_blob_client(
                container=self.metadata_container,
                blob=f"{document_id}/metadata.json"
            )
            metadata_blob_client.upload_blob(json.dumps(metadata), overwrite=True)
            
            return {
                "document_id": document_id,
                "filename": original_filename,
                "url": f"secure-documents/{document_id}/{original_filename}"
            }
            
        except Exception as e:
            self.logger.error(f"Error uploading document: {str(e)}")
            raise

    async def retrieve_document(self, document_id: str, buyer_info: dict = None) -> dict:
        """Retrieve and process a document with decryption and optional watermarking."""
        try:
            # Get metadata
            metadata_blob_client = self.blob_service_client.get_blob_client(
                container=self.metadata_container,
                blob=f"{document_id}/metadata.json"
            )
            metadata = json.loads(metadata_blob_client.download_blob().readall())
            
            # Get keys
            keys_blob_client = self.blob_service_client.get_blob_client(
                container=self.keys_container,
                blob=f"{document_id}/keys.json"
            )
            keys_data = json.loads(keys_blob_client.download_blob().readall())
            
            # Get encrypted document
            doc_blob_client = self.blob_service_client.get_blob_client(
                container=self.secure_container,
                blob=f"{document_id}/{metadata['original_filename']}"
            )
            encrypted_content = doc_blob_client.download_blob().readall()
            
            # Decrypt document
            encryption_key = base64.b64decode(keys_data["encryption_key"])
            decrypted_content = self._decrypt_file(encrypted_content, encryption_key)
            
            # Verify signature
            signature = base64.b64decode(keys_data["signature"])
            public_key = base64.b64decode(keys_data["public_key"])
            if not self._verify_signature(decrypted_content, signature, public_key):
                raise ValueError("Document signature verification failed")
            
            # Add watermark if buyer info is provided
            if buyer_info:
                watermark_text = (
                    f"Downloaded by: {buyer_info.get('name', 'Unknown')}\n"
                    f"Email: {buyer_info.get('email', 'Unknown')}\n"
                    f"Property: {buyer_info.get('property_info', 'Unknown')}\n"
                    f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                final_content = self._add_watermark(decrypted_content, watermark_text)
                
                # Store watermarked version
                download_blob_name = f"{document_id}/watermarked_{metadata['original_filename']}"
                download_blob_client = self.blob_service_client.get_blob_client(
                    container=self.downloads_container,
                    blob=download_blob_name
                )
                download_blob_client.upload_blob(final_content, overwrite=True)
                
                # Log download
                self._log_download(document_id, buyer_info)
                
                return {
                    "content": final_content,
                    "filename": f"watermarked_{metadata['original_filename']}",
                    "content_type": metadata["content_type"]
                }
            
            return {
                "content": decrypted_content,
                "filename": metadata["original_filename"],
                "content_type": metadata["content_type"]
            }
            
        except ResourceNotFoundError:
            self.logger.error(f"Document {document_id} not found")
            raise
        except Exception as e:
            self.logger.error(f"Error retrieving document: {str(e)}")
            raise

    def _log_download(self, document_id: str, buyer_info: dict):
        """Log document download information."""
        try:
            log_entry = {
                "document_id": document_id,
                "buyer_info": buyer_info,
                "download_time": datetime.utcnow().isoformat()
            }
            
            log_blob_name = f"{document_id}/downloads.json"
            log_blob_client = self.blob_service_client.get_blob_client(
                container=self.metadata_container,
                blob=log_blob_name
            )
            
            try:
                existing_logs = json.loads(log_blob_client.download_blob().readall())
            except ResourceNotFoundError:
                existing_logs = []
            
            existing_logs.append(log_entry)
            log_blob_client.upload_blob(json.dumps(existing_logs), overwrite=True)
            
        except Exception as e:
            self.logger.error(f"Error logging download: {str(e)}") 