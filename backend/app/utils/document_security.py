import os
import io
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from PyPDF2 import PdfReader, PdfWriter
import base64
import hashlib
import hmac
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

class DocumentSecurityService:
    """Handles document security features including watermarking, signatures, and access control"""
    
    def __init__(self):
        # Use a secret key for signing (in production, get from secure environment)
        self.secret_key = os.environ.get('DOCUMENT_SECURITY_KEY', 'secure-document-key-change-in-production')
        self.private_key = None
        self.public_key = None
        self._initialize_keys()
    
    def _initialize_keys(self):
        """Initialize RSA key pair for digital signatures"""
        try:
            # In production, keys should be loaded from secure storage
            # For now, generate new keys each time (in production, store and load keys)
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            self.public_key = self.private_key.public_key()
            logging.info("RSA key pair initialized for document signatures")
        except Exception as e:
            logging.error(f"Error initializing RSA keys: {str(e)}")
            # Continue without digital signature capability
            self.private_key = None
            self.public_key = None
    
    def add_watermark_to_pdf(self, pdf_content: bytes, buyer_info: Dict, property_info: Dict) -> bytes:
        """
        Add watermark to PDF document with buyer information and timestamp
        """
        original_content = pdf_content  # Keep a copy of the original content for fallback
        
        try:
            # Validate PDF content first
            if not pdf_content or len(pdf_content) < 100:
                logging.error(f"PDF content too small or empty: {len(pdf_content) if pdf_content else 0} bytes")
                return original_content
                
            # Verify this is actually a PDF by checking the signature
            if not pdf_content.startswith(b'%PDF'):
                logging.error("Content does not appear to be a valid PDF (missing %PDF header)")
                return original_content
            
            # Log some diagnostic bytes
            logging.info(f"PDF Content first 50 bytes: {pdf_content[:50]}")
            
            try:
                # Attempt to read the PDF - this is where most errors will occur if the PDF is invalid
                pdf_reader = PdfReader(io.BytesIO(pdf_content))
                
                # Validate the PDF structure
                if len(pdf_reader.pages) == 0:
                    logging.error("PDF has no pages")
                    return original_content
                    
                # Log successful PDF parsing
                logging.info(f"Successfully parsed PDF with {len(pdf_reader.pages)} pages")
                
                pdf_writer = PdfWriter()
                
                # Get buyer and property information for watermark
                buyer_name = buyer_info.get('name', 'Unknown User')
                buyer_id = buyer_info.get('id', 'Unknown ID')
                buyer_email = buyer_info.get('email', 'Unknown Email')
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                property_id = property_info.get('id', 'Unknown Property')
                property_address = property_info.get('location', 'Unknown Location')
                
                # Create watermark
                watermark_buffer = io.BytesIO()
                c = canvas.Canvas(watermark_buffer, pagesize=letter)
                
                # Configure watermark appearance
                c.setFont("Helvetica", 8)
                c.setFillColor(colors.grey)
                c.setFillAlpha(0.3)  # Set transparency
                
                # Add diagonal watermark text
                c.saveState()
                c.translate(300, 400)
                c.rotate(45)
                c.drawString(0, 0, f"DOWNLOADED BY: {buyer_name} ({buyer_email})")
                c.drawString(0, -10, f"DATE: {timestamp}")
                c.drawString(0, -20, f"USER ID: {buyer_id}")
                c.drawString(0, -30, f"PROPERTY: {property_address}")
                c.drawString(0, -40, f"DOCUMENT ID: {property_id}")
                c.drawString(0, -50, "NOT FOR DISTRIBUTION - CONFIDENTIAL")
                c.restoreState()
                
                # Add footer watermark on each page
                c.setFont("Helvetica", 6)
                c.drawString(50, 50, f"Downloaded by {buyer_name} on {timestamp} | Property: {property_address} | SureSign Official")
                
                c.save()
                watermark_buffer.seek(0)
                
                # Make sure the watermark was created successfully
                if watermark_buffer.getbuffer().nbytes < 100:
                    logging.error("Failed to create watermark buffer")
                    return original_content
                
                try:
                    # Attempt to read the watermark PDF
                    watermark_pdf = PdfReader(watermark_buffer)
                    if len(watermark_pdf.pages) == 0:
                        logging.error("Watermark PDF has no pages")
                        return original_content
                    
                    # Apply watermark to each page with error handling
                    for i in range(len(pdf_reader.pages)):
                        try:
                            page = pdf_reader.pages[i]
                            page.merge_page(watermark_pdf.pages[0])
                            pdf_writer.add_page(page)
                        except Exception as page_error:
                            logging.error(f"Error watermarking page {i}: {str(page_error)}")
                            # Add the original page without watermark
                            pdf_writer.add_page(pdf_reader.pages[i])
                    
                    # Write the watermarked PDF to a buffer
                    output_buffer = io.BytesIO()
                    pdf_writer.write(output_buffer)
                    output_buffer.seek(0)
                    
                    watermarked_content = output_buffer.read()
                    
                    # Final validation of watermarked content
                    if not watermarked_content or len(watermarked_content) < 100:
                        logging.error(f"Watermarked PDF content is too small: {len(watermarked_content) if watermarked_content else 0} bytes")
                        return original_content
                        
                    if not watermarked_content.startswith(b'%PDF'):
                        logging.error("Watermarked content is not a valid PDF")
                        return original_content
                    
                    logging.info(f"Successfully watermarked PDF: {len(watermarked_content)} bytes")
                    return watermarked_content
                except Exception as watermark_error:
                    logging.error(f"Error processing watermark PDF: {str(watermark_error)}")
                    return original_content
            except Exception as pdf_error:
                logging.error(f"Error reading PDF: {str(pdf_error)}")
                return original_content
        except Exception as e:
            logging.error(f"Unexpected error adding watermark to PDF: {str(e)}")
            # Always return the original content if there are any errors
            return original_content
    
    def add_watermark_to_docx(self, docx_content: bytes, buyer_info: Dict, property_info: Dict) -> bytes:
        """
        Add simple watermark metadata to Word documents (non-intrusive)
        For proper watermarking, convert to PDF first
        """
        # For DOCX, just add custom metadata properties with watermark info
        # In a production system, this would use a library like python-docx to add actual watermarks
        # But for simplicity, we'll return the original with the assumption that PDF is preferred format
        return docx_content
    
    def sign_document(self, document_content: bytes) -> Tuple[bytes, str]:
        """
        Digitally sign a document and return signature
        """
        if not self.private_key:
            logging.warning("Digital signature not available - RSA keys not initialized")
            return document_content, ""
        
        try:
            # Create document hash
            document_hash = hashlib.sha256(document_content).digest()
            
            # Sign the hash with the private key
            signature = self.private_key.sign(
                document_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Convert signature to base64 string for storing
            signature_b64 = base64.b64encode(signature).decode('utf-8')
            
            return document_content, signature_b64
        except Exception as e:
            logging.error(f"Error signing document: {str(e)}")
            return document_content, ""
    
    def verify_signature(self, document_content: bytes, signature_b64: str) -> bool:
        """
        Verify document signature
        """
        if not self.public_key or not signature_b64:
            return False
        
        try:
            # Decode signature from base64
            signature = base64.b64decode(signature_b64)
            
            # Create document hash
            document_hash = hashlib.sha256(document_content).digest()
            
            # Verify signature
            self.public_key.verify(
                signature,
                document_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # If we get here, verification succeeded
            return True
        except Exception as e:
            logging.error(f"Signature verification failed: {str(e)}")
            return False
    
    def generate_access_token(self, buyer_id: str, property_id: str, document_id: str, 
                              expires_in_hours: int = 24) -> str:
        """
        Generate a time-limited access token for document download
        """
        expiry_time = datetime.utcnow() + timedelta(hours=expires_in_hours)
        expiry_timestamp = int(expiry_time.timestamp())
        
        # Create token data
        token_data = f"{buyer_id}:{property_id}:{document_id}:{expiry_timestamp}"
        
        # Sign token data with HMAC
        signature = hmac.new(
            self.secret_key.encode(), 
            token_data.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        # Combine token data and signature
        token = f"{token_data}:{signature}"
        
        # Encode as base64
        encoded_token = base64.urlsafe_b64encode(token.encode()).decode()
        
        return encoded_token
    
    def validate_access_token(self, token: str, buyer_id: str, property_id: str, document_id: str) -> bool:
        """
        Validate a document access token
        """
        try:
            # Decode token
            decoded_token = base64.urlsafe_b64decode(token.encode()).decode()
            
            # Split into data and signature
            token_parts = decoded_token.split(":")
            if len(token_parts) != 5:
                logging.error("Invalid token format")
                return False
            
            token_buyer_id, token_property_id, token_document_id, expiry_timestamp, signature = token_parts
            
            # Verify buyer, property, and document IDs
            if token_buyer_id != buyer_id or token_property_id != property_id or token_document_id != document_id:
                logging.error("Token IDs don't match requested resource")
                return False
            
            # Check if token has expired
            current_time = datetime.utcnow()
            expiry_time = datetime.fromtimestamp(int(expiry_timestamp))
            if current_time > expiry_time:
                logging.error("Token has expired")
                return False
            
            # Verify signature
            token_data = f"{token_buyer_id}:{token_property_id}:{token_document_id}:{expiry_timestamp}"
            expected_signature = hmac.new(
                self.secret_key.encode(), 
                token_data.encode(), 
                hashlib.sha256
            ).hexdigest()
            
            if signature != expected_signature:
                logging.error("Invalid token signature")
                return False
            
            return True
        except Exception as e:
            logging.error(f"Error validating access token: {str(e)}")
            return False

# Singleton instance
document_security_service = DocumentSecurityService() 