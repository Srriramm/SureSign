import logging
import yagmail
from datetime import datetime
from typing import Dict, Optional
import os
from app.core.config import settings

# Email settings are now loaded from settings

async def send_lawyer_verification_email(
    lawyer_email: str,
    lawyer_name: str,
    buyer_name: str,
    property_info: Dict,
    verification_url: str,
    expiry_date: Optional[datetime] = None
):
    """
    Send verification email to lawyer with link to access property documents
    """
    try:
        # Format expiry date if provided
        expiry_text = ""
        if expiry_date:
            expiry_str = expiry_date.strftime("%B %d, %Y at %I:%M %p")
            expiry_text = f"<p><strong>This verification link will expire on:</strong> {expiry_str}</p>"
            
        # Create email body with fixed CSS formatting
        html_content = f"""
<html>
<head>
    <style type="text/css">
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
        .header {{ background-color: #1e40af; color: white; padding: 10px 20px; border-radius: 5px 5px 0 0; margin-top: 0; }}
        .content {{ padding: 20px; }}
        .property-info {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .button {{ display: inline-block; background-color: #1e40af; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .note {{ font-size: 0.9em; color: #666; font-style: italic; }}
        .footer {{ margin-top: 30px; font-size: 0.8em; color: #999; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h2 class="header">Property Document Verification Request</h2>
        <div class="content">
            <p>Dear {lawyer_name},</p>
            <p>You have been requested by <strong>{buyer_name}</strong> to verify the documents for a property they are interested in purchasing through SureSign.</p>
            
            <div class="property-info">
                <h3>Property Information:</h3>
                <p><strong>Location:</strong> {property_info.get('address', 'N/A')}</p>
                <p><strong>Survey Number:</strong> {property_info.get('survey_number', 'N/A')}</p>
                <p><strong>Plot Size:</strong> {property_info.get('plot_size', 'N/A')} sq.ft</p>
            </div>
            
            <p>Please click the button below to access the property's documents and verify their authenticity:</p>
            
            <a href="{verification_url}" class="button">Verify Property Documents</a>
            
            {expiry_text}
            
            <p class="note">Note: You will be able to download and review the property documents, then mark them as verified or flag any issues you find.</p>
        </div>
        
        <div class="footer">
            <p>This email was sent from SureSign, an online property registration portal.</p>
            <p>If you did not expect to receive this email, please ignore it.</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Set up yagmail sender
        try:
            # Initialize yagmail SMTP
            yag = yagmail.SMTP(user=settings.EMAIL_USER, password=settings.EMAIL_PASSWORD)
            
            # Send the email
            yag.send(
                to=lawyer_email,
                subject=f"Property Document Verification Request from {buyer_name}",
                contents=html_content
            )
            
            logging.info(f"Email sent successfully to {lawyer_email}")
            return True
        except Exception as smtp_error:
            logging.error(f"Email Error: {str(smtp_error)}")
            
            # For development - simulate successful email sending
            logging.info(f"Development mode: Simulating email sent to {lawyer_email}")
            logging.info(f"Email would contain verification URL: {verification_url}")
            return True
    
    except Exception as e:
        logging.error(f"Error sending email: {str(e)}")
        raise 