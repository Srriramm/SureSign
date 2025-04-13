import os
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions, ContentSettings
from datetime import datetime, timedelta
from azure.core.exceptions import AzureError, ResourceExistsError
from fastapi import HTTPException
import logging
import uuid
import hashlib
import asyncio
import urllib.parse

class AzureStorageService:
    def __init__(self):
        # Azure storage credentials
        self.connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        self.account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        self.account_key = os.getenv('AZURE_STORAGE_ACCOUNT_KEY')
        
        # Container names from environment variables
        self.container_user_selfies = os.getenv('AZURE_CONTAINER_USER_SELFIES', 'sec-user-kyc-images')
        self.container_property_docs = os.getenv('AZURE_CONTAINER_PROPERTY_DOCUMENTS', 'sec-property-legal-docs')
        self.container_property_images = os.getenv('AZURE_CONTAINER_PROPERTY_IMAGES', 'sec-property-verification-images')
        self.container_secure_docs = os.getenv('AZURE_CONTAINER_SECURE_DOCUMENTS', 'documents')
        self.container_doc_metadata = os.getenv('AZURE_CONTAINER_DOCUMENT_METADATA', 'document-metadata')
        
        # Security configuration
        self.public_access = os.getenv('AZURE_CONTAINER_PUBLIC_ACCESS', 'false').lower() == 'true'
        self.encryption_enabled = os.getenv('AZURE_BLOB_ENCRYPTION_ENABLED', 'true').lower() == 'true'
        self.container_policy = os.getenv('AZURE_CONTAINER_DEFAULT_POLICY', 'private')
        
        # Initialize blob service client to None
        self.blob_service_client = None
        
    async def get_blob_service_client(self):
        """Get a blob service client, creating a new one if necessary"""
        if not self.blob_service_client:
            # Check credentials and create a fallback connection string if needed
            if not self.connection_string or 'SharedAccessSignature' in self.connection_string:
                # If connection string is missing or contains SAS (which might expire),
                # create a new connection string from account name and key
                if self.account_name and self.account_key:
                    self.connection_string = f"DefaultEndpointsProtocol=https;AccountName={self.account_name};AccountKey={self.account_key};EndpointSuffix=core.windows.net"
                    logging.info("Created new connection string from account credentials")
                else:
                    raise ValueError("Azure Storage account name or key not set")
            
            if not self.account_name or not self.account_key:
                raise ValueError("Azure Storage account name or key not set")
            
            try:
                self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
                logging.info("Successfully initialized Azure Blob Service client")
            except Exception as e:
                logging.error(f"Failed to initialize Azure Blob Service client: {str(e)}")
                raise ValueError(f"Azure Storage initialization failed: {str(e)}")
                
        return self.blob_service_client
            
    async def refresh_connection(self):
        """
        Refresh the Azure Blob Storage connection using account name and key
        instead of potentially expired SAS tokens
        """
        try:
            if not self.account_name or not self.account_key:
                logging.error("Cannot refresh connection: missing account credentials")
                return False
                
            # Create direct connection string without SAS token
            self.connection_string = f"DefaultEndpointsProtocol=https;AccountName={self.account_name};AccountKey={self.account_key};EndpointSuffix=core.windows.net"
            
            # Close existing client if it exists
            if self.blob_service_client:
                await self.blob_service_client.close()
                
            # Reinitialize blob service client
            self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
            logging.info("Successfully refreshed Azure Blob Service connection")
            return True
        except Exception as e:
            logging.error(f"Failed to refresh Azure connection: {str(e)}")
            return False
        
    async def handle_azure_error(self, error, retry_method, *args, **kwargs):
        """
        Handle Azure errors with automatic retry for authentication issues
        
        :param error: The Azure exception that occurred
        :param retry_method: The method to retry on successful connection refresh
        :param args: Arguments to pass to the retry method
        :param kwargs: Keyword arguments to pass to the retry method
        :return: Result from retry_method if successful, otherwise raises HTTPException
        """
        error_message = str(error)
        
        # Check if error is related to authentication or SAS token expiration
        if "AuthenticationFailed" in error_message and ("Signature not valid" in error_message or "time frame" in error_message):
            logging.warning("Authentication failed due to expired SAS token, attempting to refresh connection")
            
            # Try to refresh the connection
            if await self.refresh_connection():
                logging.info("Connection refreshed, retrying operation...")
                # Retry the operation with the refreshed connection
                return await retry_method(*args, **kwargs)
        
        # If we get here, either it's not an auth error or the retry didn't work
        raise HTTPException(status_code=500, detail=f"Azure operation failed: {error_message}")
    
    async def create_secure_container(self, container_name):
        """
        Create a secured container with proper access controls
        """
        try:
            blob_service_client = await self.get_blob_service_client()
            container_client = blob_service_client.get_container_client(container_name)
            
            # Property images container should be public
            public_access = 'blob' if container_name == self.container_property_images else None
            
            try:
                await container_client.create_container(public_access=public_access)
            except ResourceExistsError:
                # For existing containers, we need to set access policy with signed_identifiers
                # The signed_identifiers parameter is a dictionary mapping ID values to access policy dict
                # For public blob access, we use an empty dict as per Azure SDK documentation
                if public_access:
                    await container_client.set_container_access_policy(
                        public_access=public_access,
                        signed_identifiers={}  # Required parameter, empty dict for no custom policy
                    )
                
            return container_client
        except Exception as e:
            logging.error(f"Failed to create secure container {container_name}: {str(e)}")
            raise
        
    def generate_secure_filename(self, original_filename, user_id=None):
        """
        Generate a secure, non-guessable filename for storage
        
        :param original_filename: Original file name
        :param user_id: Optional user ID to include in the hash
        :return: Secure filename
        """
        # Get file extension
        if '.' in original_filename:
            ext = original_filename.rsplit('.', 1)[1].lower()
        else:
            ext = 'bin'
        
        # Generate a random UUID
        random_id = str(uuid.uuid4())
        
        # Add user_id to the hash if provided
        if user_id:
            hash_base = f"{random_id}_{user_id}_{datetime.utcnow().timestamp()}"
        else:
            hash_base = f"{random_id}_{datetime.utcnow().timestamp()}"
        
        # Create a hash of the base
        filename_hash = hashlib.sha256(hash_base.encode()).hexdigest()[:16]
        
        # Return secure filename
        return f"{filename_hash}.{ext}"
        
    async def upload_file(self, container_name: str, file_name: str, file_content: bytes, content_type=None, metadata=None):
        """
        Upload a file to Azure Blob Storage and return a URL
        """
        try:
            # Map container type to actual container name if needed
            if container_name == 'user_selfies':
                container_name = self.container_user_selfies
            elif container_name == 'property_documents' or container_name == 'property-documents':
                container_name = self.container_property_docs
            elif container_name == 'property_images' or container_name == 'property-images':
                container_name = self.container_property_images
            elif container_name == 'secure_documents' or container_name == 'documents':
                container_name = self.container_secure_docs
            elif container_name == 'document_metadata' or container_name == 'document-metadata':
                container_name = self.container_doc_metadata
            
            # Create and get container with proper security settings
            container_client = await self.create_secure_container(container_name)
            
            # Get blob client
            blob_client = container_client.get_blob_client(file_name)
            
            # Set content settings
            content_settings = ContentSettings(
                content_type=content_type,
                content_disposition=f"inline; filename={file_name}",
                cache_control="public, max-age=31536000"  # 1 year cache
            )
            
            # Convert metadata to string if it's a dictionary
            if isinstance(metadata, dict):
                metadata = {str(k): str(v) for k, v in metadata.items()}
            
            # Upload file with content settings and metadata
            await blob_client.upload_blob(
                file_content, 
                overwrite=True,
                content_settings=content_settings,
                metadata=metadata
            )
            
            # Generate direct URL
            direct_url = blob_client.url
            
            # If container is private, generate a SAS URL
            if not self.public_access:
                sas_token = generate_blob_sas(
                    account_name=self.account_name,
                    container_name=container_name,
                    blob_name=file_name,
                    account_key=self.account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(days=7)
                )
                direct_url = f"{direct_url}?{sas_token}"
            
            return direct_url
            
        except Exception as e:
            logging.error(f"Failed to upload file {file_name} to container {container_name}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file: {str(e)}"
            )

    async def download_file(self, container_name: str, blob_path: str) -> bytes:
        """
        Download a file from Azure Blob Storage
        
        Args:
            container_name: Name of the container
            blob_path: Path of the blob within the container
            
        Returns:
            bytes: The content of the file
        """
        # URL decode the blob path to handle any encoded characters
        blob_path = urllib.parse.unquote(blob_path)
        
        # Map container names for backward compatibility
        if container_name == 'property-images':
            container_name = 'property_images'
        elif container_name == 'property-documents':
            container_name = 'property_documents'
        elif container_name == 'secure-documents':
            container_name = 'secure_documents'
        elif container_name == 'document-metadata':
            container_name = 'document_metadata'
            
        # Map container type to actual container name if needed
        if container_name == 'user_selfies':
            container_name = self.container_user_selfies
        elif container_name == 'property_documents':
            container_name = self.container_property_docs
        elif container_name == 'property_images':
            container_name = self.container_property_images
        elif container_name == 'secure_documents' or container_name == 'documents':
            container_name = self.container_secure_docs
        elif container_name == 'document_metadata' or container_name == 'document-metadata':
            container_name = self.container_doc_metadata
            
        logging.info(f"Mapped container name '{container_name}' for download")
        
        blob_service_client = None
        container_client = None
        blob_client = None
        content = None
        
        try:
            # Get blob service client
            blob_service_client = await self.get_blob_service_client()
            
            # Check if container exists
            container_exists = False
            try:
                container_client = blob_service_client.get_container_client(container_name)
                container_properties = await container_client.get_container_properties()
                container_exists = True
                logging.info(f"Container '{container_name}' exists")
            except Exception as container_error:
                logging.error(f"Container '{container_name}' does not exist: {str(container_error)}")
                raise HTTPException(status_code=404, detail=f"Container '{container_name}' not found")
                
            if not container_exists:
                logging.error(f"Container '{container_name}' does not exist")
                raise HTTPException(status_code=404, detail=f"Container '{container_name}' not found")
            
            # Get the blob client
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_path
            )
            
            # Check if blob exists
            try:
                blob_properties = await blob_client.get_blob_properties()
                logging.info(f"Blob '{blob_path}' exists in container '{container_name}'")
            except Exception as blob_error:
                logging.error(f"Blob '{blob_path}' not found in container '{container_name}': {str(blob_error)}")
                raise HTTPException(status_code=404, detail=f"File '{blob_path}' not found")
            
            # Download the blob
            download_stream = await blob_client.download_blob()
            content = await download_stream.readall()
            
            if not content:
                logging.error(f"Downloaded content is empty from {container_name}/{blob_path}")
                raise HTTPException(status_code=500, detail="Downloaded content is empty")
                
            logging.info(f"Successfully downloaded {len(content)} bytes from {container_name}/{blob_path}")
            return content
        except Exception as e:
            logging.error(f"Download failed: {str(e)}")
            raise

    async def delete_file(self, container_name: str, blob_name: str) -> bool:
        """
        Delete a file from Azure Blob Storage
        
        Args:
            container_name: Name of the container
            blob_name: Name of the blob to delete
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            # Get blob service client
            blob_service_client = await self.get_blob_service_client()
            
            # Get container client
            container_client = blob_service_client.get_container_client(container_name)
            
            # Get blob client
            blob_client = container_client.get_blob_client(blob_name)
            
            # Delete the blob
            await blob_client.delete_blob()
            
            return True
            
        except Exception as e:
            logging.error(f"Error deleting file from Azure: {str(e)}")
            return False

    async def close(self):
        """
        Close the blob service client and all associated connections
        """
        if self.blob_service_client:
            try:
                await self.blob_service_client.close()
                self.blob_service_client = None
                logging.info("Azure Blob Service client closed")
            except Exception as e:
                logging.error(f"Error closing Azure Blob Service client: {str(e)}")