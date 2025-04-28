from fastapi import APIRouter, Depends, File, UploadFile, Form, Path, HTTPException, Response, Body, Request, Query
from typing import List, Optional, Dict
from app.controllers.buyer import BuyerController
from app.middleware.auth_middleware import AuthHandler
from app.config.db import get_database
from app.config.azure_config import AzureStorageService
import logging
from bson import ObjectId
from pydantic import BaseModel
import urllib.parse
from datetime import datetime
import json
from app.services.secure_document_service import SecureDocumentService
from app.controllers.secure_document_controller import SecureDocumentController

# Define a Pydantic model for document requests
class DocumentRequestData(BaseModel):
    message: Optional[str] = None

# Define a Pydantic model for lawyer verification
class LawyerVerificationRequest(BaseModel):
    lawyer_name: str
    lawyer_email: str
    lawyer_phone: str

# Define a Pydantic model for verification status update
class VerificationStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
    issues_details: Optional[str] = None

router = APIRouter(tags=["Buyer"])
buyer_controller = BuyerController()

@router.get("/get-buyer")
async def get_buyer_profile(token_payload = Depends(AuthHandler.auth_wrapper)):
    """
    Retrieve the logged-in buyer's profile details
    """
    try:
        if not token_payload:
            logging.error("No token payload provided")
            raise HTTPException(status_code=401, detail="Authentication required")
            
        logging.info(f"Fetching buyer profile for user ID: {token_payload.get('sub')}, type: {token_payload.get('type')}")
        return await buyer_controller.get_buyer_profile(token_payload)
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logging.error(f"Unexpected error in get_buyer_profile route: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get buyer profile: {str(e)}")

@router.put("/update-profile")
async def update_profile(
    name: str = Form(...),
    email: str = Form(...),
    mobile_number: str = Form(...),
    profile_image: Optional[UploadFile] = File(None),
    token_payload: dict = Depends(AuthHandler.auth_wrapper)
):
    """
    Update buyer profile information and optionally the profile image
    """
    # Prepare update data
    updated_data = {
        "name": name,
        "email": email,
        "mobile_number": mobile_number
    }
    
    try:
        return await buyer_controller.update_buyer_profile(token_payload, updated_data, profile_image)
    except Exception as e:
        logging.error(f"Error updating profile: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while updating profile"
        )

@router.get("/properties")
async def list_all_properties(token_payload = Depends(AuthHandler.auth_wrapper)):
    """
    List all available properties for buyers
    """
    try:
        if not token_payload:
            logging.error("No token payload provided")
            raise HTTPException(status_code=401, detail="Authentication required")
            
        logging.info(f"Fetching properties for buyer: {token_payload.get('sub')}")
        return await buyer_controller.list_all_properties()
    except Exception as e:
        logging.error(f"Error retrieving properties: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve properties: {str(e)}")

@router.get("/property/{property_id}")
async def get_property_details(property_id: str, token_payload = Depends(AuthHandler.auth_wrapper)):
    """
    Get detailed information about a specific property
    """
    try:
        if not token_payload:
            logging.error("No token payload provided")
            raise HTTPException(status_code=401, detail="Authentication required")
            
        logging.info(f"Fetching property details for property ID: {property_id}, buyer: {token_payload.get('sub')}")
        return await buyer_controller.get_property_details(property_id)
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logging.error(f"Error retrieving property details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve property details: {str(e)}")

