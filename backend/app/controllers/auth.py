from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import uuid
from azure.storage.blob import BlobServiceClient
from app.models.user import Seller, Buyer
from app.middleware.auth_middleware import AuthHandler
from app.config.db import get_database
from app.config.azure_config import AzureStorageService
from datetime import datetime
import logging
import asyncio

router = APIRouter()

# Azure Blob Storage Configuration - Using environment variables
AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
USER_SELFIES_CONTAINER = os.getenv('AZURE_CONTAINER_USER_SELFIES', 'sec-user-kyc-images')

class AuthController:
    @staticmethod
    async def register_user(user_data: dict, user_type: str):
        """
        Register a new user (seller or buyer)
        """
        db = await get_database()
        
        # Check if user already exists
        existing_user = await db[f"{user_type}s"].find_one({
            "$or": [
                {"email": user_data['email']},
                {"mobile_number": user_data['mobile_number']}
            ]
        })
        
        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Hash password
        user_data['password'] = AuthHandler.hash_password(user_data['password'])
        
        # Create user model based on type
        if user_type == 'seller':
            user = Seller(**user_data)
        else:
            user = Buyer(**user_data)
        
        # Convert to dictionary for insertion
        user_dict = user.model_dump(by_alias=True, exclude_unset=True)
        
        # Insert user to database
        result = await db[f"{user_type}s"].insert_one(user_dict)
        
        return str(result.inserted_id)

    @staticmethod
    async def upload_selfie(user_id: str, user_type: str, selfie: UploadFile = File(...)):
        """
        Upload user selfie to Azure Blob Storage with enhanced security
        """
        azure_storage = None
        try:
            # Create Azure storage service
            azure_storage = AzureStorageService()
            
            # Generate unique filename - includes user type for additional context
            timestamp = datetime.now().timestamp()
            file_extension = selfie.filename.split('.')[-1] if '.' in selfie.filename else 'jpg'
            blob_name = f"{user_type}_{user_id}_{timestamp}_selfie.{file_extension}"
            
            # Read selfie file
            selfie_content = await selfie.read()
            
            # Set metadata for the blob
            metadata = {
                "user_id": user_id,
                "user_type": user_type,
                "content_type": selfie.content_type,
                "original_filename": selfie.filename,
                "upload_timestamp": str(timestamp)
            }
            
            # Use the container specified in .env file
            container_name = USER_SELFIES_CONTAINER
            logging.info(f"Uploading selfie to container: {container_name}")
            
            # Upload to Azure using the container from .env
            upload_result = await azure_storage.upload_file(
                container_name=container_name,
                file_name=blob_name,
                file_content=selfie_content,
                content_type=selfie.content_type,
                metadata=metadata
            )
            
            # Update user record with selfie information
            db = await get_database()
            await db[f"{user_type}s"].update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "selfie_url": upload_result["direct_url"],
                    "selfie_sas_url": upload_result["sas_url"],
                    "selfie_filename": upload_result["secure_filename"],
                    "selfie_original_filename": selfie.filename,
                    "selfie_content_type": selfie.content_type,
                    "selfie_timestamp": timestamp,
                    "selfie_container": container_name,
                    "selfie_upload_date": datetime.utcnow()
                }}
            )
            
            return {
                "selfie_url": upload_result["direct_url"],
                "secure_filename": upload_result["secure_filename"],
                "timestamp": upload_result["timestamp"]
            }
        
        except Exception as e:
            logging.error(f"Selfie upload failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Selfie upload failed: {str(e)}")
        finally:
            # Close Azure storage client
            if azure_storage:
                await azure_storage.close()

    @staticmethod
    async def login(email: str, password: str, user_type: str):
        """
        User login with email and password
        """
        db = await get_database()
        
        # Find user
        user = await db[f"{user_type}s"].find_one({"email": email})
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Verify password
        if not AuthHandler.verify_password(password, user['password']):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Generate JWT token
        token = AuthHandler.encode_token(str(user['_id']), user_type)
        
        return {"access_token": token, "token_type": "bearer", "user_type": user_type, "user_id": str(user['_id'])}

    @classmethod
    async def complete_user_registration(cls, user_data, selfie, user_type):
        db = await get_database()
        azure_storage = None
        
        # Check if user already exists
        existing_user = await db[f"{user_type}s"].find_one({
            "$or": [
                {"email": user_data['email']},
                {"mobile_number": user_data['mobile_number']}
            ]
        })
        
        if existing_user:
            raise HTTPException(status_code=400, detail=f"{user_type.capitalize()} already exists")
            
        try:
            # Initialize Azure storage service
            azure_storage = AzureStorageService()
            
            # Hash password
            user_data['password'] = AuthHandler.hash_password(user_data['password'])
            
            # Create user model based on type
            if user_type == 'seller':
                user = Seller(**user_data)
                collection = 'sellers'
            else:
                user = Buyer(**user_data)
                collection = 'buyers'
            
            # Convert to dictionary for insertion
            user_dict = user.model_dump(by_alias=True, exclude_unset=True)
            
            # Insert user to database
            result = await db[collection].insert_one(user_dict)
            user_id = str(result.inserted_id)
            
            # Upload selfie to Azure Storage
            upload_result = None  # Initialize upload_result
            if selfie:
                # Read selfie file
                selfie_content = await selfie.read()
                
                # Set metadata for the blob
                metadata = {
                    "user_id": user_id,
                    "user_type": user_type,
                    "content_type": selfie.content_type,
                    "original_filename": selfie.filename,
                    "upload_timestamp": str(datetime.now().timestamp())
                }
                
                # Generate a secure filename
                timestamp = datetime.now().timestamp()
                file_extension = selfie.filename.split('.')[-1] if '.' in selfie.filename else 'jpg'
                secure_filename = f"{user_type}_{user_id}_{timestamp}_selfie.{file_extension}"
                
                # Upload to Azure Blob Storage with enhanced security
                upload_result = await azure_storage.upload_file(
                    container_name=USER_SELFIES_CONTAINER,
                    file_name=secure_filename,
                    file_content=selfie_content,
                    content_type=selfie.content_type,
                    metadata=metadata
                )
                
                # Update user with selfie information
                await db[collection].update_one(
                    {"_id": ObjectId(user_id)},
                    {"$set": {
                        "selfie_url": upload_result["direct_url"],
                        "selfie_sas_url": upload_result["sas_url"],
                        "selfie_filename": upload_result["secure_filename"],
                        "selfie_original_filename": selfie.filename,
                        "selfie_content_type": selfie.content_type,
                        "selfie_timestamp": datetime.now().timestamp(),
                        "selfie_container": USER_SELFIES_CONTAINER,
                        "selfie_upload_date": datetime.utcnow(),
                        "is_verified": True  # Assuming selfie verification
                    }}
                )
            
            return {
                "user_id": user_id, 
                "selfie_url": upload_result["direct_url"] if upload_result else None,
                "message": f"{user_type.capitalize()} registration completed successfully"
            }
        
        except Exception as e:
            # Rollback user creation if any step fails
            if 'result' in locals() and result.inserted_id:
                await db[collection].delete_one({"_id": result.inserted_id})
            logging.error(f"Registration failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
        finally:
            # Close Azure storage client
            if azure_storage:
                await azure_storage.close()

    @staticmethod
    async def get_user_selfie(user_id: str, user_type: str):
        """
        Get user selfie URL and container information with enhanced debugging
        """
        db = await get_database()
        azure_storage = None
        
        try:
            user = await db[f"{user_type}s"].find_one({"_id": ObjectId(user_id)})
            
            if not user:
                logging.error(f"User not found: {user_id} (type: {user_type})")
                raise HTTPException(status_code=404, detail=f"{user_type.capitalize()} not found")
                
            # Check if user has selfie
            if not user.get('selfie_url'):
                logging.info(f"No selfie URL found for user {user_id}")
                return {"message": "No selfie found for user", "selfie_url": None}
                
            # If we have the filename and container, we can download directly
            filename = user.get('selfie_filename')
            container = user.get('selfie_container', USER_SELFIES_CONTAINER)
            
            if filename and container:
                # Initialize Azure storage
                azure_storage = AzureStorageService()
                
                try:
                    # Download selfie
                    selfie_data = await azure_storage.download_file(container, filename)
                    
                    # Return selfie data and URL info
                    return {
                        "selfie_url": user.get('selfie_url'),
                        "selfie_filename": filename,
                        "selfie_container": container,
                        "selfie_data": selfie_data
                    }
                except Exception as azure_error:
                    logging.error(f"Azure error: {str(azure_error)}")
                    # Fall back to URL
                    return {
                        "selfie_url": user.get('selfie_url'),
                        "error": f"Could not download selfie: {str(azure_error)}"
                    }
            
            # If we don't have filename/container, return URL only
            return {"selfie_url": user.get('selfie_url')}
        
        except Exception as e:
            logging.error(f"Error getting selfie: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to get selfie: {str(e)}")
        finally:
            # Close Azure storage client
            if azure_storage:
                await azure_storage.close()

    @staticmethod
    async def update_user_selfie_container(user_id: str, user_type: str, container_name: str, blob_name: str):
        """
        Update user selfie container information
        """
        db = await get_database()
        azure_storage = None
        
        try:
            # Find user
            user = await db[f"{user_type}s"].find_one({"_id": ObjectId(user_id)})
            
            if not user:
                raise HTTPException(status_code=404, detail=f"{user_type.capitalize()} not found")
            
            # Initialize Azure storage for URL generation
            azure_storage = AzureStorageService()
            
            # Generate direct URL
            direct_url = f"https://{azure_storage.account_name}.blob.core.windows.net/{container_name}/{blob_name}"
            
            # Generate SAS URL
            sas_token = generate_blob_sas(
                account_name=azure_storage.account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=azure_storage.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(days=7)  # 7-day expiry
            )
            sas_url = f"{direct_url}?{sas_token}"
            
            # Update user with new selfie container information
            await db[f"{user_type}s"].update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "selfie_url": direct_url,
                    "selfie_sas_url": sas_url,
                    "selfie_filename": blob_name,
                    "selfie_container": container_name,
                    "selfie_updated_at": datetime.utcnow()
                }}
            )
            
            return {
                "message": "Selfie container information updated",
                "selfie_url": direct_url,
                "selfie_sas_url": sas_url
            }
        except Exception as e:
            logging.error(f"Failed to update selfie container: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to update selfie container: {str(e)}")
        finally:
            # Close Azure storage client
            if azure_storage:
                await azure_storage.close()