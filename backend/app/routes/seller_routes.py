from fastapi import APIRouter, Depends, File, UploadFile, Form, Path, Body, Request
from typing import List, Optional
from bson import ObjectId
from app.config.azure_config import AzureStorageService
from app.controllers.seller import PropertyListingController, DocumentAccessController
from app.controllers.auth import AuthController
from app.middleware.auth_middleware import AuthHandler
from app.models.property import PropertyModel
from app.config.db import get_database
import logging
from fastapi import HTTPException, Response
from fastapi.responses import StreamingResponse
from azure.core.exceptions import AzureError
from PIL import Image, ImageDraw
import os
import uuid
import datetime
import base64
import urllib.parse

router = APIRouter(tags=["Seller"])
property_controller = PropertyListingController()
document_access_controller = DocumentAccessController()

@router.put("/update-profile")
async def update_profile(
    name: str = Form(...),
    email: str = Form(...),
    mobile_number: str = Form(...),
    profile_image: Optional[UploadFile] = File(None),
    token_payload: dict = Depends(AuthHandler.auth_wrapper)
):
    """
    Update seller profile information and optionally the profile image
    """
    azure_storage = None
    try:
        db = await get_database()
        seller_id = ObjectId(token_payload['sub'])
        
        # Prepare update data
        update_data = {
            "name": name,
            "email": email,
            "mobile_number": mobile_number
        }
        
        # Handle profile image upload if provided
        if profile_image:
            try:
                # Create Azure storage service
                azure_storage = AzureStorageService()
                container_name = "sec-user-kyc-images"
                
                # Generate unique filename for the image
                file_ext = profile_image.filename.split('.')[-1]
                new_filename = f"{uuid.uuid4().hex}.{file_ext}"
                
                # Upload to Azure
                content = await profile_image.read()
                blob_url = await azure_storage.upload_file(
                    container_name,
                    new_filename,
                    content
                )
                
                # Add image info to update data
                update_data.update({
                    "selfie_filename": new_filename,
                    "selfie_container": container_name,
                    "selfie_url": blob_url
                })
                
                # Delete old image if exists
                seller = await db['sellers'].find_one({"_id": seller_id})
                if seller and seller.get('selfie_filename'):
                    try:
                        await azure_storage.delete_file(
                            container_name,
                            seller['selfie_filename']
                        )
                    except Exception as delete_error:
                        logging.error(f"Error deleting old profile image: {str(delete_error)}")
                
            except Exception as upload_error:
                logging.error(f"Error uploading profile image: {str(upload_error)}")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to upload profile image"
                )
        
        # Update seller in database
        result = await db['sellers'].update_one(
            {"_id": seller_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Seller not found or no changes made"
            )
        
        # Get updated seller data
        updated_seller = await db['sellers'].find_one({"_id": seller_id})
        if not updated_seller:
            raise HTTPException(
                status_code=404,
                detail="Failed to retrieve updated profile"
            )
        
        # Convert ObjectId to string for response
        updated_seller['_id'] = str(updated_seller['_id'])
        
        # Remove sensitive fields
        updated_seller.pop('password_hash', None)
        updated_seller.pop('document_hash', None)
        
        return updated_seller
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error updating profile: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while updating profile"
        )
    finally:
        # Close Azure storage client
        if azure_storage:
            await azure_storage.close()

@router.get("/get-seller")
async def get_seller_profile(token_payload = Depends(AuthHandler.auth_wrapper)):
    """
    Retrieve the logged-in seller's profile details
    """
    return await property_controller.get_seller_profile(token_payload)

@router.get("/image/{user_id}")
async def get_user_image(user_id: str, response: Response):
    """
    Get user image - simplified version that directly accesses the known container
    """
    azure_storage = None
    try:
        # Get the user's selfie filename from database
        db = await get_database()
        user = await db['sellers'].find_one({"_id": ObjectId(user_id)})
        
        if not user:
            user = await db['buyers'].find_one({"_id": ObjectId(user_id)})
        
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

@router.get("/properties")
async def list_properties(token_payload = Depends(AuthHandler.auth_wrapper)):
    """
    Get all properties listed by the seller
    """
    return await property_controller.list_seller_properties(token_payload)

@router.post("/property")
async def create_property_listing(
    property_type: str = Form(...),
    square_feet: float = Form(...),
    price: float = Form(...),
    area: str = Form(...),
    description: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    images: List[UploadFile] = File(...),
    documents: List[UploadFile] = File(...),
    document_types: List[str] = Form(...),
    token_payload = Depends(AuthHandler.auth_wrapper)
):
    """
    Create a new property listing
    """
    return await property_controller.create_property_listing(
        token_payload, 
        property_type=property_type,
        square_feet=square_feet,
        price=price,
        area=area,
        description=description,
        location=location,
        images=images, 
        documents=documents,
        document_types=document_types
    )


