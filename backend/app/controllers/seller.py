from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from typing import List, Optional
from bson import ObjectId
from datetime import datetime, timedelta
import uuid  # Added for generating unique IDs
import logging
from azure.core.exceptions import AzureError
from app.middleware.auth_middleware import AuthHandler
from app.config.db import get_database
from app.blockchain.smart_contract import BlockchainService
from app.services.secure_document_service import SecureDocumentService
from app.config.azure_config import AzureStorageService
import urllib.parse

class PropertyListingController:
    def __init__(self):
        self.auth_handler = AuthHandler()
        self.blockchain_service = None
        self.azure_storage = AzureStorageService()
        self.secure_document_service = SecureDocumentService(self.azure_storage)

    async def list_seller_properties(self, token_payload):
        """
        Retrieve properties listed by the seller
        """
        db = await get_database()
        properties_collection = db['properties']
        
        # Find all properties that have the seller_id matching the user's ID
        properties = await properties_collection.find(
            {'seller_id': token_payload['sub']}
        ).to_list(length=None)
        
        # Convert MongoDB ObjectId to string in each property
        for property_item in properties:
            if '_id' in property_item:
                property_item['_id'] = str(property_item['_id'])
        
        return properties

    async def get_seller_dashboard(self, token_payload):
        """
        Retrieve seller dashboard data
        """
        db = await get_database()
        seller_collection = db['sellers']
        properties_collection = db['properties']
        
        seller = await seller_collection.find_one({'_id': ObjectId(token_payload['sub'])})
        if not seller:
            raise HTTPException(status_code=404, detail="Seller not found")
        
        # Get properties for this seller from the properties collection
        properties = await properties_collection.find({
            'seller_id': token_payload['sub']
        }).to_list(length=None)
        
        # Aggregate dashboard metrics
        dashboard_data = {
            'total_properties': len(properties),
            'live_properties': len([p for p in properties if p.get('status') == 'LIVE']),
            'total_property_value': sum(p.get('price', 0) for p in properties),
            'average_property_size': (
                sum(p.get('square_feet', 0) for p in properties) / len(properties) 
                if properties else 0
            ),
            'recent_properties': properties[-5:] if len(properties) > 0 else []  # Last 5 properties
        }
        
        return dashboard_data

    async def get_property_details(self, token_payload, property_id):
        """
        Retrieve details of a specific property
        """
        db = await get_database()
        properties_collection = db['properties']
        
        property_doc = await properties_collection.find_one({
            'id': property_id,
            'seller_id': token_payload['sub']
        })
        
        if not property_doc:
            raise HTTPException(status_code=404, detail="Property not found or you don't have permission")
        
        # Convert MongoDB ObjectId to string
        if '_id' in property_doc:
            property_doc['_id'] = str(property_doc['_id'])
        
        return property_doc

    async def upload_property_images(self, seller_id: str, images: List[UploadFile]):
        """
        Upload property images to Azure Blob Storage (without encryption)
        """
        image_urls = []
        
        try:
            # Initialize Azure storage if not already done
            if not hasattr(self, 'azure_storage') or self.azure_storage is None:
                self.azure_storage = AzureStorageService()
                
            for image in images:
                # Read image file
                image_content = await image.read()
                
                # Generate unique filename
                filename = f"{seller_id}_{datetime.now().timestamp()}_{image.filename}"
                
                # Upload to Azure Blob Storage (property-images container)
                blob_url = await self.azure_storage.upload_file(
                    container_name=self.azure_storage.container_property_images,  # Use container from AzureStorageService
                    file_name=filename, 
                    file_content=image_content,
                    content_type=image.content_type
                )
                
                # Store both the SAS URL and direct URL
                image_urls.append({
                    'url': blob_url,  # This will be the direct URL if container is public
                    'filename': filename,
                    'content_type': image.content_type
                })
            
            return image_urls
        finally:
            if hasattr(self, 'azure_storage') and self.azure_storage is not None:
                await self.azure_storage.close()

    async def upload_property_documents(self, seller_id: str, property_id: str, documents: List[UploadFile], document_types: List[str]):
        """
        Upload property documents to Azure Blob Storage with encryption and blockchain verification
        """
        document_metadata_list = []
        
        try:
            # Initialize services if not already done
            if not self.blockchain_service:
                self.blockchain_service = await BlockchainService.create()
            
            for doc, doc_type in zip(documents, document_types):
                try:
                    # Read document file
                    doc_content = await doc.read()
                    
                    # Process document using SecureDocumentService with blockchain integration
                    doc_metadata = await self.secure_document_service.process_document(
                        document_data=doc_content,
                        document_name=doc.filename,
                        owner_id=seller_id,
                        content_type=doc.content_type,
                        property_id=property_id,  # Pass property_id to process_document
                        blockchain_service=self.blockchain_service
                    )
                    
                    # Add document type to metadata
                    doc_metadata['type'] = doc_type
                    document_metadata_list.append(doc_metadata)
                    
                except Exception as e:
                    logging.error(f"Error processing document {doc.filename}: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to process document {doc.filename}: {str(e)}"
                    )
            
            return document_metadata_list
            
        except Exception as e:
            logging.error(f"Error uploading property documents: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload documents: {str(e)}"
            )
        finally:
            # Close any open connections
            if self.azure_storage:
                await self.azure_storage.close()

    async def create_property_listing(
        self, token_payload, 
        property_type: str, 
        square_feet: float, 
        price: float, 
        area: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        images: List[UploadFile] = None,
        documents: List[UploadFile] = None,
        document_types: List[str] = None
    ):
        """
        Create a new property listing in the properties collection
        """
        db = await get_database()
        
        try:
            # Generate a unique identifier for the property
            unique_property_id = str(uuid.uuid4())
            
            # Upload images
            encrypted_image_urls = await self.upload_property_images(
                token_payload['sub'], 
                images
            )
            
            # Upload documents
            document_metadata_list = await self.upload_property_documents(
                token_payload['sub'],
                unique_property_id,
                documents,
                document_types
            ) if documents and document_types else []
            
            # Extract document hashes for blockchain verification
            document_hashes = [doc['document_hash'] for doc in document_metadata_list]
            
            # Prepare property listing data
            property_listing = {
                'id': unique_property_id,
                'seller_id': token_payload['sub'],
                'property_type': property_type,
                'square_feet': square_feet,
                'price': price,
                'area': area,
                'description': description,
                'location': location,
                'images': encrypted_image_urls,
                'documents': document_metadata_list,
                'document_hashes': document_hashes,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'status': 'LIVE'  # Default status
            }
            
            # Insert into database
            properties_collection = db['properties']
            await properties_collection.insert_one(property_listing)
            
            # Convert ObjectId to string for response
            property_listing['_id'] = str(property_listing['_id'])
            
            return property_listing
            
        except Exception as e:
            logging.error(f"Error creating property listing: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create property listing: {str(e)}"
            )

    async def update_property_listing(
        self, token_payload, property_id: str,
        property_type: Optional[str] = None,
        square_feet: Optional[float] = None,
        price: Optional[float] = None,
        area: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        images: Optional[List[UploadFile]] = None,
        documents: Optional[List[UploadFile]] = None,
        document_types: Optional[List[str]] = None
    ):
        """
        Update an existing property listing
        """
        try:
            # Find the property and validate ownership
            db = await get_database()
            properties_collection = db['properties']
            
            property_doc = await properties_collection.find_one({
                'id': property_id,
                'seller_id': token_payload['sub']
            })
            
            if not property_doc:
                raise HTTPException(status_code=404, detail="Property not found or you don't have permission")
            
            # Initialize update fields
            update_fields = {}
            
            # Handle basic property fields
            if property_type:
                update_fields['property_type'] = property_type
            if square_feet:
                update_fields['square_feet'] = square_feet
            if price:
                update_fields['price'] = price
            if area:
                update_fields['area'] = area
            if description:
                update_fields['description'] = description
            if location:
                update_fields['location'] = location
            
            # Handle images if provided
            if images and len(images) > 0:
                encrypted_image_urls = await self.upload_property_images(
                    token_payload['sub'], 
                    images
                )
                update_fields['images'] = encrypted_image_urls
            
            # Handle documents if provided
            if documents and document_types and len(documents) > 0:
                if len(documents) != len(document_types):
                    raise HTTPException(status_code=400, detail="Number of documents must match document types")
                    
                document_metadata_list = await self.upload_property_documents(
                    token_payload['sub'],
                    property_id,
                    documents,
                    document_types
                )
                update_fields['documents'] = document_metadata_list
            
            # Add timestamp
            update_fields['updated_at'] = datetime.utcnow()
            
            # Update the property
            result = await properties_collection.update_one(
                {
                    'id': property_id,
                    'seller_id': token_payload['sub']
                },
                {'$set': update_fields}
            )
            
            if result.modified_count == 0:
                raise HTTPException(status_code=500, detail="Failed to update property")
            
            # Get updated property
            updated_property = await properties_collection.find_one({
                'id': property_id,
                'seller_id': token_payload['sub']
            })
            
            # Convert MongoDB ObjectId to string
            if '_id' in updated_property:
                updated_property['_id'] = str(updated_property['_id'])
            
            return {
                "message": "Property updated successfully",
                "property": updated_property
            }
        finally:
            # Ensure we close the Azure storage client after all operations
            if hasattr(self, 'azure_storage') and self.azure_storage is not None:
                await self.azure_storage.close()

    async def delete_property_listing(self, token_payload, property_id):
        """
        Delete a specific property listing
        """
        db = await get_database()
        properties_collection = db['properties']
        
        result = await properties_collection.delete_one({
            'id': property_id,
            'seller_id': token_payload['sub']
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Property not found or you don't have permission")
        
        return {"message": "Property deleted successfully"}

    async def upload_additional_documents(
        self, 
        token_payload: dict, 
        property_id: str,
        documents: List[UploadFile],
        document_types: List[str]
    ):
        """
        Upload additional documents for an existing property
        """
        try:
            # Ensure documents and types match
            if len(documents) != len(document_types):
                raise HTTPException(
                    status_code=400, 
                    detail="Number of documents must match document types"
                )
                
            # Find the property and validate ownership
            db = await get_database()
            properties_collection = db['properties']
            
            property_doc = await properties_collection.find_one({
                'id': property_id,
                'seller_id': token_payload['sub']
            })
            
            if not property_doc:
                raise HTTPException(
                    status_code=404, 
                    detail="Property not found or you don't have permission"
                )
            
            # Upload new documents
            document_metadata_list = await self.upload_property_documents(
                token_payload['sub'],
                property_id,
                documents,
                document_types
            )
            
            # Update the property with new documents
            existing_documents = property_doc.get('documents', [])
            
            # Add new documents
            result = await properties_collection.update_one(
                {'id': property_id, 'seller_id': token_payload['sub']},
                {
                    '$set': {
                        'updated_at': datetime.utcnow()
                    },
                    '$push': {
                        'documents': {'$each': document_metadata_list}
                    }
                }
            )
            
            if result.modified_count == 0:
                raise HTTPException(
                    status_code=500, 
                    detail="Failed to update property with new documents"
                )
            
            return {
                "message": "Documents uploaded successfully",
                "added_documents": len(document_metadata_list)
            }
        finally:
            # Ensure we close the Azure storage client after all operations
            if hasattr(self, 'azure_storage') and self.azure_storage is not None:
                await self.azure_storage.close()

    async def get_seller_profile(self, token_payload: dict):
        """
        Retrieve seller profile details
        """
        try:
            db = await get_database()
            seller_collection = db['sellers']
            
            # Find seller by ID from token payload
            seller = await seller_collection.find_one(
                {'_id': ObjectId(token_payload['sub'])}, 
                {
                    'password': 0,  # Exclude password
                    'document_hashes': 0,  # Exclude any sensitive hashes
                    'properties.document_hashes': 0  # Exclude document hashes in properties
                }
            )
            
            if not seller:
                raise HTTPException(status_code=404, detail="Seller profile not found")
            
            # Convert ObjectId to string for JSON serialization
            seller['_id'] = str(seller['_id'])
            
            # Log the current selfie_url value for debugging
            logging.info(f"Original selfie_url: {seller.get('selfie_url', 'None')}")
            
            # Ensure properties have string IDs
            if 'properties' in seller:
                for prop in seller.get('properties', []):
                    if '_id' in prop:
                        prop['_id'] = str(prop['_id'])
            
            # Transform the selfie_url if it exists
            if 'selfie_url' in seller and seller['selfie_url']:
                try:
                    # Extract container and blob name from the URL
                    # This assumes the URL format: https://<account>.blob.core.windows.net/<container>/<blob>
                    url_parts = seller['selfie_url'].split('/')
                    container_name = url_parts[-2]  # Assuming container is second to last part
                    blob_name = url_parts[-1]  # Assuming blob name is the last part
                    
                    # Create proxy URL
                    seller['selfie_url'] = f"/seller/images/{container_name}/{blob_name}"
                    logging.info(f"Transformed selfie_url: {seller['selfie_url']}")
                except Exception as e:
                    logging.error(f"Failed to transform URL: {str(e)}")
                    # Keep original URL if transformation fails
            else:
                # Add a default selfie URL if not present
                seller['selfie_url'] = '/api/placeholder/50/50'
                
            return seller
                
        except Exception as e:
            logging.error(f"Failed to fetch seller profile: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch seller profile: {str(e)}"
            )
     
    async def get_image(self, container: str, image_path: str, token_payload: dict = None) -> bytes:
        """
        Get an image from Azure Storage
        
        This method verifies access permissions and retrieves the actual image content
        """
        try:
            # If token payload is provided, verify access
            if token_payload:
                has_access = await self.verify_image_access(token_payload['sub'], container, image_path)
                if not has_access:
                    raise HTTPException(status_code=403, detail="Access denied to this image")
            
            # URL decode the image path to handle any encoded characters
            decoded_image_path = urllib.parse.unquote(image_path)
            
            # Get the image content from Azure
            image_content = await self.azure_storage.download_file(container, decoded_image_path)
            return image_content
        finally:
            # Ensure we close the Azure storage client after all operations
            if hasattr(self, 'azure_storage') and self.azure_storage is not None:
                await self.azure_storage.close()

    async def verify_image_access(self, user_id: str, container_name: str, blob_name: str) -> bool:
        """Verify if the user has access to the requested image"""
        try:
            db = await get_database()
            logging.debug(f"Checking access for user_id={user_id}, container={container_name}, blob={blob_name}")
            
            if container_name == "user-selfies":
                # Check if this is the user's own selfie
                seller = await db['sellers'].find_one(
                    {'_id': ObjectId(user_id)},
                    {'selfie_url': 1}
                )
                logging.debug(f"Found seller with selfie_url: {seller.get('selfie_url') if seller else 'None'}")
                
                if seller and seller.get('selfie_url'):
                    # Case 1: The URL is already a transformed one with container info
                    if blob_name in seller['selfie_url']:
                        logging.debug(f"Direct match found for blob_name in URL")
                        return True
                    
                    # Case 2: Azure blob URL format, extract blob name
                    try:
                        url_parts = seller['selfie_url'].split('/')
                        stored_blob_name = url_parts[-1]
                        logging.debug(f"Extracted blob name from URL: {stored_blob_name}")
                        logging.debug(f"Comparing with requested blob: {blob_name}")
                        
                        # Check for exact match or if the blob name is contained in the URL
                        if stored_blob_name == blob_name:
                            return True
                    except Exception as e:
                        logging.error(f"Error parsing URL: {str(e)}")
                
                # For debugging, allow all selfie access temporarily
                logging.debug("Allowing access for debugging")
                return True
            
            elif container_name == "property-images":
                # Check if this is an image from one of the user's properties
                property = await db['properties'].find_one(
                    {'seller_id': ObjectId(user_id), 'images': {'$elemMatch': {'$regex': blob_name}}},
                    {'_id': 1}
                )
                logging.debug(f"Property found: {property is not None}")
                if property:
                    return True
                
                # For debugging, allow all property image access temporarily
                logging.debug("Allowing access for debugging")
                return True
            
            logging.debug("Access verification failed: No matching resources found")
            # Temporarily allow all access for debugging
            logging.debug("Allowing access for debugging")
            return True
        except Exception as e:
            logging.error(f"Image access verification failed: {str(e)}")
            # Temporarily allow all access for debugging
            return True
    
class DocumentAccessController:
    def __init__(self):
        self.auth_handler = AuthHandler()

    async def list_document_requests(self, token_payload):
        """
        Retrieve all document access requests for seller's properties
        """
        db = await get_database()
        document_requests_collection = db['document_requests']
        
        # Find all document requests for properties owned by this seller
        requests = await document_requests_collection.find({
            'seller_id': token_payload['sub']
        }).to_list(length=None)
        
        # Enrich requests with property and buyer information
        for request in requests:
            if '_id' in request:
                request['id'] = str(request['_id'])
                del request['_id']
                
            # Get property information
            if 'property_id' in request:
                property_doc = await db['properties'].find_one({'id': request['property_id']})
                if property_doc:
                    request['property_location'] = property_doc.get('location') or property_doc.get('area', 'Unknown location')
                    request['property_reference'] = property_doc.get('reference_number') or property_doc.get('id')
            
            # Get buyer information
            if 'buyer_id' in request:
                buyer_doc = await db['buyers'].find_one({'_id': ObjectId(request['buyer_id'])})
                if buyer_doc:
                    request['buyer_name'] = buyer_doc.get('name', 'Unknown buyer')
                    request['buyer_email'] = buyer_doc.get('email', '')
        
        return requests

    async def get_request_details(self, token_payload, request_id):
        """
        Get detailed information about a specific document request
        """
        db = await get_database()
        document_requests_collection = db['document_requests']
        
        # Find the document request
        request = await document_requests_collection.find_one({
            '_id': ObjectId(request_id),
            'seller_id': token_payload['sub']
        })
        
        if not request:
            raise HTTPException(status_code=404, detail="Document request not found")
        
        # Convert ObjectId to string
        request['id'] = str(request['_id'])
        del request['_id']
        
        # Get property information
        if 'property_id' in request:
            property_doc = await db['properties'].find_one({'id': request['property_id']})
            if property_doc:
                request['property_location'] = property_doc.get('location') or property_doc.get('area', 'Unknown location')
                request['property_reference'] = property_doc.get('reference_number') or property_doc.get('id')
                request['property_type'] = property_doc.get('property_type', 'Unknown type')
                request['property_price'] = property_doc.get('price', 0)
        
        # Get buyer information
        if 'buyer_id' in request:
            buyer_doc = await db['buyers'].find_one({'_id': ObjectId(request['buyer_id'])})
            if buyer_doc:
                request['buyer_name'] = buyer_doc.get('name', 'Unknown buyer')
                request['buyer_email'] = buyer_doc.get('email', '')
                request['buyer_phone'] = buyer_doc.get('mobile_number', '')
        
        return request

    async def handle_document_request(
        self, 
        token_payload: dict, 
        request_id: str, 
        status: str,
        rejection_reason: Optional[str] = None,
        expiry_days: Optional[int] = 7
    ):
        """
        Approve or reject a document access request
        """
        # Validate status
        if status not in ['approved', 'rejected']:
            raise HTTPException(status_code=400, detail="Invalid status. Must be 'approved' or 'rejected'")
        
        db = await get_database()
        document_requests_collection = db['document_requests']
        
        # Get the request to check it exists and belongs to this seller
        request = await document_requests_collection.find_one({
            '_id': ObjectId(request_id),
            'seller_id': token_payload['sub']
        })
        
        if not request:
            raise HTTPException(status_code=404, detail="Document request not found")
        
        # Prepare the update data
        update_data = {
            'status': status,
            'updated_at': datetime.utcnow()
        }
        
        if status == 'approved':
            # Set expiry date if approved
            update_data['approved_at'] = datetime.utcnow()
            update_data['expiry_date'] = datetime.utcnow() + timedelta(days=expiry_days)
        elif status == 'rejected':
            # Set rejection reason if rejected
            update_data['rejected_at'] = datetime.utcnow()
            update_data['rejection_reason'] = rejection_reason
        
        # Update document request status
        result = await document_requests_collection.update_one(
            {'_id': ObjectId(request_id)},
            {'$set': update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update document request")
        
        # Get the updated document request
        updated_request = await document_requests_collection.find_one({'_id': ObjectId(request_id)})
        updated_request['id'] = str(updated_request['_id'])
        del updated_request['_id']
        
        return {
            "message": f"Document request {status} successfully", 
            "request": updated_request
        }