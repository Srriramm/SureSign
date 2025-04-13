from fastapi import APIRouter, Depends, File, UploadFile, Form, Path, Body, Request, Query
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
from datetime import datetime
import base64
import urllib.parse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from io import BytesIO
import zipfile
from app.utils.encryption import FileEncryptor
from app.core.config import settings
import json

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
async def get_property_document(
    property_id: str, 
    document_index: int, 
    response: Response, 
    token: Optional[str] = None,
    filename: Optional[str] = None,
    request: Request = None,
    current_user: Optional[dict] = Depends(AuthHandler.auth_wrapper_optional)
):
    """
    Get a specific property document by property ID and document index
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
        
        # Get the property details
        db = await get_database()
        seller_id = current_user['sub']
        
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
        document_url = None
        original_filename = None
        document_type = None
        is_encrypted = False
        
        # If document_data is a string, it's the URL directly (old format)
        if isinstance(document_data, str):
            document_url = document_data
            logging.info(f"Document URL is a direct string: {document_url}")
            # Assume old format documents are encrypted
            is_encrypted = True
        # If it's a dict, extract the URL and encrypted flag
        elif isinstance(document_data, dict):
            document_url = document_data.get('url')
            original_filename = document_data.get('filename')
            document_type = document_data.get('type')
            # Check if document is marked as encrypted
            is_encrypted = document_data.get('encrypted', True)  # Default to True for backward compatibility
            logging.info(f"Document URL extracted from dictionary: {document_url}")
            logging.info(f"Original filename: {original_filename}, Type: {document_type}, Encrypted: {is_encrypted}")
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
        
        # If the document is encrypted, decrypt it before serving
        if is_encrypted and "raw" not in request.query_params:
            try:
                # Create a file encryptor instance
                file_encryptor = FileEncryptor()
                
                # Decrypt the content
                logging.info(f"Decrypting document content of size {len(content)} bytes")
                content = file_encryptor.decrypt_data(content)
                logging.info(f"Successfully decrypted document to {len(content)} bytes")
            except Exception as e:
                logging.error(f"Error decrypting document: {str(e)}")
                # If decryption fails, provide a helpful error message
                raise HTTPException(
                    status_code=500, 
                    detail="This document is encrypted and could not be decrypted. Try requesting the raw version."
                )
        else:
            logging.info(f"Serving unencrypted document of size {len(content)} bytes")
        
        # Determine content type and extension
        content_type = "application/octet-stream"  # Default
        file_extension = ".bin"
        
        # From the original filename if available
        if original_filename and '.' in original_filename:
            extension = original_filename.split('.')[-1].lower()
            if extension == 'pdf':
                content_type = "application/pdf"
                file_extension = ".pdf"
            elif extension == 'doc':
                content_type = "application/msword"
                file_extension = ".doc"
            elif extension == 'docx':
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                file_extension = ".docx"
            elif extension == 'txt':
                content_type = "text/plain"
                file_extension = ".txt"
        # Or from blob name
        elif blob_name and '.' in blob_name:
            extension = blob_name.split('.')[-1].lower()
            if extension == 'pdf':
                content_type = "application/pdf"
                file_extension = ".pdf"
            elif extension == 'doc':
                content_type = "application/msword"
                file_extension = ".doc"
            elif extension == 'docx':
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                file_extension = ".docx"
            elif extension == 'txt':
                content_type = "text/plain"
                file_extension = ".txt"
        
        # Determine final filename
        if filename:
            # Use provided filename
            final_filename = filename
            # Ensure it has the correct extension
            if not final_filename.lower().endswith(file_extension):
                final_filename = f"{final_filename}{file_extension}"
        elif original_filename:
            # Clean up the original filename
            final_filename = original_filename.split('_')[-1]
            final_filename = final_filename.replace('[', '').replace(']', '')
            # Ensure it has an extension
            if not any(final_filename.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.txt']):
                final_filename = f"{final_filename}{file_extension}"
        elif document_type:
            # Generate from document type
            safe_type = document_type.lower().replace(' ', '_')
            final_filename = f"{safe_type}{file_extension}"
        else:
            # Default generic name with extension
            final_filename = f"document{file_extension}"
        
        # Make sure the filename is clean and safe
        final_filename = ''.join(c for c in final_filename if c.isalnum() or c in '._- ')
        
        logging.info(f"Serving document: filename={final_filename}, content-type={content_type}")
        
        # Special handling for Word documents (.doc, .docx)
        if file_extension.lower() in ['.doc', '.docx']:
            logging.info(f"Handling Word document: {blob_name} with content length {len(content)}")
            
            # Check for verified mode (with blockchain verification certificate)
            verified_mode = request.query_params.get('verified', 'false').lower() == 'true'
            if verified_mode:
                logging.info(f"Serving document with verification certificate")
                try:
                    # Get blockchain verification data
                    blockchain_hash = None
                    if isinstance(document_data, dict) and document_data.get('blockchain_tx_hash'):
                        blockchain_hash = document_data.get('blockchain_tx_hash')
                    
                    if not blockchain_hash:
                        raise HTTPException(status_code=400, detail="Blockchain verification data not available")
                    
                    # Create a verification certificate PDF
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.pagesizes import letter
                    from reportlab.lib import colors
                    from io import BytesIO
                    import tempfile
                    import zipfile
                    import os
                    
                    # Create a temporary file for the verification certificate
                    temp_dir = tempfile.mkdtemp()
                    cert_path = os.path.join(temp_dir, 'verification_certificate.pdf')
                    
                    # Generate verification certificate
                    c = canvas.Canvas(cert_path, pagesize=letter)
                    
                    # Add certificate header
                    c.setFont("Helvetica-Bold", 18)
                    c.drawString(72, 750, "Document Verification Certificate")
                    
                    # Add SureSign logo/header
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(72, 720, "SureSign Blockchain Verification")
                    
                    # Add document details
                    c.setFont("Helvetica", 12)
                    c.drawString(72, 680, f"Document Name: {final_filename}")
                    c.drawString(72, 660, f"Property ID: {property_id}")
                    c.drawString(72, 640, f"Document Type: {document_type or 'N/A'}")
                    c.drawString(72, 620, f"Date Verified: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Add blockchain verification details
                    c.setFont("Helvetica-Bold", 12)
                    c.drawString(72, 580, "Blockchain Verification Details:")
                    
                    c.setFont("Helvetica", 10)
                    c.drawString(72, 560, f"Transaction Hash: {blockchain_hash}")
                    c.drawString(72, 540, "Verification Method: SHA-256 with Blockchain Timestamp")
                    c.drawString(72, 520, "This document has been verified against its blockchain hash.")
                    c.drawString(72, 500, "To verify independently, check the transaction hash on the blockchain.")
                    
                    # Add legal notice
                    c.setFont("Helvetica-Bold", 12)
                    c.drawString(72, 460, "Legal Notice:")
                    
                    c.setFont("Helvetica", 10)
                    c.drawString(72, 440, "This certificate serves as proof that the attached document has been")
                    c.drawString(72, 425, "verified against its registered blockchain hash. The hash uniquely")
                    c.drawString(72, 410, "identifies the document and ensures it has not been altered since")
                    c.drawString(72, 395, "registration.")
                    
                    # Add verification status
                    c.setFont("Helvetica-Bold", 14)
                    c.setFillColor(colors.green)
                    c.drawString(72, 350, "VERIFICATION STATUS: VERIFIED")
                    c.setFillColor(colors.black)
                    
                    # Add footer
                    c.setFont("Helvetica", 8)
                    c.drawString(72, 72, f"Certificate generated by SureSign on {datetime.now().strftime('%Y-%m-%d')}")
                    c.drawString(72, 60, "This certificate is computer-generated and does not require a signature.")
                    
                    c.save()
                    
                    # Now create a zip file containing both the certificate and original document
                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        # Add the verification certificate
                        zipf.write(cert_path, 'verification_certificate.pdf')
                        
                        # Add the original document
                        doc_filename = 'original_' + final_filename
                        zipf.writestr(doc_filename, content)
                        
                        # Add a README
                        readme_content = f"""
                        # SureSign Verified Document Package
                        
                        This package contains:
                        
                        1. verification_certificate.pdf - A certificate verifying the document's blockchain hash
                        2. {doc_filename} - The original document
                        
                        The verification certificate contains the blockchain transaction hash that can be used
                        to independently verify the document's authenticity.
                        
                        Transaction Hash: {blockchain_hash}
                        
                        For legal verification, both files should be kept together.
                        """
                        
                        zipf.writestr('README.txt', readme_content)
                    
                    # Clean up the temporary directory
                    os.unlink(cert_path)
                    os.rmdir(temp_dir)
                    
                    # Get the zip data
                    zip_buffer.seek(0)
                    verified_package = zip_buffer.read()
                    
                    # Set response headers for the zip file
                    response.headers["Content-Type"] = "application/zip"
                    response.headers["Content-Disposition"] = f'attachment; filename="verified_{final_filename}.zip"'
                    response.headers["Content-Length"] = str(len(verified_package))
                    
                    return Response(
                        content=verified_package,
                        media_type="application/zip",
                        headers=response.headers
                    )
                    
                except Exception as e:
                    logging.error(f"Error creating verification package: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Failed to create verification package: {str(e)}")
            
            # Check for raw mode (bypass blockchain verification)
            raw_mode = request.query_params.get('raw', 'false').lower() == 'true'
            if raw_mode:
                logging.info(f"Serving Word document in raw mode")
                try:
                    # Set minimal headers to ensure the file is served unmodified
                    response.headers["Content-Type"] = content_type
                    response.headers["Content-Length"] = str(len(content))
                    response.headers["Content-Disposition"] = f'attachment; filename="{final_filename}"'
                    # Force binary transfer
                    response.headers["Content-Transfer-Encoding"] = "binary"
                    
                    return Response(
                        content=content,
                        headers=response.headers
                    )
                except Exception as e:
                    logging.error(f"Error serving raw Word document: {str(e)}")
                    raise HTTPException(status_code=500, detail="Failed to serve raw document")
            
            # Check if this is a viewing request or download request
            view_mode = request.query_params.get('view', 'false').lower() == 'true'
            
            # For view mode, serve as inline content
            if view_mode:
                logging.info(f"Serving Word document in view mode")
                try:
                    response.headers["Content-Type"] = content_type
                    response.headers["Content-Length"] = str(len(content))
                    response.headers["Content-Disposition"] = f'inline; filename="{final_filename}"'
                    response.headers["X-Content-Type-Options"] = "nosniff"
                    
                    # Add blockchain verification header if available
                    if isinstance(document_data, dict) and document_data.get('blockchain_tx_hash'):
                        response.headers["X-Blockchain-Hash"] = document_data.get('blockchain_tx_hash')
                    
                    return Response(
                        content=content,
                        media_type=content_type,
                    )
                except Exception as e:
                    logging.error(f"Error serving Word document in view mode: {str(e)}")
                    raise HTTPException(status_code=500, detail="Failed to view document")
            
            # For download mode (default)
            try:
                # Set correct headers for Word documents
                response.headers["Content-Type"] = content_type
                response.headers["Content-Length"] = str(len(content))
                response.headers["Content-Disposition"] = f'attachment; filename="{final_filename}"'
                response.headers["Content-Transfer-Encoding"] = "binary"
                response.headers["X-Content-Type-Options"] = "nosniff"
                
                # Add blockchain verification header if available
                if isinstance(document_data, dict) and document_data.get('blockchain_tx_hash'):
                    response.headers["X-Blockchain-Hash"] = document_data.get('blockchain_tx_hash')
                
                return Response(
                    content=content,
                    media_type=content_type,
                )
            except Exception as e:
                logging.error(f"Error processing Word document for download: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to process document")
        
        # For other document types
        response.headers["Content-Type"] = content_type
        response.headers["Content-Disposition"] = f'attachment; filename="{final_filename}"'
        response.headers["Content-Length"] = str(len(content))
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        # For debugging
        logging.info(f"Response headers: {response.headers}")
        
        return Response(
            content=content,
            media_type=content_type,
            headers=response.headers
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error serving property document: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document")
    finally:
        if azure_storage:
            await azure_storage.close()

@router.get("/property-document/{property_id}/{document_index}/original")
async def get_original_property_document(
    property_id: str = Path(..., description="ID of the property"),
    document_index: int = Path(..., description="Index of the document in the property documents array"),
    token: str = Query(..., description="JWT token for authentication"),
    db=Depends(get_database)
):
    """
    Get the original (unencrypted) property document for sellers
    """
    azure_storage = None
    
    try:
        # Verify the seller's token
        try:
            seller = AuthHandler.decode_token(token)
            if not seller or seller.get('type') != 'seller':
                raise HTTPException(status_code=401, detail="Invalid or expired token")
        except Exception as e:
            logging.error(f"Token verification failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Get the property from the database and verify owner
        property_data = await db.properties.find_one({
            "id": property_id,
            "seller_id": seller['sub']
        })
        
        if not property_data:
            raise HTTPException(status_code=404, detail="Property not found or you don't have permission")
        
        # Check if the document exists at the specified index
        try:
            document_index = int(document_index)  # Ensure it's an integer
        except ValueError:
            raise HTTPException(status_code=400, detail="Document index must be an integer")
            
        if not property_data.get('documents') or document_index >= len(property_data['documents']):
            raise HTTPException(status_code=404, detail="Document not found")
        
        property_doc = property_data['documents'][document_index]
        logging.info(f"Retrieving original document for seller: {json.dumps(property_doc, default=str)}")
        
        # Initialize Azure storage
        azure_storage = AzureStorageService()
        
        # Get the original document URL
        original_url = property_doc.get('original_url')
        if not original_url:
            raise HTTPException(status_code=404, detail="Original document URL not found")
        
        # Get document name from property record
        document_name = property_doc.get('document_name')
        if not document_name:
            # Extract from URL if not in metadata
            document_name = original_url.split('/')[-1].split('?')[0]
            document_name = urllib.parse.unquote(document_name)
        
        # Use the designated property documents container
        container_name = azure_storage.container_property_docs
        
        # Determine the path within the container - should be seller_id/property_id/documents/document_name
        seller_id = seller['sub']
        blob_path = f"{seller_id}/{property_id}/documents/{document_name}"
        
        logging.info(f"Attempting to download original document: container={container_name}, blob_path={blob_path}")
        
        # Download the document
        try:
            document_content = await azure_storage.download_file(
                container_name=container_name,
                blob_path=blob_path
            )
            
            if not document_content:
                raise HTTPException(status_code=404, detail="Document not found in Azure storage")
            
            # Determine content type
            content_type = property_doc.get('content_type', 'application/octet-stream')
            if not content_type or content_type == 'application/octet-stream':
                if document_name.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif document_name.lower().endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif document_name.lower().endswith('.png'):
                    content_type = 'image/png'
            
            # Return the document
            return Response(
                content=document_content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f"attachment; filename=\"{document_name}\"",
                    "Content-Type": content_type,
                    "Content-Length": str(len(document_content)),
                    "Cache-Control": "no-cache"
                }
            )
            
        except Exception as e:
            logging.error(f"Error downloading original document: {str(e)}")
            
            # Alternative approach - try to extract blob name directly from URL
            try:
                logging.info(f"Attempting alternative method using URL: {original_url}")
                
                # Parse the URL to extract blob path
                url_parts = original_url.split('/')
                blob_name = None
                
                # Look for the document name in the URL
                for i, part in enumerate(url_parts):
                    if part == "documents" and i < len(url_parts) - 1:
                        blob_name = url_parts[i+1].split('?')[0]  # Remove SAS token if present
                        break
                
                if not blob_name:
                    # Just use the last part as the blob name
                    blob_name = url_parts[-1].split('?')[0]  # Remove SAS token if present
                
                # URL decode the blob name
                blob_name = urllib.parse.unquote(blob_name)
                
                # Try to download using the extracted blob name
                blob_path = f"{seller_id}/{property_id}/documents/{blob_name}"
                logging.info(f"Attempting to download with alternative path: {blob_path}")
                
                document_content = await azure_storage.download_file(
                    container_name=container_name,
                    blob_path=blob_path
                )
                
                if document_content:
                    # Determine content type
                    content_type = property_doc.get('content_type', 'application/octet-stream')
                    if not content_type or content_type == 'application/octet-stream':
                        if blob_name.lower().endswith('.pdf'):
                            content_type = 'application/pdf'
                        elif blob_name.lower().endswith(('.jpg', '.jpeg')):
                            content_type = 'image/jpeg'
                        elif blob_name.lower().endswith('.png'):
                            content_type = 'image/png'
                    
                    # Return the document
                    return Response(
                        content=document_content,
                        media_type=content_type,
                        headers={
                            "Content-Disposition": f"attachment; filename=\"{blob_name}\"",
                            "Content-Type": content_type,
                            "Content-Length": str(len(document_content)),
                            "Cache-Control": "no-cache"
                        }
                    )
            except Exception as inner_e:
                logging.error(f"Alternative method failed: {str(inner_e)}")
            
            # If we get here, both methods failed
            raise HTTPException(status_code=404, detail="Could not download the document from storage")
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in get_original_property_document: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
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
            # Download image
            image_content = await azure_storage.download_file(container_name, blob_name)
            
            # Set cache headers
            response.headers["Cache-Control"] = "public, max-age=3600"
            
            # Get content type from image data or default to jpeg
            content_type = image_data.get('content_type', 'image/jpeg')
            
            return Response(
                content=image_content,
                media_type=content_type
            )
        except Exception as e:
            logging.error(f"Error downloading image: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to download image: {str(e)}")
            
    except Exception as e:
        logging.error(f"Error serving public property image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve image: {str(e)}")
    finally:
        if azure_storage:
            await azure_storage.close()

@router.get("/property/{property_id}")
async def get_property(property_id: str, token_payload = Depends(AuthHandler.auth_wrapper)):
    """
    Get a specific property by ID
    """
    return await property_controller.get_property_details(token_payload, property_id)

@router.get("/document-requests")
async def list_document_requests(
    token_payload: dict = Depends(AuthHandler.auth_wrapper)
):
    """
    List all document access requests for properties owned by the seller
    """
    try:
        if token_payload.get('type') != 'seller':
            raise HTTPException(status_code=403, detail="Only sellers can access document requests")
            
        return await document_access_controller.list_document_requests(token_payload)
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error listing document requests: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list document requests: {str(e)}")

@router.get("/document-requests/{request_id}")
async def get_document_request_details(
    request_id: str,
    token_payload: dict = Depends(AuthHandler.auth_wrapper)
):
    """
    Get detailed information about a specific document request
    """
    try:
        if token_payload.get('type') != 'seller':
            raise HTTPException(status_code=403, detail="Only sellers can access document request details")
            
        return await document_access_controller.get_request_details(token_payload, request_id)
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error getting document request details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get document request details: {str(e)}")

@router.put("/document-requests/{request_id}")
async def handle_document_request(
    request_id: str,
    data: dict = Body(...),
    token_payload: dict = Depends(AuthHandler.auth_wrapper)
):
    """
    Approve or reject a document access request
    
    The request body should contain:
    {
        "status": "approved" or "rejected",
        "rejection_reason": "Optional reason for rejection",
        "expiry_days": 7 (optional, default is 7 days)
    }
    """
    try:
        if token_payload.get('type') != 'seller':
            raise HTTPException(status_code=403, detail="Only sellers can handle document requests")
        
        status = data.get('status')
        if not status or status not in ['approved', 'rejected']:
            raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")
        
        rejection_reason = data.get('rejection_reason')
        expiry_days = data.get('expiry_days', 7)
        
        return await document_access_controller.handle_document_request(
            token_payload, 
            request_id, 
            status, 
            rejection_reason, 
            expiry_days
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logging.error(f"Error handling document request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to handle document request: {str(e)}")

@router.get("/property/{property_id}/document/{document_index}/download")
async def get_seller_document(
    property_id: str = Path(..., description="ID of the property"),
    document_index: int = Path(..., description="Index of the document in the property documents array"),
    token_payload: dict = Depends(AuthHandler.auth_wrapper),
    db=Depends(get_database)
):
    """
    Get the original property document - simplified version with standard authentication
    """
    azure_storage = None
    
    try:
        # Verify the seller has permissions for this property
        seller_id = token_payload.get('sub')
        if token_payload.get('type') != 'seller':
            raise HTTPException(status_code=403, detail="Only sellers can access original documents")
        
        # Get the property from the database and verify owner
        property_data = await db.properties.find_one({
            "id": property_id,
            "seller_id": seller_id
        })
        
        if not property_data:
            raise HTTPException(status_code=404, detail="Property not found or you don't have permission")
        
        # Check if the document exists at the specified index
        try:
            document_index = int(document_index)  # Ensure it's an integer
        except ValueError:
            raise HTTPException(status_code=400, detail="Document index must be an integer")
            
        if not property_data.get('documents') or document_index >= len(property_data['documents']):
            raise HTTPException(status_code=404, detail="Document not found")
        
        property_doc = property_data['documents'][document_index]
        logging.info(f"Retrieving original document for seller: {json.dumps(property_doc, default=str)}")
        
        # Initialize Azure storage
        azure_storage = AzureStorageService()
        
        # Get document name and type
        document_name = property_doc.get('document_name')
        if not document_name:
            # Try to get it from the original URL
            original_url = property_doc.get('original_url')
            document_name = original_url.split('/')[-1].split('?')[0]
            document_name = urllib.parse.unquote(document_name)
        
        # Use the designated property documents container
        container_name = azure_storage.container_property_docs
        
        # The document should be stored in the pattern: seller_id/property_id/documents/document_name
        blob_path = f"{seller_id}/{property_id}/documents/{document_name}"
        
        logging.info(f"Attempting to download document: container={container_name}, blob_path={blob_path}")
        
        try:
            # Download the document
            document_content = await azure_storage.download_file(
                container_name=container_name,
                blob_path=blob_path
            )
            
            if not document_content:
                raise HTTPException(status_code=404, detail="Document not found in storage")
            
            # Determine content type based on file extension
            content_type = property_doc.get('content_type', 'application/octet-stream')
            if not content_type or content_type == 'application/octet-stream':
                if document_name.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif document_name.lower().endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif document_name.lower().endswith('.png'):
                    content_type = 'image/png'
                elif document_name.lower().endswith('.docx'):
                    content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            
            # Return the document
            return Response(
                content=document_content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f"attachment; filename=\"{document_name}\"",
                    "Content-Type": content_type,
                    "Content-Length": str(len(document_content)),
                    "Cache-Control": "no-cache"
                }
            )
            
        except Exception as e:
            logging.error(f"Error downloading document: {str(e)}")
            
            # Try alternative approach - check if the document has an original_url we can parse differently
            original_url = property_doc.get('original_url')
            if original_url:
                try:
                    # Parse the URL to find another possible blob name
                    url_parts = original_url.split('/')
                    for i, part in enumerate(url_parts):
                        if part == "documents" and i < len(url_parts) - 1:
                            alt_document_name = url_parts[i+1].split('?')[0]  # Remove SAS token
                            alt_blob_path = f"{seller_id}/{property_id}/documents/{alt_document_name}"
                            
                            logging.info(f"Trying alternative path: {alt_blob_path}")
                            alt_content = await azure_storage.download_file(
                                container_name=container_name,
                                blob_path=alt_blob_path
                            )
                            
                            if alt_content:
                                # Determine content type
                                if alt_document_name.lower().endswith('.pdf'):
                                    content_type = 'application/pdf'
                                elif alt_document_name.lower().endswith(('.jpg', '.jpeg')):
                                    content_type = 'image/jpeg'
                                elif alt_document_name.lower().endswith('.png'):
                                    content_type = 'image/png'
                                else:
                                    content_type = 'application/octet-stream'
                                
                                # Return the document
                                return Response(
                                    content=alt_content,
                                    media_type=content_type,
                                    headers={
                                        "Content-Disposition": f"attachment; filename=\"{alt_document_name}\"",
                                        "Content-Type": content_type,
                                        "Content-Length": str(len(alt_content)),
                                        "Cache-Control": "no-cache"
                                    }
                                )
                except Exception as alt_error:
                    logging.error(f"Alternative download method failed: {str(alt_error)}")
            
            # If we get here, all attempts failed
            raise HTTPException(status_code=404, detail="Could not download the document from storage")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in get_seller_document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if azure_storage:
            await azure_storage.close()

@router.get("/property/{property_id}/document/{document_index}/recover")
async def recover_original_document(
    property_id: str = Path(..., description="ID of the property"),
    document_index: int = Path(..., description="Index of the document in the property documents array"),
    token_payload: dict = Depends(AuthHandler.auth_wrapper),
    db=Depends(get_database)
):
    """
    Recover an original property document by decrypting its secure version if the original is missing
    """
    azure_storage = None
    
    try:
        # Verify the seller has permissions for this property
        seller_id = token_payload.get('sub')
        if token_payload.get('type') != 'seller':
            raise HTTPException(status_code=403, detail="Only sellers can recover original documents")
        
        # Get the property from the database and verify owner
        property_data = await db.properties.find_one({
            "id": property_id,
            "seller_id": seller_id
        })
        
        if not property_data:
            raise HTTPException(status_code=404, detail="Property not found or you don't have permission")
        
        # Check if the document exists at the specified index
        try:
            document_index = int(document_index)  # Ensure it's an integer
        except ValueError:
            raise HTTPException(status_code=400, detail="Document index must be an integer")
            
        if not property_data.get('documents') or document_index >= len(property_data['documents']):
            raise HTTPException(status_code=404, detail="Document not found")
        
        property_doc = property_data['documents'][document_index]
        logging.info(f"Attempting to recover original document: {json.dumps(property_doc, default=str)}")
        
        # Initialize Azure storage
        azure_storage = AzureStorageService()
        
        # First try to get the original document
        document_name = property_doc.get('document_name')
        if not document_name:
            # Try to get it from the original URL
            original_url = property_doc.get('original_url', '')
            if original_url:
                document_name = original_url.split('/')[-1].split('?')[0]
                document_name = urllib.parse.unquote(document_name)
            else:
                # Fallback to a generic name
                document_name = f"document_{document_index}.pdf"
        
        # Use the designated property documents container
        container_name = azure_storage.container_property_docs
        
        # The document should be stored in the pattern: seller_id/property_id/documents/document_name
        blob_path = f"{seller_id}/{property_id}/documents/{document_name}"
        original_found = False
        original_content = None
        
        try:
            # Try to download original document first
            logging.info(f"Attempting to download original document: container={container_name}, blob_path={blob_path}")
            original_content = await azure_storage.download_file(
                container_name=container_name,
                blob_path=blob_path
            )
            
            if original_content and len(original_content) > 0:
                original_found = True
                logging.info(f"Original document found, no recovery needed")
        except Exception as e:
            logging.warning(f"Original document not found: {str(e)}")
        
        # If original document is found, just return it
        if original_found and original_content:
            # Determine content type
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
            
            # Return the document
            return Response(
                content=original_content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f"attachment; filename=\"{document_name}\"",
                    "Content-Type": content_type,
                    "Content-Length": str(len(original_content)),
                    "Cache-Control": "no-cache"
                }
            )
        
        # If original document is not found, try to recover from secure document
        logging.info("Original document not found, attempting to recover from encrypted version")
        
        # Get document ID and encrypted URL from property document
        document_id = property_doc.get('document_id')
        encrypted_url = property_doc.get('encrypted_url')
        
        if not document_id:
            raise HTTPException(status_code=404, detail="Document ID not found, cannot recover document")
        
        # Import the secure document service
        from app.services.secure_document_service import SecureDocumentService
        
        # Create secure document service
        secure_doc_service = SecureDocumentService(azure_storage)
        
        try:
            # Attempt to retrieve document using secure document service
            logging.info(f"Retrieving document using SecureDocumentService: ID={document_id}")
            recovered_content = await secure_doc_service.retrieve_document(
                document_id=document_id,
                owner_id=seller_id,
                property_id=property_id
            )
            
            if not recovered_content or len(recovered_content) == 0:
                raise HTTPException(status_code=404, detail="Could not recover document content")
            
            # Determine content type
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
            
            # Optionally, save the recovered document back to the original document container
            try:
                logging.info(f"Saving recovered document to original container: {blob_path}")
                await azure_storage.upload_file(
                    container_name=container_name,
                    file_name=blob_path,
                    file_content=recovered_content,
                    content_type=content_type
                )
                logging.info("Successfully saved recovered document to original container")
            except Exception as save_error:
                logging.error(f"Failed to save recovered document: {str(save_error)}")
                # Continue even if saving fails
            
            # Return the recovered document
            return Response(
                content=recovered_content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f"attachment; filename=\"{document_name}\"",
                    "Content-Type": content_type,
                    "Content-Length": str(len(recovered_content)),
                    "Cache-Control": "no-cache",
                    "X-Document-Recovered": "true"
                }
            )
            
        except Exception as recovery_error:
            logging.error(f"Error recovering document: {str(recovery_error)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to recover document: {str(recovery_error)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in recover_original_document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        if azure_storage:
            await azure_storage.close()