@router.get("/property-document/{property_id}/{document_index}")
async def get_property_document(property_id: str, document_index: int, response: Response, token_payload = Depends(AuthHandler.auth_wrapper)):
    """
    Get a specific property document by property ID and document index
    """
    azure_storage = None
    
    try:
        # Get the property details
        db = await get_database()
        seller_id = token_payload['sub']
        
        # Find the property in the properties collection
        property_doc = await db['properties'].find_one({
            'id': property_id,
            'seller_id': seller_id
        })
        
        if not property_doc or not property_doc.get('documents') or len(property_doc['documents']) <= document_index:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get the document data
        document_data = property_doc['documents'][document_index]
        
        # Create Azure storage service
        azure_storage = AzureStorageService()
        
        # Get document URL - handle both string and dictionary formats for backward compatibility
        document_url = document_data['url'] if isinstance(document_data, dict) else document_data
        
        # If document_data is a string, it's the URL directly
        if isinstance(document_data, str):
            document_url = document_data
            logging.info(f"Document URL is a direct string: {document_url}")
        # If it's a dict, extract the URL
        elif isinstance(document_data, dict) and 'url' in document_data:
            document_url = document_data.get('url')
            logging.info(f"Document URL extracted from dictionary: {document_url}")
        else:
            # Log the actual document_data for debugging
            logging.error(f"Unexpected document_data format: {type(document_data)}, value: {document_data}")
            raise HTTPException(status_code=404, detail="Document URL not found")
            
        if not document_url:
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
        
        logging.info(f"Retrieving property document: container={container_name}, blob={blob_name}")
        
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
        
        # Determine content type based on file extension
        content_type = "application/octet-stream"  # Default
        if blob_name.lower().endswith('.pdf'):
            content_type = "application/pdf"
        elif blob_name.lower().endswith('.doc'):
            content_type = "application/msword"
        elif blob_name.lower().endswith('.docx'):
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        
        # Set additional headers for downloads - handle both string and dictionary formats
        filename = None
        if isinstance(document_data, dict):
            # Try to get the original filename from the document data
            filename = document_data.get('filename', blob_name)
        else:
            # If document_data is a string, use the blob name
            filename = blob_name
            
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        
        return Response(
            content=content,
            media_type=content_type
        )
    except Exception as e:
        logging.error(f"Error serving property document: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document")
    finally:
        if azure_storage:
            await azure_storage.close()

@router.get("/property-image/{property_id}/{image_index}")
async def get_property_image(
    property_id: str, 
    image_index: int,
    response: Response,
    token_payload: dict = Depends(AuthHandler.auth_wrapper)
):
    """
    Get a specific property image by property ID and image index
    """
    azure_storage = None
    try:
        # Get the property details from database
        db = await get_database()
        seller_id = token_payload['sub']
        
        # Find the property in the properties collection
        property_doc = await db['properties'].find_one({
            'id': property_id,
            'seller_id': seller_id
        })
                
        if not property_doc or not property_doc.get('images') or len(property_doc['images']) <= image_index:
            raise HTTPException(status_code=404, detail="Image not found")
        
        # Get the specified image
        image_data = property_doc['images'][image_index]
        
        # Create Azure storage service
        azure_storage = AzureStorageService()
        
        # Extract filename from URL
        image_url = image_data['url']
        url_parts = image_url.split('/')
        container_name = azure_storage.container_property_images  # Use configured container name
        blob_name = url_parts[-1].split('?')[0]  # Remove SAS token if present
        
        # URL decode the blob name
        blob_name = urllib.parse.unquote(blob_name)
        
        logging.info(f"Retrieving property image: container={container_name}, blob={blob_name}")
        
        # Download the image
        image_content = await azure_storage.download_file(container_name, blob_name)
        
        # Set cache headers
        response.headers["Cache-Control"] = "public, max-age=3600"
        
        # Determine content type
        content_type = image_data.get('content_type', 'image/jpeg')
        
        return Response(
            content=image_content,
            media_type=content_type
        )
    except Exception as e:
        logging.error(f"Error serving property image: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve image")
    finally:
        if azure_storage:
            await azure_storage.close()

@router.get("/public-property-image/{property_id}/{image_index}")
async def get_public_property_image(
    property_id: str, 
    image_index: int,
    response: Response
):
    """
    Public endpoint to get property images (no authentication required)
    """
    azure_storage = None
    try:
        # Get the database
        db = await get_database()
        
        # In the new structure, properties are stored in their own collection
        property_doc = await db['properties'].find_one({'id': property_id})
        
        if not property_doc or not property_doc.get('images') or len(property_doc['images']) <= image_index:
            raise HTTPException(status_code=404, detail="Image not found")
        
        image_data = property_doc['images'][image_index]
        image_url = image_data['url']
        
        # Create Azure storage service
        azure_storage = AzureStorageService()
        
        # Extract container and blob name
        url_parts = image_url.split('/')
        container_name = azure_storage.container_property_images  # Use configured container name
        blob_name = url_parts[-1].split('?')[0]  # Remove SAS token
        
        # URL decode the blob name
        blob_name = urllib.parse.unquote(blob_name)
        
        logging.info(f"Retrieving property image: container={container_name}, blob={blob_name}")
        
        # Download image
        image_content = await azure_storage.download_file(container_name, blob_name)
        
        # Set cache headers
        response.headers["Cache-Control"] = "public, max-age=3600"
        
        # Determine content type
        content_type = image_data.get('content_type', 'image/jpeg')
        
        return Response(
            content=image_content,
            media_type=content_type
        )
    except Exception as e:
        logging.error(f"Error serving public property image: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve image")
    finally:
        if azure_storage:
            await azure_storage.close()

@router.get("/property/{property_id}")
async def get_property(property_id: str, token_payload = Depends(AuthHandler.auth_wrapper)):
    """
    Get a specific property by ID
    """
    return await property_controller.get_property_details(token_payload, property_id)