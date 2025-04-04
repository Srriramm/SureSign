from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from typing import List, Optional
from bson import ObjectId
from datetime import datetime, timedelta
import uuid
import logging
from app.middleware.auth_middleware import AuthHandler
from app.config.db import get_database
from app.config.azure_config import AzureStorageService
from app.models.document_request import DocumentRequestCreate

class BuyerController:
    def __init__(self):
        self.auth_handler = AuthHandler()
        self.azure_storage = AzureStorageService()

    async def list_all_properties(self):
        """
        Retrieve all properties available for buyers
        """
        db = await get_database()
        properties_collection = db['properties']
        
        # Find all properties with 'LIVE' status
        properties = await properties_collection.find(
            {'status': 'LIVE'}
        ).to_list(length=None)
        
        # Convert MongoDB ObjectId to string in each property
        for property_item in properties:
            if '_id' in property_item:
                property_item['_id'] = str(property_item['_id'])
        
        return properties
        
    async def get_property_details(self, property_id):
        """
        Retrieve detailed information about a specific property
        """
        db = await get_database()
        properties_collection = db['properties']
        
        property_doc = await properties_collection.find_one({
            'id': property_id,
            'status': 'LIVE'  # Only show active properties
        })
        
        if not property_doc:
            raise HTTPException(status_code=404, detail="Property not found")
        
        # Convert MongoDB ObjectId to string
        if '_id' in property_doc:
            property_doc['_id'] = str(property_doc['_id'])
        
        # Get seller information
        if 'seller_id' in property_doc:
            seller_doc = await db['sellers'].find_one({'_id': ObjectId(property_doc['seller_id'])})
            if seller_doc:
                property_doc['seller_name'] = seller_doc.get('name', 'Unknown')
                property_doc['seller_contact'] = seller_doc.get('mobile_number', 'Unknown')
        
        return property_doc
    
    async def get_buyer_profile(self, token_payload: dict):
        """
        Retrieve the buyer's profile information
        """
        db = await get_database()
        
        # Validate that the token is for a buyer
        if token_payload.get('type') != 'buyer':
            logging.error(f"Token type mismatch: expected 'buyer', got '{token_payload.get('type')}'")
            raise HTTPException(status_code=403, detail="Access forbidden: token not for buyer")
            
        try:
            # Get buyer from database
            buyer = await db['buyers'].find_one({'_id': ObjectId(token_payload['sub'])})
            
            if not buyer:
                logging.error(f"Buyer not found for ID: {token_payload['sub']}")
                raise HTTPException(status_code=404, detail="Buyer profile not found")
            
            # Convert ObjectId to string for JSON serialization
            buyer['_id'] = str(buyer['_id'])
            
            # Remove sensitive information
            if 'password' in buyer:
                del buyer['password']
            
            return buyer
        except Exception as e:
            logging.error(f"Error in get_buyer_profile: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving buyer profile: {str(e)}")
    
    async def update_buyer_profile(self, token_payload: dict, updated_data: dict, profile_image: Optional[UploadFile] = None):
        """
        Update buyer profile information
        """
        db = await get_database()
        buyer_id = ObjectId(token_payload['sub'])
        
        # Prepare update data
        update_data = {}
        for key, value in updated_data.items():
            if value is not None and key not in ['password', '_id', 'id']:  # Exclude sensitive fields
                update_data[key] = value
        
        # Handle profile image upload if provided
        if profile_image:
            try:
                # Create Azure storage service
                container_name = "sec-user-kyc-images"
                
                # Generate unique filename for the image
                file_ext = profile_image.filename.split('.')[-1]
                new_filename = f"{uuid.uuid4().hex}.{file_ext}"
                
                # Upload to Azure
                content = await profile_image.read()
                upload_result = await self.azure_storage.upload_file(
                    container_name,
                    new_filename,
                    content
                )
                
                # Add image info to update data
                update_data.update({
                    "selfie_filename": new_filename,
                    "selfie_container": container_name,
                    "selfie_url": upload_result["direct_url"] if isinstance(upload_result, dict) else upload_result
                })
                
                # Delete old image if exists
                buyer = await db['buyers'].find_one({"_id": buyer_id})
                if buyer and buyer.get('selfie_filename'):
                    try:
                        await self.azure_storage.delete_file(
                            container_name,
                            buyer['selfie_filename']
                        )
                    except Exception as delete_error:
                        logging.error(f"Error deleting old profile image: {str(delete_error)}")
                
            except Exception as upload_error:
                logging.error(f"Error uploading profile image: {str(upload_error)}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to upload profile image"
                )
        
        # Update buyer in database
        if update_data:
            result = await db['buyers'].update_one(
                {"_id": buyer_id},
                {"$set": update_data}
            )
            
            if result.modified_count == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Buyer not found or no changes made"
                )
        
        # Get updated buyer data
        updated_buyer = await db['buyers'].find_one({"_id": buyer_id})
        if not updated_buyer:
            raise HTTPException(
                status_code=404,
                detail="Failed to retrieve updated profile"
            )
        
        # Convert ObjectId to string for response
        updated_buyer['_id'] = str(updated_buyer['_id'])
        
        # Remove sensitive fields
        updated_buyer.pop('password', None)
        
        return updated_buyer

    async def request_document_access(self, token_payload: dict, property_id: str, message: Optional[str] = None):
        """
        Request access to property documents
        """
        try:
            db = await get_database()
            properties_collection = db['properties']
            document_requests_collection = db['document_requests']
            
            # First, check if the property exists
            property_doc = await properties_collection.find_one({'id': property_id})
            if not property_doc:
                raise HTTPException(status_code=404, detail="Property not found")
            
            # Get seller ID from the property
            seller_id = property_doc.get('seller_id')
            if not seller_id:
                raise HTTPException(status_code=400, detail="Property has no seller information")
            
            # Check if buyer already has a pending or approved request
            existing_request = await document_requests_collection.find_one({
                'property_id': property_id,
                'buyer_id': token_payload['sub'],
                'status': {'$in': ['pending', 'approved']}
            })
            
            if existing_request:
                # If there's an existing request, return its status
                return {
                    "message": f"You already have a document request with status: {existing_request['status']}",
                    "request_id": str(existing_request['_id']),
                    "status": existing_request['status']
                }
            
            # Create a new document request
            new_request = {
                'property_id': property_id,
                'buyer_id': token_payload['sub'],
                'seller_id': seller_id,
                'message': message if message else "",  # Ensure message is never None
                'created_at': datetime.utcnow(),
                'status': 'pending'
            }
            
            result = await document_requests_collection.insert_one(new_request)
            
            if not result.inserted_id:
                raise HTTPException(status_code=500, detail="Failed to create document request")
            
            # Return the created request
            return {
                "message": "Document access request submitted successfully",
                "request_id": str(result.inserted_id),
                "status": "pending"
            }
            
        except Exception as e:
            logging.error(f"Error in request_document_access: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error requesting document access: {str(e)}")

    async def get_document_access(self, token_payload: dict, property_id: str):
        """
        Check if buyer has access to property documents and return them if access is granted
        """
        try:
            db = await get_database()
            document_requests_collection = db['document_requests']
            properties_collection = db['properties']
            
            # Check if the buyer has an approved request
            access_request = await document_requests_collection.find_one({
                'property_id': property_id,
                'buyer_id': token_payload['sub'],
                'status': 'approved'
            })
            
            if not access_request:
                return {
                    "has_access": False,
                    "message": "You do not have access to these documents. Please request access."
                }
            
            # Check if the access has expired (if expiry_date is set)
            if access_request.get('expiry_date') and datetime.utcnow() > access_request['expiry_date']:
                return {
                    "has_access": False,
                    "message": "Your document access has expired. Please request access again."
                }
            
            # Get the property details to get document URLs
            property_doc = await properties_collection.find_one({'id': property_id})
            if not property_doc:
                raise HTTPException(status_code=404, detail="Property not found")
            
            # Get document information and return with access URLs
            documents = property_doc.get('documents', [])
            
            return {
                "has_access": True,
                "message": "Document access granted",
                "documents": documents,
                "access_granted_on": access_request.get('updated_at', access_request.get('created_at')),
                "access_expires_on": access_request.get('expiry_date')
            }
            
        except Exception as e:
            logging.error(f"Error in get_document_access: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error getting document access: {str(e)}")

    async def list_my_document_requests(self, token_payload: dict):
        """
        List all document requests made by the buyer
        """
        try:
            db = await get_database()
            document_requests_collection = db['document_requests']
            properties_collection = db['properties']
            
            # Find all document requests made by this buyer
            requests = await document_requests_collection.find({
                'buyer_id': token_payload['sub']
            }).to_list(length=None)
            
            # Enrich requests with property information
            for request in requests:
                if '_id' in request:
                    request['id'] = str(request['_id'])
                    del request['_id']
                    
                # Get property details
                if 'property_id' in request:
                    property_doc = await properties_collection.find_one({'id': request['property_id']})
                    if property_doc:
                        request['property_location'] = property_doc.get('location') or property_doc.get('area', 'Unknown location')
                        request['property_reference'] = property_doc.get('reference_number') or property_doc.get('id')
            
            return requests
            
        except Exception as e:
            logging.error(f"Error in list_my_document_requests: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error listing document requests: {str(e)}")
