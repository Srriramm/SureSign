from fastapi import HTTPException, Security, Request, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from datetime import datetime, timedelta
from jose import jwt
import bcrypt
import os
from typing import Optional
import logging

class AuthHandler:
    security = HTTPBearer(auto_error=False)
    SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
    ALGORITHM = "HS256"

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )

    @classmethod
    def encode_token(cls, user_id: str, user_type: str) -> str:
        """Generate a JWT token"""
        payload = {
            'exp': datetime.utcnow() + timedelta(days=1),
            'iat': datetime.utcnow(),
            'sub': str(user_id),
            'type': user_type
        }
        return jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)

    @classmethod
    def decode_token(cls, token: str):
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail='Token has expired')
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail='Invalid token')
    
    @classmethod
    def auth_wrapper(cls, auth: HTTPAuthorizationCredentials = Security(security)):
        """
        Standard auth wrapper that requires valid authentication
        
        Raises:
            HTTPException: 401 if no valid token is provided
        """
        if not auth:
            raise HTTPException(status_code=401, detail="Authentication required")
        return cls.decode_token(auth.credentials)
        
    @classmethod
    async def auth_wrapper_optional(cls, auth: Optional[HTTPAuthorizationCredentials] = Depends(security)):
        """
        Optional middleware that returns None instead of raising an exception if no valid token is provided
        """
        if not auth:
            return None
            
        try:
            return cls.decode_token(auth.credentials)
        except Exception as e:
            logging.warning(f"Auth error (non-blocking): {str(e)}")
            return None
            
    @classmethod
    async def auth_wrapper_with_query(cls, request: Request, auth: Optional[HTTPAuthorizationCredentials] = Depends(security)):
        """
        Enhanced wrapper for token authentication that checks multiple sources
        - Authorization header
        - Cookies
        - Query parameters
        """
        # Allow unauthenticated access to public endpoints
        if request.url.path.startswith('/public/'):
            return None
        
        # Check for token in Authorization header
        if auth is not None:
            return cls.decode_token(auth.credentials)
        
        # Check for token in cookies
        token = request.cookies.get("access_token")
        if token:
            return cls.decode_token(token)
        
        # Check for token in query parameters
        token = request.query_params.get("token")
        if token:
            return cls.decode_token(token)
            
        raise HTTPException(status_code=401, detail='Authentication required')