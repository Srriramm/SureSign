import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './BuyerPropertyDetails.css';
import { getToken } from '../../utils/authUtils';
import LawyerVerification from './LawyerVerification';

function BuyerPropertyDetails() {
  const { propertyId } = useParams();
  const navigate = useNavigate();
  const [property, setProperty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [showRequestForm, setShowRequestForm] = useState(false);
  const [requestMessage, setRequestMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [notification, setNotification] = useState(null);
  const [documentAccess, setDocumentAccess] = useState(null);
  const [checkingAccess, setCheckingAccess] = useState(false);

  // Define checkDocumentAccess outside useEffect so it can be reused
  const checkDocumentAccess = useCallback(async () => {
    try {
      setCheckingAccess(true);
      const token = getToken('buyer');
      if (!token) {
        return;
      }

      const response = await fetch(`http://localhost:8000/buyer/document-access/${propertyId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        console.warn('Error checking document access:', response.statusText);
        return;
      }
      
      const accessData = await response.json();
      console.log('Document access data:', accessData);
      
      // If this is the first time getting access, show a notification about the download limit
      if (accessData.has_access && (!documentAccess || !documentAccess.has_access)) {
        setNotification({
          type: 'info',
          message: 'You now have access to property documents. Please note that each document can be downloaded a maximum of 3 times.'
        });
        
        // Clear notification after 8 seconds
        setTimeout(() => {
          setNotification(null);
        }, 8000);
      }
      
      setDocumentAccess(accessData);
    } catch (err) {
      console.error('Error checking document access:', err);
    } finally {
      setCheckingAccess(false);
    }
  }, [propertyId]);

  useEffect(() => {
    // Check if the user is logged in as a buyer
    const buyerToken = getToken('buyer');
    if (!buyerToken) {
      console.error('No buyer token found. User might not be logged in as a buyer.');
      setError('Please log in as a buyer to access this page');
      setTimeout(() => {
        navigate('/login/buyer');
      }, 3000);
      return;
    }
    
    const fetchPropertyDetails = async () => {
      try {
        setLoading(true);
        const token = getToken('buyer');
        if (!token) {
          navigate('/login');
          return;
        }

        // Fetch the property details from the property endpoint
        const propertyResponse = await fetch(`http://localhost:8000/buyer/property/${propertyId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!propertyResponse.ok) {
          throw new Error('Failed to fetch property details');
        }
        
        const propertyData = await propertyResponse.json();
        
        console.log('Property data:', propertyData);
        
        setProperty(propertyData);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching property details:', err);
        setError(err.message);
        setLoading(false);
      }
    };

    fetchPropertyDetails();
    checkDocumentAccess();
  }, [propertyId, navigate, checkDocumentAccess]);

  const handleGoBack = () => {
    navigate('/properties');
  };

  const handleImageClick = (index) => {
    setSelectedImageIndex(index);
  };

  const getPublicImageUrl = (index) => {
    // Use the public-property-image endpoint that doesn't require authentication
    console.log(`Generating public image URL for property ${propertyId}, index ${index}`);
    return `http://localhost:8000/buyer/property-image/${propertyId}/${index}`;
  };

  const handleImageError = (e) => {
    console.log('Image loading error in BuyerPropertyDetails');
    // Try to debug what's happening
    const imageSrc = e.target.src;
    console.log('Failed image source:', imageSrc);
    
    // Add extra debugging
    console.log('Property ID:', propertyId);
    console.log('Property images array:', property?.images);
    
    // Try loading the image again with the public endpoint
    if (!imageSrc.includes('public-property-image')) {
      const imageIndex = parseInt(imageSrc.split('/').pop()) || 0;
      console.log('Trying with public endpoint for image index:', imageIndex);
      e.target.src = getPublicImageUrl(imageIndex);
      // Add a new error handler that will just use placeholder if public endpoint also fails
      e.target.onerror = () => {
        console.log('Public endpoint also failed, using placeholder');
        e.target.onerror = null;
        e.target.src = '/placeholder.jpg';
      };
    } else {
      // If we're already using the public endpoint, fall back to placeholder
      console.log('Already using public endpoint, falling back to placeholder');
      e.target.onerror = null;
      e.target.src = '/placeholder.jpg';
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const handleRequestDocuments = () => {
    setShowRequestForm(true);
  };

  const handleSubmitRequest = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setSubmitError('');
      
      const token = getToken('buyer');
      if (!token) {
        throw new Error('Please log in as a buyer to request document access');
      }
      
      // Create a payload for the message
      const payload = {
        message: requestMessage || ""
      };
      
      console.log('Sending document request with data:', payload);
      console.log('To endpoint:', `http://localhost:8000/buyer/request-documents/${propertyId}`);
      
      const response = await fetch(`http://localhost:8000/buyer/request-documents/${propertyId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response text:', errorText);
        
        let errorDetail = 'Failed to submit request';
        try {
          const errorData = JSON.parse(errorText);
          errorDetail = errorData.detail || errorData.message || errorDetail;
        } catch (parseError) {
          console.error('Could not parse error response as JSON:', parseError);
        }
        
        throw new Error(errorDetail);
      }
      
      const data = await response.json();
      console.log('Document request response:', data);
      
      // After successful submission, refresh document access status
      setSubmitSuccess(true);
      setShowRequestForm(false);
      setRequestMessage('');
      
      // Wait a moment then check if document access status has changed
      setTimeout(() => {
        checkDocumentAccess();
      }, 1000);
      
    } catch (err) {
      console.error('Error submitting document request:', err);
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelRequest = () => {
    setShowRequestForm(false);
    setRequestMessage('');
  };

  const handleContactSeller = () => {
    if (property && property.seller_contact) {
      setNotification({
        type: 'success',
        message: `Contact the seller at: ${property.seller_contact}`
      });

      // Clear notification after 10 seconds
      setTimeout(() => {
        setNotification(null);
      }, 10000);
    } else {
      setNotification({
        type: 'error',
        message: 'Seller contact information is not available.'
      });

      // Clear error notification after 5 seconds
      setTimeout(() => {
        setNotification(null);
      }, 5000);
    }
  };

  // Render document section with visibility based on access
  const renderDocumentsSection = () => {
    // If checking access, show loading
    if (checkingAccess) {
      return (
        <div className="documents-list">
          <div className="loading-spinner-small"></div>
          <p>Checking document access...</p>
        </div>
      );
    }

    // If access has been granted
    if (documentAccess && documentAccess.has_access) {
      const handleDocumentClick = (index, event) => {
        event.preventDefault();
        
        const token = getToken('buyer');
        if (!token) {
          setNotification({
            type: 'error',
            message: 'You need to be logged in as a buyer to download documents'
          });
          return;
        }
        
        // Check download limits
        const limits = documentAccess.document_limits || [];
        const docLimit = limits.find(limit => limit.document_index === index);
        
        if (docLimit && docLimit.remaining_downloads <= 0) {
          // Show notification that downloads are exhausted
          setNotification({
            type: 'error',
            message: 'Download limit reached for this document. Contact seller for more access.'
          });
          return;
        }
        
        // Create URL with token parameter
        const downloadUrl = `http://localhost:8000/buyer/property-document/${propertyId}/${index}?token=${encodeURIComponent(token)}`;
        
        // Open in a new tab to trigger a direct download
        window.open(downloadUrl, '_blank');
        
        // Show a notification about the download
        setNotification({
          type: 'info',
          message: 'Document download started...'
        });
        
        // Clear notification after 3 seconds
        setTimeout(() => {
          setNotification(null);
        }, 3000);
        
        // Refresh document access data after download to update counters
        setTimeout(() => {
          checkDocumentAccess();
        }, 2000);
      };
      
      // Helper function to get download limits for a document
      const getDocumentLimit = (index) => {
        const limits = documentAccess.document_limits || [];
        return limits.find(limit => limit.document_index === index) || {
          max_downloads: 3,
          remaining_downloads: 3,
          download_count: 0
        };
      };
      
      return (
        <div className="documents-list">
          <div className="success-message">
            You have access to view these documents until {new Date(documentAccess.access_expires_on).toLocaleString()}
          </div>
          <div className="document-items">
            {documentAccess.documents.map((doc, index) => {
              const docLimit = getDocumentLimit(index);
              const isLimitReached = docLimit.remaining_downloads <= 0;
              
              return (
              <div 
                key={index} 
                  className={`document-item ${isLimitReached ? 'limit-reached' : ''}`}
                onClick={(e) => handleDocumentClick(index, e)}
                  style={{ cursor: isLimitReached ? 'not-allowed' : 'pointer' }}
              >
                <div className="document-icon">📄</div>
                <div className="document-info">
                  <span className="document-title">{doc.type || `Document ${index + 1}`}</span>
                  <span className="document-filename">{doc.filename || `document-${index + 1}`}</span>
                    <span className={`download-limit-badge ${isLimitReached ? 'limit-reached' : ''}`}>
                      {isLimitReached ? 
                        'Download limit reached' : 
                        `${docLimit.remaining_downloads}/${docLimit.max_downloads} downloads remaining`}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      );
    }

    // If request was just submitted successfully
    if (submitSuccess) {
      return (
        <div className="success-message">
          Request submitted successfully.
        </div>
      );
    }

    // If showing request form
    if (showRequestForm) {
      return (
        <div className="document-request-form">
          <form onSubmit={handleSubmitRequest}>
            <div className="form-group">
              <textarea
                id="requestMessage"
                className="form-control"
                value={requestMessage}
                onChange={(e) => setRequestMessage(e.target.value)}
                placeholder="Why do you need access to documents? (Optional)"
                rows={2}
              ></textarea>
            </div>
            
            {submitError && (
              <div className="error-message">
                <p>{submitError}</p>
                {submitError.includes('buyer') && (
                  <button 
                    type="button"
                    onClick={() => navigate('/login/buyer')} 
                    className="btn login-btn"
                  >
                    Log in as Buyer
                  </button>
                )}
              </div>
            )}
            
            <div className="form-actions">
              <button 
                type="button" 
                className="btn btn-cancel"
                onClick={handleCancelRequest}
                disabled={submitting}
              >
                Cancel
              </button>
              <button 
                type="submit" 
                className="btn btn-submit"
                disabled={submitting}
              >
                {submitting ? 'Submitting...' : 'Submit'}
              </button>
            </div>
          </form>
        </div>
      );
    }

    // Default state - show document count and request button
    return (
      <div className="documents-list">
        <p>{property.documents && property.documents.length > 0 ? 
          "Document access is restricted. Please request access." : 
          "No documents available for this property."}</p>
      </div>
    );
  };

  if (loading) return (
    <div className="loading-container">
      <div className="loading-spinner"></div>
      <p>Loading property details...</p>
    </div>
  );
  
  if (error) return (
    <div className="error-container">
      <div className="error-message">
        <h3>Error Loading Property</h3>
        <p>{error}</p>
        {error.includes('buyer') ? (
          <div className="login-info">
            <p>You need to be logged in as a buyer to request documents.</p>
            <button 
              onClick={() => navigate('/login/buyer')} 
              className="btn btn-primary"
            >
              Log in as Buyer
            </button>
          </div>
        ) : (
          <button onClick={handleGoBack} className="btn btn-primary">
            Back to Properties
          </button>
        )}
      </div>
    </div>
  );

  if (!property) return null;

  // Check if property has images
  const hasImages = property.images && Array.isArray(property.images) && property.images.length > 0;
  console.log('Property has images:', hasImages, property.images?.length);
  
  // Safely get the main image
  const mainImageUrl = hasImages && selectedImageIndex < property.images.length 
    ? getPublicImageUrl(selectedImageIndex) // Use the public URL for main image too
    : '/placeholder.jpg';
  
  console.log('Main image URL:', mainImageUrl);

  return (
    <div className="property-details-page">
      <header>
        <div className="container header-container full-width">
          <div className="header-left">
            <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign Logo" className="logo-image" />
          </div>
          
          <div className="header-center">
            <h1>Property Details</h1>
          </div>
          
          <div className="header-right">
            {/* Empty div to maintain the header layout */}
          </div>
        </div>
      </header>

      <main className="container full-width">
        {notification && (
          <div className={`notification ${notification.type}`}>
            <span className="notification-message">{notification.message}</span>
            <button 
              className="notification-close"
              onClick={() => setNotification(null)}
            >
              ×
            </button>
          </div>
        )}

        <div className="property-content">
          {/* Property images section */}
          <div className="property-images-section">
            <div className="main-image-container">
              <img 
                src={mainImageUrl} 
                alt={property.address || "Property"} 
                className="main-property-image"
                onError={handleImageError}
              />
            </div>
            
            {hasImages && property.images.length > 1 && (
              <div className="thumbnail-gallery">
                {property.images.map((image, index) => (
                  <div 
                    key={index} 
                    className={`thumbnail ${index === selectedImageIndex ? 'selected' : ''}`}
                    onClick={() => handleImageClick(index)}
                  >
                    <img 
                      src={getPublicImageUrl(index)} 
                      alt={`Property ${index + 1}`}
                      onError={handleImageError}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* Property info section */}
          <div className="property-info-section">
            <h2>{property.address || 'Unknown Location'}</h2>
            
            <div className="property-reference">
              <span>Survey Number: {property.survey_number || property.id}</span>
            </div>
            
            <div className="property-details-grid compact">
              <div className="property-detail-item">
                <span className="detail-label">Survey Number</span>
                <span className="detail-value">{property.survey_number || 'Not specified'}</span>
              </div>
              
              <div className="property-detail-item">
                <span className="detail-label">Plot Size</span>
                <span className="detail-value">{property.plot_size || 'N/A'} sq.ft</span>
              </div>
              
              <div className="property-detail-item">
                <span className="detail-label">Price</span>
                <span className="detail-value">₹{property.price ? property.price.toLocaleString() : '0'}</span>
              </div>
              
              <div className="property-detail-item">
                <span className="detail-label">Address</span>
                <span className="detail-value">{property.address || 'Not specified'}</span>
              </div>
            </div>
            
            {/* Seller Information and Document Request Section */}
            <div className="info-documents-container">
              {/* Seller Information Section */}
              <div className="seller-info-section compact">
                <h3>Seller Information</h3>
                <div className="seller-details">
                  <div className="seller-detail-item">
                    <span className="detail-label">Seller Name</span>
                    <span className="detail-value">{property.seller_name || 'Not available'}</span>
                  </div>
                  
                  <div className="property-actions">
                    <button 
                      className="action-button contact-button"
                      onClick={handleContactSeller}
                    >
                      Contact Seller
                    </button>
                  </div>
                </div>
              </div>
              
              {/* Document Request Section */}
              <div className="property-documents compact">
                <div className="documents-header">
                  <h3>Property Documents</h3>
                  
                  {(!submitSuccess && !showRequestForm && (!documentAccess || !documentAccess.has_access)) && (
                    <button 
                      className="request-document-btn"
                      onClick={handleRequestDocuments}
                    >
                      Request Documents
                    </button>
                  )}
                </div>
                
                {renderDocumentsSection()}
              </div>
            </div>
            
            {/* Add Legal Verification Section */}
            {documentAccess && documentAccess.has_access && (
              <LawyerVerification 
                propertyId={propertyId}
                onVerificationUpdated={() => {
                  // Refresh document access status if needed
                  checkDocumentAccess();
                }}
              />
            )}
            
            <div className="status-timestamp-container">
              <div className="property-status">
                <span className="status-label">Status</span>
                <span className={`status-badge ${property.status?.toLowerCase()}`}>
                  {property.status || 'Not specified'}
                </span>
              </div>
              
              <div className="property-timestamp">
                <span className="timestamp-label">Listed on</span>
                <span className="timestamp-value">
                  {property.created_at 
                    ? formatDate(property.created_at) 
                    : 'Unknown date'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer>
        <div className="container full-width">
          <p>&copy; 2025 SureSign - Online Property Registration Portal. All Rights Reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default BuyerPropertyDetails; 