import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List
from bson import ObjectId
from fastapi import HTTPException, Request

from app.config.db import get_database
from app.utils.document_security import document_security_service
from app.models.document_access import DocumentAccessLog, DocumentAccessLimit

class SecureDocumentController:
    """
    Controller for handling secure document access with advanced security features:
    - Watermarking
    - Digital signatures
    - Download limits
    - Time-limited access tokens
    - Access logging
    """
    
    async def get_buyer_info(self, buyer_id: str) -> Dict:
        """Get buyer information for watermarking"""
        db = await get_database()
        buyer = await db['buyers'].find_one({'_id': ObjectId(buyer_id)})
        
        if not buyer:
            return {
                'id': buyer_id,
                'name': 'Unknown Buyer',
                'email': 'unknown@example.com'
            }
        
        return {
            'id': str(buyer['_id']),
            'name': buyer.get('name', 'Unknown Buyer'),
            'email': buyer.get('email', 'unknown@example.com'),
            'mobile': buyer.get('mobile_number', 'N/A')
        }
    
    async def get_property_info(self, property_id: str) -> Dict:
        """Get property information for watermarking"""
        db = await get_database()
        property_doc = await db['properties'].find_one({'id': property_id})
        
        if not property_doc:
            return {
                'id': property_id,
                'location': 'Unknown Location'
            }
        
        return {
            'id': property_doc['id'],
            'location': property_doc.get('location', property_doc.get('area', 'Unknown Location')),
            'reference': property_doc.get('reference_number', property_doc['id']),
            'type': property_doc.get('property_type', 'N/A')
        }
    
    async def check_access_limits(self, buyer_id: str, property_id: str, document_index: int) -> bool:
        """
        Check if buyer has exceeded download limits for this document
        Returns True if access is allowed, False otherwise
        """
        db = await get_database()
        access_limits_collection = db['document_access_limits']
        
        # Find access limit record for this buyer and document
        limit_record = await access_limits_collection.find_one({
            'buyer_id': buyer_id,
            'property_id': property_id,
            'document_index': document_index
        })
        
        if not limit_record:
            # No limit record yet, create one
            limit_record = DocumentAccessLimit(
                buyer_id=buyer_id,
                property_id=property_id,
                document_index=document_index,
                first_access=datetime.utcnow(),
                last_access=datetime.utcnow(),
                expiry_date=datetime.utcnow() + timedelta(days=7),  # Default 7-day expiry
                download_count=1  # This will be the first download
            ).dict()
            
            await access_limits_collection.insert_one(limit_record)
            return True
        
        # Convert to model
        limit = DocumentAccessLimit(**limit_record)
        
        # Check if expired
        if limit.expiry_date and datetime.utcnow() > limit.expiry_date:
            limit.is_expired = True
            # Update the record and deny access
            await access_limits_collection.update_one(
                {'_id': limit_record['_id']},
                {'$set': {'is_expired': True}}
            )
            return False
        
        # Check download count
        if limit.download_count >= limit.max_downloads:
            logging.warning(f"Buyer {buyer_id} has exceeded download limit for document {property_id}/{document_index}")
            return False
        
        # Update download count and last access
        await access_limits_collection.update_one(
            {'_id': limit_record['_id']},
            {
                '$inc': {'download_count': 1},
                '$set': {'last_access': datetime.utcnow()}
            }
        )
        
        return True
    
    async def log_document_access(self, buyer_id: str, property_id: str, document_index: int, 
                                  document_type: str, request: Request, 
                                  is_watermarked: bool, is_signed: bool, 
                                  signature: Optional[str] = None,
                                  access_token: Optional[str] = None) -> None:
        """
        Log document access for auditing and tracking
        """
        db = await get_database()
        access_logs_collection = db['document_access_logs']
        
        # Get client IP and user agent
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent', 'Unknown')
        
        # Create access log entry
        log_entry = DocumentAccessLog(
            buyer_id=buyer_id,
            property_id=property_id,
            document_index=document_index,
            document_type=document_type,
            download_date=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
            access_token=access_token,
            is_watermarked=is_watermarked,
            is_signed=is_signed,
            signature=signature
        ).dict()
        
        # Add to database
        await access_logs_collection.insert_one(log_entry)
    
    async def generate_secure_document_token(self, buyer_id: str, property_id: str, 
                                             document_index: int, 
                                             expires_in_hours: int = 24) -> str:
        """
        Generate a secure, time-limited access token for document download
        """
        # Create document ID
        document_id = f"{property_id}_{document_index}"
        
        # Generate token
        token = document_security_service.generate_access_token(
            buyer_id=buyer_id,
            property_id=property_id,
            document_id=document_id,
            expires_in_hours=expires_in_hours
        )
        
        return token
    
    async def validate_document_token(self, token: str, buyer_id: str, 
                                     property_id: str, document_index: int) -> bool:
        """
        Validate a document access token
        """
        document_id = f"{property_id}_{document_index}"
        
        return document_security_service.validate_access_token(
            token=token,
            buyer_id=buyer_id,
            property_id=property_id,
            document_id=document_id
        )
    
    async def apply_security_to_document(self, content: bytes, content_type: str,
                                         buyer_id: str, property_id: str, 
                                         document_index: int) -> Tuple[bytes, str]:
        """
        Apply security features to document:
        - Watermarking
        - Digital signature
        Returns: (secured_content, signature)
        """
        try:
            # Get buyer and property info for watermarking
            buyer_info = await self.get_buyer_info(buyer_id)
            property_info = await self.get_property_info(property_id)
            
            # Apply watermark based on content type
            if content_type.lower() == 'application/pdf':
                # Add watermark to PDF
                content = document_security_service.add_watermark_to_pdf(
                    content, buyer_info, property_info
                )
            elif content_type.lower() in ['application/msword', 
                                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                # Add watermark to Word document (limited functionality)
                content = document_security_service.add_watermark_to_docx(
                    content, buyer_info, property_info
                )
            
            # Apply digital signature
            content, signature = document_security_service.sign_document(content)
            
            return content, signature
        except Exception as e:
            logging.error(f"Error applying security to document: {str(e)}")
            # Return original content if security measures fail
            return content, ""
    
    async def get_secure_document(self, content: bytes, content_type: str,
                                 buyer_id: str, property_id: str,
                                 document_index: int, document_type: str,
                                 request: Request) -> Tuple[bytes, Dict]:
        """
        Process document with security features and track access
        Returns: (secured_content, metadata)
        """
        # Check access limits
        if not await self.check_access_limits(buyer_id, property_id, document_index):
            raise HTTPException(
                status_code=403,
                detail="Document access limit exceeded or expired"
            )
        
        # Apply security features
        try:
            # Get buyer and property info for watermarking
            buyer_info = await self.get_buyer_info(buyer_id)
            property_info = await self.get_property_info(property_id)
            
            # Log basic info 
            logging.info(f"Processing document for buyer {buyer_id}, property {property_id}, document index {document_index}")
            logging.info(f"Document type: {content_type}, size: {len(content)} bytes")
            
            # Handle different document types for watermarking
            is_watermarked = False
            secured_content = content
            signature = ""
            
            # Only apply watermark for PDF documents for now
            if content_type.lower() == 'application/pdf':
                # Validate the content is a PDF before attempting to watermark
                if content.startswith(b'%PDF'):
                    try:
                        # Add watermark
                        secured_content = document_security_service.add_watermark_to_pdf(
                            content, buyer_info, property_info
                        )
                        is_watermarked = True
                        logging.info(f"PDF watermarking successful: {len(secured_content)} bytes")
                    except Exception as e:
                        logging.error(f"Error watermarking PDF: {str(e)}")
                        # Fallback to original content
                        secured_content = content
                else:
                    logging.warning(f"Content claimed to be PDF but doesn't start with %PDF header")
            else:
                logging.info(f"No watermarking applied for content type: {content_type}")
                
            # Only apply digital signature if needed
            try:
                secured_content, signature = document_security_service.sign_document(secured_content)
                logging.info("Digital signature applied successfully")
            except Exception as e:
                logging.error(f"Error applying digital signature: {str(e)}")
                # Signature will remain empty string
        except Exception as e:
            logging.error(f"Error processing document security: {str(e)}")
            # Return original content if security measures fail
            secured_content = content
            is_watermarked = False
            signature = ""
        
        # Log access
        await self.log_document_access(
            buyer_id=buyer_id,
            property_id=property_id,
            document_index=document_index,
            document_type=document_type,
            request=request,
            is_watermarked=is_watermarked,
            is_signed=bool(signature),
            signature=signature
        )
        
        # Prepare metadata
        metadata = {
            'is_watermarked': is_watermarked,
            'is_signed': bool(signature),
            'download_date': datetime.utcnow().isoformat(),
            'buyer_id': buyer_id,
            'property_id': property_id,
            'document_type': document_type,
            'file_size': len(secured_content)
        }
        
        return secured_content, metadata

# Singleton instance
secure_document_controller = SecureDocumentController() 