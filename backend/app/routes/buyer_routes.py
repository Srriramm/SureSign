from fastapi import APIRouter, Depends, File, UploadFile, Form, Path, HTTPException, Response, Body, Request
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

# Define a Pydantic model for document requests
class DocumentRequestData(BaseModel):
    message: Optional[str] = None

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
async def get_buyer_property_document(
    property_id: str, 
    document_index: int, 
    response: Response,
    token: Optional[str] = None,
    request: Request = None,
    current_user: Optional[dict] = Depends(AuthHandler.auth_wrapper_optional)
):
    """
    Get a specific property document by property ID and document index for buyers with access
    """
    azure_storage = None
    
    try:
        # If no user from auth header, try token from query param
        if not current_user and token:
            try:
                current_user = AuthHandler.decode_token(token)
                logging.info(f"Using token from query parameter")
            except Exception as e:
                logging.error(f"Invalid token in query parameter: {str(e)}")
                raise HTTPException(status_code=401, detail="Invalid token")
        
        # If still no user, authentication failed
        if not current_user:
            logging.error("No valid authentication provided")
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if current_user.get('type') != 'buyer':
            logging.error(f"Access denied: User type is {current_user.get('type')}, expected 'buyer'")
            raise HTTPException(status_code=403, detail="Only buyers can access documents")
            
        logging.info(f"Buyer {current_user['sub']} requesting document {document_index} for property {property_id}")
            
        # Check if the buyer has access
        db = await get_database()
        document_requests_collection = db['document_requests']
        
        # Check if the buyer has an approved request
        access_request = await document_requests_collection.find_one({
            'property_id': property_id,
            'buyer_id': current_user['sub'],
            'status': 'approved'
        })
        
        if not access_request:
            logging.error(f"Access denied: Buyer {current_user['sub']} has no approved request for property {property_id}")
            raise HTTPException(status_code=403, detail="You do not have access to this document")
        
        # Check if the access has expired (if expiry_date is set)
        if access_request.get('expiry_date') and datetime.utcnow() > access_request['expiry_date']:
            logging.error(f"Access denied: Buyer's access has expired for property {property_id}")
            raise HTTPException(status_code=403, detail="Your document access has expired")
        
        # Get the property details to get document URLs
        properties_collection = db['properties']
        property_doc = await properties_collection.find_one({'id': property_id})
        if not property_doc:
            logging.error(f"Property {property_id} not found")
            raise HTTPException(status_code=404, detail="Property not found")
        
        # Check if the document exists
        if not property_doc.get('documents') or len(property_doc['documents']) <= document_index:
            logging.error(f"Document index {document_index} not found for property {property_id}")
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get the document data
        document_data = property_doc['documents'][document_index]
        logging.info(f"Document data type: {type(document_data)}")
        
        # Create Azure storage service
        azure_storage = AzureStorageService()
        
        # Get document URL - handle both string and dictionary formats
        document_url = None
        if isinstance(document_data, str):
            document_url = document_data
            logging.info(f"Document URL is a direct string: {document_url}")
        elif isinstance(document_data, dict) and 'url' in document_data:
            document_url = document_data.get('url')
            logging.info(f"Document URL extracted from dictionary: {document_url}")
        else:
            logging.error(f"Unexpected document_data format: {type(document_data)}")
            raise HTTPException(status_code=404, detail="Document URL not found")
            
        if not document_url:
            logging.error(f"Document URL is empty")
            raise HTTPException(status_code=404, detail="Document URL not found")
            
        # Extract container and blob
        container_name = azure_storage.container_property_docs
        
        # Extract blob name from URL
        url_parts = document_url.split('/')
        blob_name = url_parts[-1].split('?')[0]  # Remove SAS token
        
        if not blob_name:
            logging.error(f"No valid blob name found for property {property_id}, document index {document_index}")
            raise HTTPException(status_code=404, detail="Document blob not found")
        
        # URL decode the blob name
        blob_name = urllib.parse.unquote(blob_name)
        
        logging.info(f"Buyer retrieving property document: container={container_name}, blob={blob_name}")
        
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
        
        # Get filename from document data or use blob name
        filename = None
        if isinstance(document_data, dict):
            filename = document_data.get('filename', blob_name)
        else:
            filename = blob_name
            
        # Determine content type based on file extension
        content_type = "application/octet-stream"  # Default
        is_word_doc = False
        
        if blob_name.lower().endswith('.pdf'):
            content_type = "application/pdf"
        elif blob_name.lower().endswith('.doc'):
            content_type = "application/msword"
            is_word_doc = True
        elif blob_name.lower().endswith('.docx'):
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            is_word_doc = True
        
        # Special handling for Word documents
        if is_word_doc:
            # Force binary output for Word documents
            response.headers["Content-Transfer-Encoding"] = "binary"
            # Prevent content sniffing
            response.headers["X-Content-Type-Options"] = "nosniff"
            # No caching for documents
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        else:
            # Set cache headers for non-Word documents
            response.headers["Cache-Control"] = "public, max-age=3600"
        
        # Ensure the filename is properly set
        clean_filename = filename.split('/')[-1]  # Remove any path components
        # Remove any special characters that might cause issues
        clean_filename = ''.join(c for c in clean_filename if c.isalnum() or c in '._- ')
        
        # Log what we're sending back
        logging.info(f"Serving document with content type: {content_type}, filename: {clean_filename}")
        
        # Set the Content-Disposition header to force download
        response.headers["Content-Disposition"] = f'attachment; filename="{clean_filename}"'
        
        return Response(
            content=content,
            media_type=content_type
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error serving property document to buyer: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document: {str(e)}")
    finally:
        if azure_storage:
            await azure_storage.close()
