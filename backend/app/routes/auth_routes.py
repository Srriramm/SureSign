from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, BackgroundTasks
from typing import Annotated, List
from pydantic import BaseModel

from app.controllers.auth import AuthController
from app.middleware.auth_middleware import AuthHandler
from app.config.azure_config import AzureStorageService

router = APIRouter()

class RegisterRequest(BaseModel):
    name: str
    mobile_number: str
    email: str
    password: str

@router.post("/register/{user_type}")
async def register_user(
    user_type: str, 
    name: Annotated[str, Form()],
    mobile_number: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()]
):
    """
    Register a new user (seller or buyer)
    """
    user_data = {
        "name": name,
        "mobile_number": mobile_number,
        "email": email,
        "password": password
    }
    
    user_id = await AuthController.register_user(user_data, user_type)
    return {"user_id": user_id, "message": f"{user_type.capitalize()} registered successfully"}

@router.post("/upload_selfie/{user_type}/{user_id}")
async def upload_selfie(
    user_type: str, 
    user_id: str, 
    selfie: UploadFile = File(...),
    token_payload = Depends(AuthHandler.auth_wrapper)
):
    """
    Upload user selfie
    
    - Improved endpoint to handle user selfie uploads
    - Stores the image in the standardized user-profile-images container
    - Maintains consistent naming conventions
    """
    # Security check - only allow users to upload their own selfie
    if token_payload['sub'] != user_id:
        raise HTTPException(status_code=403, detail="You can only upload your own selfie")
        
    result = await AuthController.upload_selfie(user_id, user_type, selfie)
    return result

@router.get("/user-selfie/{user_type}/{user_id}")
async def get_user_selfie(
    user_type: str,
    user_id: str,
    token_payload = Depends(AuthHandler.auth_wrapper)
):
    """
    Get user selfie URL
    
    - Returns the selfie URL for a specific user
    - Handles container migration if needed
    - Ensures consistent access to user profile images
    """
    # Allow admins and self access
    if token_payload['sub'] != user_id:
        raise HTTPException(status_code=403, detail="You can only access your own selfie")
    
    return await AuthController.get_user_selfie(user_id, user_type)

@router.post("/migrate-selfies")
async def migrate_selfies(
    background_tasks: BackgroundTasks,
    token_payload: dict = Depends(AuthHandler.auth_wrapper)
):
    """
    Migrate all existing selfies to the new secure container structure
    
    This endpoint is admin-only and initiates a background task to:
    - Find all selfies in legacy containers
    - Migrate them to the new secure container structure
    - Update user records with the new selfie information
    - Apply proper security settings and metadata
    
    Returns a status message and task ID for tracking
    """
    # Check if user is admin
    if token_payload.get('type') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required for this operation")
    
    # Start migration task in background
    task_id = await AuthController.start_selfie_migration(background_tasks)
    
    return {
        "status": "migration_started",
        "message": "Selfie migration process has been initiated in the background",
        "task_id": task_id
    }

@router.get("/migration-status/{task_id}")
async def migration_status(
    task_id: str,
    token_payload: dict = Depends(AuthHandler.auth_wrapper)
):
    """
    Check the status of a migration task
    
    This endpoint allows admins to check the progress of a migration task
    """
    # Check if user is admin
    if token_payload.get('type') != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required for this operation")
    
    status = await AuthController.get_migration_status(task_id)
    return status

@router.post("/complete_registration/{user_type}")
async def complete_user_registration(
    user_type: str,
    name: Annotated[str, Form()],
    mobile_number: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    selfie: UploadFile = File(...)
):
    """
    Complete user registration with all details
    
    - Enhanced registration flow with selfie upload
    - Uses standardized container structure
    - Provides comprehensive user registration in one step
    """
    user_data = {
        "name": name,
        "mobile_number": mobile_number,
        "email": email,
        "password": password
    }
    
    result = await AuthController.complete_user_registration(user_data, selfie, user_type)
    return result


@router.post("/login/{user_type}")
async def login(
    user_type: str,
    email: Annotated[str, Form()], 
    password: Annotated[str, Form()]
):
    """
    User login
    """
    return await AuthController.login(email, password, user_type)

@router.get("/validate-token")
async def validate_token(token_payload = Depends(AuthHandler.auth_wrapper)):
    """
    Validate JWT token
    
    This endpoint checks if a token is valid and returns the user information
    if it is. It will automatically return a 401/403 status code if the token
    is invalid or expired due to the auth_wrapper dependency.
    """
    return {"valid": True, "user_id": token_payload['sub'], "user_type": token_payload['type']}