@router.get("/image/{user_id}")
async def get_user_image(user_id: str, response: Response):
    """
    Get user image - simplified version that directly accesses the known container
    """
    azure_storage = None
    try:
        # Get the user's selfie filename from database
        db = await get_database()
        user = await db['buyers'].find_one({"_id": ObjectId(user_id)})
        
        if not user:
            user = await db['sellers'].find_one({"_id": ObjectId(user_id)})
        
        # Create Azure storage service
        azure_storage = AzureStorageService()
        container_name = "sec-user-kyc-images"  # Use the known working container
        
        # If we found the user, try to get their image
        if user:
            try:
                # Get blob client
                blob_name = user.get('selfie_filename')
                if not blob_name:
                    return Response(status_code=404)
                    
                # Get blob service client
                blob_service_client = await azure_storage.get_blob_service_client()
                
                # Get blob client
                blob_client = blob_service_client.get_blob_client(
                    container=container_name,
                    blob=blob_name
                )
                
                # Download blob
                download_stream = await blob_client.download_blob()
                content = await download_stream.readall()
                
                # Set cache headers
                response.headers["Cache-Control"] = "public, max-age=3600"
                
                # Determine content type
                content_type = "image/jpeg"
                if blob_name.lower().endswith('.png'):
                    content_type = "image/png"
                
                return Response(
                    content=content,
                    media_type=content_type
                )
            except Exception as e:
                logging.error(f"Error downloading image: {str(e)}")
                return Response(status_code=404)
                
        return Response(status_code=404)
            
    except Exception as e:
        logging.error(f"Error serving image: {str(e)}")
        return Response(status_code=404)
    finally:
        # Close Azure storage client
        if azure_storage:
            await azure_storage.close()

@router.get("/property-image/{property_id}/{image_index}")
async def get_property_image(
    property_id: str, 
    image_index: int,
    response: Response
):
    """
    Get a property image by property ID and image index
    """
    azure_storage = None
    try:
        # Get property from database
        db = await get_database()
        property_doc = await db['properties'].find_one({"id": property_id})
        
        if not property_doc or 'images' not in property_doc or len(property_doc['images']) <= image_index:
            return Response(status_code=404)
        
        # Get image data from property
        image_data = property_doc['images'][image_index]
        
        # Create Azure storage service
        azure_storage = AzureStorageService()
        
        # Get the filename from the image data
        blob_name = image_data.get('filename')
        if not blob_name:
            # Fallback to extracting from URL if filename is not available
            url = image_data.get('url', '')
            url_parts = url.split('/')
            blob_name = url_parts[-1].split('?')[0]  # Remove SAS token if present
        
        # URL decode the blob name
        blob_name = urllib.parse.unquote(blob_name)
        
        # Get the container name from Azure storage service
        container_name = azure_storage.container_property_images
        
        logging.info(f"Retrieving property image: container={container_name}, blob={blob_name}")
        
        try:
            # Get blob service client
            blob_service_client = await azure_storage.get_blob_service_client()
            
            # Get blob client
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            # Download blob
            download_stream = await blob_client.download_blob()
            content = await download_stream.readall()
            
            # Set cache headers
            response.headers["Cache-Control"] = "public, max-age=3600"
            
            # Get content type from image data or default to jpeg
            content_type = image_data.get('content_type', 'image/jpeg')
            
            return Response(
                content=content,
                media_type=content_type
            )
        except Exception as e:
            logging.error(f"Error downloading image: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to download image: {str(e)}")
            
    except Exception as e:
        logging.error(f"Error serving image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve image: {str(e)}")
    finally:
        if azure_storage:
            await azure_storage.close()

@router.post("/request-documents/{property_id}")
async def request_document_access(
    property_id: str,
    request_data: DocumentRequestData,
    token_payload: dict = Depends(AuthHandler.auth_wrapper)
):
    """
    Request access to property documents
    """
    try:
        if token_payload.get('type') != 'buyer':
            raise HTTPException(status_code=403, detail="Only buyers can request document access")
            
        return await buyer_controller.request_document_access(token_payload, property_id, request_data.message)
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error requesting document access: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to request document access: {str(e)}")

@router.get("/document-access/{property_id}")
async def get_document_access(
    property_id: str,
    token_payload: dict = Depends(AuthHandler.auth_wrapper)
):
    """
    Check if buyer has access to property documents and get the documents if access is granted
    """
    try:
        if token_payload.get('type') != 'buyer':
            raise HTTPException(status_code=403, detail="Only buyers can access documents")
            
        return await buyer_controller.get_document_access(token_payload, property_id)
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error getting document access: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get document access: {str(e)}")

@router.get("/my-document-requests")
async def list_my_document_requests(
    token_payload: dict = Depends(AuthHandler.auth_wrapper)
):
    """
    List all document requests made by the buyer
    """
    try:
        if token_payload.get('type') != 'buyer':
            raise HTTPException(status_code=403, detail="Only buyers can access their document requests")
            
        return await buyer_controller.list_my_document_requests(token_payload)
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error listing document requests: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list document requests: {str(e)}")

