import jwt
import time
import os
from datetime import datetime, timedelta
from typing import Dict
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get JWT secret from environment
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

class AuthHandler:
    security = HTTPBearer()
    
    def get_password_hash(self, password):
        """
        Dummy method for password hashing - in a real app, use a proper password hashing library
        """
        # This is a placeholder - in a real app, use bcrypt or similar
        return f"hashed_{password}"
    
    def verify_password(self, plain_password, hashed_password):
        """
        Dummy method for password verification - in a real app, use a proper password verification
        """
        # This is a placeholder - in a real app, use bcrypt or similar
        return hashed_password == f"hashed_{plain_password}"
    
    def create_access_token(self, user_id: str, user_type: str = "buyer") -> str:
        """
        Create a JWT access token with user ID and type
        """
        payload = {
            'exp': datetime.utcnow() + timedelta(days=7),  # 7 day expiration
            'iat': datetime.utcnow(),
            'sub': user_id,
            'type': user_type
        }
        
        try:
            return jwt.encode(
                payload,
                JWT_SECRET,
                algorithm=JWT_ALGORITHM
            )
        except Exception as e:
            logger.error(f"Error encoding JWT: {str(e)}")
            raise HTTPException(status_code=500, detail='Failed to create access token')
    
    def decode_token(self, token: str) -> dict:
        """
        Decode a JWT token
        """
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM]
            )
            
            # Check if token is expired
            if payload['exp'] < time.time():
                raise HTTPException(status_code=401, detail='Token has expired')
                
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail='Token has expired')
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail='Invalid token')
    
    def auth_wrapper(self, auth: HTTPAuthorizationCredentials = Security(security)):
        """
        Wrapper for route dependencies to validate JWT token
        """
        try:
            return self.decode_token(auth.credentials)
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(status_code=401, detail='Invalid token')
    
    def auth_wrapper_optional(self, auth: HTTPAuthorizationCredentials = Security(security, auto_error=False)):
        """
        Optional auth wrapper that doesn't error if no token is provided
        Used for endpoints that can accept token via query param or header
        """
        if auth is None:
            return None
            
        try:
            return self.decode_token(auth.credentials)
        except Exception as e:
            logger.info(f"Optional auth validation failed: {str(e)}")
            return None 