from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from typing import List, Optional
from bson import ObjectId
from datetime import datetime, timedelta
import uuid
import logging
import secrets
from app.middleware.auth_middleware import AuthHandler
from app.config.db import get_database
from app.config.azure_config import AzureStorageService
from app.models.document_request import DocumentRequestCreate
from app.models.document_access import LawyerVerification
from app.utils.email_service import send_lawyer_verification_email

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
            access_limits_collection = db['document_access_limits']
            
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
            
            # Get document download limits for each document
            document_limits = []
            for i in range(len(documents)):
                # Find access limit record for this buyer and document
                limit_record = await access_limits_collection.find_one({
                    'buyer_id': token_payload['sub'],
                    'property_id': property_id,
                    'document_index': i
                })
                
                if limit_record:
                    # Calculate remaining downloads
                    max_downloads = limit_record.get('max_downloads', 3)
                    current_count = limit_record.get('download_count', 0)
                    remaining = max(0, max_downloads - current_count)
                    
                    document_limits.append({
                        'document_index': i,
                        'max_downloads': max_downloads,
                        'download_count': current_count,
                        'remaining_downloads': remaining
                    })
                else:
                    # No record yet, so all downloads remaining
                    document_limits.append({
                        'document_index': i,
                        'max_downloads': 3,
                        'download_count': 0,
                        'remaining_downloads': 3
                    })
            
            return {
                "has_access": True,
                "message": "Document access granted",
                "documents": documents,
                "document_limits": document_limits,
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

    async def add_lawyer_for_verification(
        self, 
        token_payload: dict, 
        property_id: str, 
        lawyer_name: str, 
        lawyer_email: str, 
        lawyer_phone: str
    ):
        """
        Add a lawyer for property document verification
        """
        try:
            db = await get_database()
            properties_collection = db['properties']
            lawyer_verification_collection = db['lawyer_verifications']
            
            # First, check if the property exists
            property_doc = await properties_collection.find_one({'id': property_id})
            if not property_doc:
                raise HTTPException(status_code=404, detail="Property not found")
            
            # Check if the buyer already has an active lawyer for this property
            existing_verification = await lawyer_verification_collection.find_one({
                'property_id': property_id,
                'buyer_id': token_payload['sub'],
                'is_active': True
            })
            
            # If there's an existing verification, deactivate it
            if existing_verification:
                await lawyer_verification_collection.update_one(
                    {'_id': existing_verification['_id']},
                    {'$set': {'is_active': False}}
                )
            
            # Generate a secure access token for the lawyer
            access_token = secrets.token_urlsafe(32)
            token_expiry = datetime.utcnow() + timedelta(days=7)  # Token valid for 7 days
            
            # Create new lawyer verification record
            new_verification = LawyerVerification(
                property_id=property_id,
                buyer_id=token_payload['sub'],
                lawyer_name=lawyer_name,
                lawyer_email=lawyer_email,
                lawyer_phone=lawyer_phone,
                access_token=access_token,
                token_expiry=token_expiry,
                created_at=datetime.utcnow()
            ).dict()
            
            result = await lawyer_verification_collection.insert_one(new_verification)
            
            if not result.inserted_id:
                raise HTTPException(status_code=500, detail="Failed to create lawyer verification record")
            
            # Get buyer information for the email
            buyer = await db['buyers'].find_one({'_id': ObjectId(token_payload['sub'])})
            if not buyer:
                raise HTTPException(status_code=404, detail="Buyer not found")
            
            # Get property information for the email
            property_info = {
                'id': property_doc['id'],
                'address': property_doc.get('address', 'Unknown address'),
                'survey_number': property_doc.get('survey_number', 'Unknown'),
                'plot_size': property_doc.get('plot_size', 'Unknown')
            }
            
            # Send email to lawyer
            verification_url = f"http://localhost:3000/lawyer/verify/{property_id}?token={access_token}"
            try:
                # Try to send email
                await send_lawyer_verification_email(
                    lawyer_email=lawyer_email,
                    lawyer_name=lawyer_name,
                    buyer_name=buyer.get('name', 'Unknown Buyer'),
                    property_info=property_info,
                    verification_url=verification_url,
                    expiry_date=token_expiry
                )
                email_sent = True
            except Exception as e:
                logging.error(f"Failed to send email to lawyer: {str(e)}")
                email_sent = False
            
            # Return the created verification record
            new_verification['_id'] = str(result.inserted_id)
            return {
                "message": "Lawyer added for verification successfully",
                "email_sent": email_sent,
                "lawyer_verification": new_verification,
                "verification_url": verification_url
            }
            
        except Exception as e:
            logging.error(f"Error in add_lawyer_for_verification: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error adding lawyer: {str(e)}")

    async def get_lawyer_verification_status(self, token_payload: dict, property_id: str):
        """
        Get the status of lawyer verification for a property
        """
        try:
            db = await get_database()
            lawyer_verification_collection = db['lawyer_verifications']
            
            # Find the active lawyer verification for this property and buyer
            verification = await lawyer_verification_collection.find_one({
                'property_id': property_id,
                'buyer_id': token_payload['sub'],
                'is_active': True
            })
            
            if not verification:
                return {
                    "has_verification": False,
                    "message": "No active lawyer verification found for this property"
                }
            
            # Serialize the verification record
            serialized_verification = self._serialize_document(verification)
            
            # Check if the verification token has expired
            is_expired = verification.get('token_expiry') and datetime.utcnow() > verification['token_expiry']
            
            return {
                "has_verification": True,
                "verification": serialized_verification,
                "is_expired": is_expired
            }
            
        except Exception as e:
            logging.error(f"Error in get_lawyer_verification_status: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error getting lawyer verification: {str(e)}")
            
    async def get_lawyer_verification_by_token(self, property_id: str, token: str):
        """
        Get lawyer verification by token - used by lawyers to access and verify documents
        """
        try:
            db = await get_database()
            lawyer_verification_collection = db['lawyer_verifications']
            properties_collection = db['properties']
            
            # Find the lawyer verification by token
            verification = await lawyer_verification_collection.find_one({
                'property_id': property_id,
                'access_token': token,
                'is_active': True
            })
            
            if not verification:
                raise HTTPException(status_code=404, detail="Verification not found or inactive")
            
            # Check if token has expired
            if verification.get('token_expiry') and datetime.utcnow() > verification['token_expiry']:
                raise HTTPException(status_code=401, detail="Verification token has expired")
            
            # Get the property details
            property_doc = await properties_collection.find_one({'id': property_id})
            if not property_doc:
                raise HTTPException(status_code=404, detail="Property not found")
            
            # Get buyer information
            buyer = await db['buyers'].find_one({'_id': ObjectId(verification['buyer_id'])})
            buyer_name = buyer.get('name', 'Unknown Buyer') if buyer else 'Unknown Buyer'
            
            # Convert all ObjectId instances to strings in the verification object
            serialized_verification = self._serialize_document(verification)
            
            # Convert ObjectIds in property_doc
            serialized_property = self._serialize_document(property_doc)
            
            return {
                "verification": serialized_verification,
                "property": serialized_property,
                "buyer_name": buyer_name
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Error in get_lawyer_verification_by_token: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving verification: {str(e)}")
            
    def _serialize_document(self, doc):
        """Helper method to convert MongoDB document with ObjectId to serializable dict"""
        if doc is None:
            return None
            
        serialized_doc = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                serialized_doc[k] = str(v)
            elif isinstance(v, list):
                serialized_doc[k] = [
                    self._serialize_document(item) if isinstance(item, dict) else 
                    str(item) if isinstance(item, ObjectId) else item 
                    for item in v
                ]
            elif isinstance(v, dict):
                serialized_doc[k] = self._serialize_document(v)
            elif isinstance(v, datetime):
                serialized_doc[k] = v.isoformat()
            else:
                serialized_doc[k] = v
                
        return serialized_doc
    
    async def update_lawyer_verification(self, property_id: str, token: str, status: str, notes: Optional[str] = None, issues_details: Optional[str] = None):
        """
        Update the verification status by the lawyer
        """
        try:
            db = await get_database()
            lawyer_verification_collection = db['lawyer_verifications']
            
            # Find the verification record
            verification = await lawyer_verification_collection.find_one({
                'property_id': property_id,
                'access_token': token,
                'is_active': True
            })
            
            if not verification:
                raise HTTPException(status_code=404, detail="Verification not found or inactive")
            
            # Check if token has expired
            if verification.get('token_expiry') and datetime.utcnow() > verification['token_expiry']:
                raise HTTPException(status_code=401, detail="Verification token has expired")
            
            # Validate status
            if status not in ["verified", "issues_found", "pending"]:
                raise HTTPException(status_code=400, detail="Invalid status. Must be 'verified', 'issues_found', or 'pending'")
            
            # Update verification
            update_data = {
                'verification_status': status,
                'updated_at': datetime.utcnow()
            }
            
            if notes:
                update_data['verification_notes'] = notes
                
            if issues_details and status == "issues_found":
                update_data['issues_details'] = issues_details
            
            # Update the record
            result = await lawyer_verification_collection.update_one(
                {'_id': verification['_id']},
                {'$set': update_data}
            )
            
            if result.modified_count == 0:
                raise HTTPException(status_code=500, detail="Failed to update verification")
            
            # Get the updated verification
            updated_verification = await lawyer_verification_collection.find_one({'_id': verification['_id']})
            
            # Serialize the updated verification
            serialized_verification = self._serialize_document(updated_verification)
            
            return {
                "message": f"Verification status updated to '{status}'",
                "verification": serialized_verification
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Error in update_lawyer_verification: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error updating verification: {str(e)}")
            
    async def track_lawyer_document_access(self, property_id: str, token: str, document_index: int):
        """
        Track lawyer's document access to limit downloads
        """
        try:
            db = await get_database()
            lawyer_verification_collection = db['lawyer_verifications']
            
            # Find the verification record
            verification = await lawyer_verification_collection.find_one({
                'property_id': property_id,
                'access_token': token,
                'is_active': True
            })
            
            if not verification:
                raise HTTPException(status_code=404, detail="Verification not found or inactive")
            
            # Check if token has expired
            if verification.get('token_expiry') and datetime.utcnow() > verification['token_expiry']:
                raise HTTPException(status_code=401, detail="Verification token has expired")
            
            # Add document index to accessed documents if not already there
            documents_accessed = verification.get('documents_accessed', [])
            if document_index not in documents_accessed:
                documents_accessed.append(document_index)
                
                # Update the record
                await lawyer_verification_collection.update_one(
                    {'_id': verification['_id']},
                    {'$set': {'documents_accessed': documents_accessed}}
                )
            
            # Return success
            return {
                "message": "Document access tracked successfully",
                "document_index": document_index
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Error in track_lawyer_document_access: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error tracking document access: {str(e)}")