@router.get("/property-document/{property_id}/{document_index}")
async def get_property_document(
    property_id: str = Path(..., description="ID of the property"),
    document_index: int = Path(..., description="Index of the document in the property's documents array"),
    token: str = Query(..., description="JWT token for authentication"),
    request: Request = None,
    db=Depends(get_database)
):
    """
    Get a property document with decryption and watermarking for buyers
    """
    azure_storage = None
    
    try:
        # Verify token and get buyer info
        try:
            buyer = AuthHandler.decode_token(token)
            if not buyer or buyer.get('type') != 'buyer':
                raise HTTPException(status_code=401, detail="Invalid or expired token")
        except Exception as e:
            logging.error(f"Token verification failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
            
        # Get property from database using the property_id directly
        property_data = await db.properties.find_one({"id": property_id})
        if not property_data:
            raise HTTPException(status_code=404, detail="Property not found")
            
        # Check if document exists
        if not property_data.get('documents') or document_index >= len(property_data['documents']):
            raise HTTPException(status_code=404, detail="Document not found")
            
        property_doc = property_data['documents'][document_index]
        logging.info(f"Retrieved property document info: {json.dumps(property_doc, default=str)}")
        
        # Initialize Azure storage
        azure_storage = AzureStorageService()
        
        # Get the encrypted document URL and document ID
        encrypted_url = property_doc.get('encrypted_url')
        document_id = property_doc.get('document_id')
        
        if not encrypted_url or not document_id:
            raise HTTPException(status_code=404, detail="Encrypted document information not found")
        
        # Initialize the secure document service for decryption
        secure_doc_service = SecureDocumentService(azure_storage)
        
        try:
            # Use SecureDocumentService to retrieve and decrypt the document
            logging.info(f"Using SecureDocumentService to retrieve document: {document_id}")
            
            # First get the decrypted document
            document_content = await secure_doc_service.retrieve_document(
                document_id=document_id,
                owner_id=property_data['seller_id'],
                property_id=property_id
            )
            
            if not document_content or len(document_content) == 0:
                logging.error(f"Empty document content received")
                raise HTTPException(status_code=500, detail="Document content is empty")
            
            # Get document name from metadata
            document_name = property_doc.get('document_name', f"document_{document_index}")
            
            # Ensure filename has extension
            if '.' not in document_name:
                content_type = property_doc.get('content_type', 'application/octet-stream')
                if content_type == 'application/pdf':
                    document_name += '.pdf'
                elif content_type == 'image/jpeg':
                    document_name += '.jpg'
                elif content_type == 'image/png':
                    document_name += '.png'
                else:
                    document_name += '.bin'
            
            # Determine content type based on file extension
            content_type = property_doc.get('content_type', 'application/octet-stream')
            if not content_type or content_type == 'application/octet-stream':
                if document_name.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif document_name.lower().endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif document_name.lower().endswith('.png'):
                    content_type = 'image/png'
                else:
                    content_type = 'application/octet-stream'
            
            logging.info(f"Document content type: {content_type}, size: {len(document_content)} bytes")
            
            # For PDF files, check if they start with the PDF signature
            if content_type == 'application/pdf' and not document_content.startswith(b'%PDF'):
                # Try to find PDF signature
                pdf_start = document_content.find(b'%PDF')
                if pdf_start > 0:
                    logging.warning(f"PDF document corrupt, repairing by removing {pdf_start} bytes from start")
                    document_content = document_content[pdf_start:]
            
            # Now apply security features with SecureDocumentController
            from app.controllers.document_access import secure_document_controller
            
            # Apply watermark and other security features to the document
            try:
                document_type = property_doc.get('type', 'unknown')
                secured_content, metadata = await secure_document_controller.get_secure_document(
                    content=document_content,
                    content_type=content_type,
                    buyer_id=buyer['sub'],
                    property_id=property_id,
                    document_index=document_index,
                    document_type=document_type,
                    request=request
                )
                
                # Use the watermarked content if successful
                if secured_content and len(secured_content) > 0:
                    logging.info(f"Successfully applied security features: {metadata}")
                    document_content = secured_content
                else:
                    logging.warning("Failed to apply security features, using original content")
            except Exception as sec_error:
                logging.error(f"Error applying security features: {str(sec_error)}")
                # Continue with original content if security application fails
            
            # Return the document with appropriate headers
            response = Response(
                content=document_content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f"attachment; filename=\"{document_name}\"",
                    "Content-Type": content_type,
                    "Content-Length": str(len(document_content)),
                    "Cache-Control": "no-cache"
                }
            )
            
            logging.info(f"Successfully prepared document response: {document_name}")
            return response
            
        except Exception as e:
            logging.error(f"Error retrieving document: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving document: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in get_property_document: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if azure_storage:
            await azure_storage.close()

@router.post("/property/{property_id}/verify-with-lawyer")
async def add_lawyer_for_verification(
    property_id: str = Path(..., description="ID of the property to verify"),
    data: LawyerVerificationRequest = Body(...),
    token_payload: dict = Depends(AuthHandler.auth_wrapper)
):
    """
    Add a lawyer to verify property documents
    """
    try:
        if token_payload.get('type') != 'buyer':
            raise HTTPException(status_code=403, detail="Only buyers can add lawyers for verification")
            
        return await buyer_controller.add_lawyer_for_verification(
            token_payload=token_payload,
            property_id=property_id,
            lawyer_name=data.lawyer_name,
            lawyer_email=data.lawyer_email,
            lawyer_phone=data.lawyer_phone
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error adding lawyer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add lawyer: {str(e)}")

@router.get("/property/{property_id}/lawyer-verification")
async def get_lawyer_verification(
    property_id: str = Path(..., description="ID of the property"),
    token_payload: dict = Depends(AuthHandler.auth_wrapper)
):
    """
    Get the status of lawyer verification for a property
    """
    try:
        if token_payload.get('type') != 'buyer':
            raise HTTPException(status_code=403, detail="Only buyers can check verification status")
            
        return await buyer_controller.get_lawyer_verification_status(token_payload, property_id)
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error getting lawyer verification: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get lawyer verification: {str(e)}")

# Routes for lawyers to access and verify documents
@router.get("/lawyer/verification/{property_id}")
async def get_lawyer_verification_details(
    property_id: str = Path(..., description="ID of the property"),
    token: str = Query(..., description="Verification token sent to lawyer")
):
    """
    Get property and verification details for a lawyer using their token
    """
    try:
        return await buyer_controller.get_lawyer_verification_by_token(property_id, token)
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error getting verification details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get verification details: {str(e)}")

@router.post("/lawyer/verification/{property_id}")
async def update_lawyer_verification(
    property_id: str = Path(..., description="ID of the property"),
    token: str = Query(..., description="Verification token sent to lawyer"),
    data: VerificationStatusUpdate = Body(...)
):
    """
    Update verification status by lawyer
    """
    try:
        return await buyer_controller.update_lawyer_verification(
            property_id=property_id,
            token=token,
            status=data.status,
            notes=data.notes,
            issues_details=data.issues_details
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error updating verification: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update verification: {str(e)}")

@router.get("/lawyer/property-document/{property_id}/{document_index}")
async def get_property_document_for_lawyer(
    property_id: str = Path(..., description="ID of the property"),
    document_index: int = Path(..., description="Index of the document in the property's documents array"),
    token: str = Query(..., description="Lawyer verification token"),
    request: Request = None,
    db=Depends(get_database)
):
    """
    Allow a lawyer to download a property document using their verification token
    """
    azure_storage = None
    
    try:
        # Track lawyer document access first
        await buyer_controller.track_lawyer_document_access(property_id, token, document_index)
        
        # Get verification record to ensure token is valid
        verification_result = await buyer_controller.get_lawyer_verification_by_token(property_id, token)
        buyer_id = verification_result.get("verification", {}).get("buyer_id")
        
        if not buyer_id:
            raise HTTPException(status_code=401, detail="Invalid verification token")
        
        # Get property from database using the property_id
        property_data = await db.properties.find_one({"id": property_id})
        if not property_data:
            raise HTTPException(status_code=404, detail="Property not found")
            
        # Check if document exists
        if not property_data.get('documents') or document_index >= len(property_data['documents']):
            raise HTTPException(status_code=404, detail="Document not found")
            
        property_doc = property_data['documents'][document_index]
        logging.info(f"Retrieved property document info for lawyer: {json.dumps(property_doc, default=str)}")
        
        # Initialize Azure storage
        azure_storage = AzureStorageService()
        
        # Get the encrypted document URL and document ID
        encrypted_url = property_doc.get('encrypted_url')
        document_id = property_doc.get('document_id')
        
        if not encrypted_url or not document_id:
            raise HTTPException(status_code=404, detail="Encrypted document information not found")
        
        # Initialize the secure document service for decryption
        secure_doc_service = SecureDocumentService(azure_storage)
        
        try:
            # Use SecureDocumentService to retrieve and decrypt the document
            logging.info(f"Using SecureDocumentService to retrieve document for lawyer: {document_id}")
            
            # First get the decrypted document
            document_content = await secure_doc_service.retrieve_document(
                document_id=document_id,
                owner_id=property_data['seller_id'],
                property_id=property_id
            )
            
            if not document_content or len(document_content) == 0:
                logging.error(f"Empty document content received")
                raise HTTPException(status_code=500, detail="Document content is empty")
            
            # Get document name from metadata
            document_name = property_doc.get('document_name', f"document_{document_index}")
            
            # Ensure filename has extension
            if '.' not in document_name:
                content_type = property_doc.get('content_type', 'application/octet-stream')
                if content_type == 'application/pdf':
                    document_name += '.pdf'
                elif content_type == 'image/jpeg':
                    document_name += '.jpg'
                elif content_type == 'image/png':
                    document_name += '.png'
                else:
                    document_name += '.bin'
            
            # Determine content type based on file extension
            content_type = property_doc.get('content_type', 'application/octet-stream')
            if not content_type or content_type == 'application/octet-stream':
                if document_name.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif document_name.lower().endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif document_name.lower().endswith('.png'):
                    content_type = 'image/png'
                else:
                    content_type = 'application/octet-stream'
            
            logging.info(f"Document content type for lawyer: {content_type}, size: {len(document_content)} bytes")
            
            # For PDF files, check if they start with the PDF signature
            if content_type == 'application/pdf' and not document_content.startswith(b'%PDF'):
                # Try to find PDF signature
                pdf_start = document_content.find(b'%PDF')
                if pdf_start > 0:
                    logging.warning(f"PDF document corrupt, repairing by removing {pdf_start} bytes from start")
                    document_content = document_content[pdf_start:]
            
            # Apply watermark for lawyers similar to buyers
            from app.controllers.document_access import secure_document_controller
            
            try:
                document_type = property_doc.get('type', 'unknown')
                
                # Make sure we use the correct content type for watermarking
                if document_name.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                
                secured_content, metadata = await secure_document_controller.get_secure_document(
                    content=document_content,
                    content_type=content_type,
                    buyer_id=buyer_id,  # Use buyer's ID for tracking
                    property_id=property_id,
                    document_index=document_index,
                    document_type=document_type,
                    request=request
                )
                
                # Use the watermarked content if successful
                if secured_content and len(secured_content) > 0:
                    logging.info(f"Successfully applied security features for lawyer: {metadata}")
                    document_content = secured_content
                else:
                    logging.warning("Failed to apply security features for lawyer, using original content")
            except Exception as sec_error:
                logging.error(f"Error applying security features for lawyer: {str(sec_error)}")
                # Continue with original content if security application fails
            
            # Add "LAWYER COPY" to the filename
            lawyer_document_name = f"LAWYER_COPY_{document_name}"
            
            # Return the document with appropriate headers
            response = Response(
                content=document_content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f"attachment; filename=\"{lawyer_document_name}\"",
                    "Content-Type": content_type,
                    "Content-Length": str(len(document_content)),
                    "Cache-Control": "no-cache"
                }
            )
            
            logging.info(f"Successfully prepared document response for lawyer: {lawyer_document_name}")
            return response
            
        except Exception as e:
            logging.error(f"Error retrieving document for lawyer: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving document: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in get_property_document_for_lawyer: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if azure_storage:
            await azure_storage.close()
