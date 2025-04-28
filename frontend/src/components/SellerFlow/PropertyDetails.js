import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './PropertyDetails.css';
import { getToken, clearAuthData } from '../../utils/authUtils';

function PropertyDetails() {
  const { propertyId } = useParams();
  const navigate = useNavigate();
  const [property, setProperty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [documentsVisible, setDocumentsVisible] = useState(false);
  const [notification, setNotification] = useState({ message: '', type: '' });
  const [isDownloading, setIsDownloading] = useState(false);

  // Function to show notification
  const showNotification = (message, type = 'info') => {
    setNotification({ message, type });
    // Auto-clear notification after 5 seconds
    setTimeout(() => {
      setNotification({ message: '', type: '' });
    }, 5000);
  };

  useEffect(() => {
    const fetchPropertyDetails = async () => {
      try {
        setLoading(true);
        const token = getToken('seller');
        
        if (!token) {
          console.error('No authentication token found');
          navigate('/login/seller');
          return;
        }

        console.log('Using token for API requests:', token ? 'Token found' : 'No token');

        // Get seller data for user info
        const sellerResponse = await fetch('http://localhost:8000/seller/get-seller', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!sellerResponse.ok) {
          if (sellerResponse.status === 401) {
            // Token has expired
            console.error('Token has expired');
            clearAuthData('seller');
            navigate('/login/seller');
            return;
          }
          console.error('Failed to fetch seller data:', sellerResponse.status);
          throw new Error('Failed to fetch seller data');
        }

        const sellerData = await sellerResponse.json();
        console.log('Seller data:', sellerData);
        
        // Directly fetch the property details from the property endpoint
        const propertyResponse = await fetch(`http://localhost:8000/seller/property/${propertyId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!propertyResponse.ok) {
          if (propertyResponse.status === 401) {
            // Token has expired
            console.error('Token has expired');
            clearAuthData('seller');
            navigate('/login/seller');
            return;
          }
          console.error('Failed to fetch property details:', propertyResponse.status);
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
  }, [propertyId, navigate]);

  // Add a side effect to ensure document visibility state is always respected
  useEffect(() => {
    console.log('Document visibility state changed to:', documentsVisible);
    
    // Target the documents list directly based on state
    const documentsList = document.querySelector('.documents-list');
    if (documentsList) {
      if (documentsVisible) {
        documentsList.classList.remove('blurred');
        console.log('Removed blurred class');
      } else {
        documentsList.classList.add('blurred');
        console.log('Added blurred class');
      }
    } else {
      console.log('Could not find documents list element');
    }
  }, [documentsVisible]);

  // Add debug logging for component state
  useEffect(() => {
    console.log('Selected Image Index:', selectedImageIndex);
    console.log('Documents Visible:', documentsVisible);
  }, [selectedImageIndex, documentsVisible]);

  const handleGoBack = () => {
    navigate('/list-properties');
  };

  const handleImageClick = (index) => {
    console.log('Image clicked:', index);
    setSelectedImageIndex(index);
  };
  
  const getPublicImageUrl = (index) => {
    // Use the public-property-image endpoint that doesn't require authentication
    console.log(`Generating public image URL for property ${propertyId}, index ${index}`);
    return `http://localhost:8000/seller/public-property-image/${propertyId}/${index}`;
  };

  // Toggle document visibility for the property documents section
  const toggleDocumentVisibility = async () => {
    console.log('Toggle document visibility clicked');
    console.log('Current visibility state:', documentsVisible);
    
    try {
      setDocumentsVisible(!documentsVisible);
    } catch (err) {
      console.error('Error toggling document visibility:', err);
      setError('Failed to toggle document visibility');
    }
  };

  // Update document download to handle token expiration
  const handleDocumentDownload = async (doc, index) => {
    if (!documentsVisible) {
      console.log('Document access blocked - toggle visibility first');
      return;
    }
    
    setIsDownloading(true);
    showNotification('Starting document download...', 'info');
    
    try {
      const token = getToken('seller');
      if (!token) {
        console.error('No token found for document download');
        showNotification('Authentication error. Please log in again.', 'error');
        setIsDownloading(false);
        return;
      }

      // Get the document name
      const filename = doc.document_name || `document_${index}.pdf`;
      
      // Create the download URL using the new endpoint
      const downloadUrl = `http://localhost:8000/seller/property/${propertyId}/document/${index}/download`;
      
      showNotification(`Downloading ${filename}...`, 'info');
      
      // Fetch the document with authorization header
      const response = await fetch(downloadUrl, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        if (response.status === 401) {
          console.error('Token has expired');
          showNotification('Your session has expired. Please log in again.', 'error');
          clearAuthData('seller');
          navigate('/login/seller');
          return;
        }
        
        if (response.status === 404) {
          console.error('Document not found');
          showNotification('Document not found. Attempting recovery...', 'warning');
          
          // Try the recovery endpoint
          console.log('Attempting document recovery...');
          
          const recoveryUrl = `http://localhost:8000/seller/property/${propertyId}/document/${index}/recover`;
          const recoveryResponse = await fetch(recoveryUrl, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });
          
          if (!recoveryResponse.ok) {
            throw new Error('Failed to recover and download document');
          }
          
          showNotification('Document recovered successfully!', 'success');
          
          // Get the blob from the recovery response
          const blob = await recoveryResponse.blob();
          
          // Create a download link
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          
          // Cleanup
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
          setIsDownloading(false);
          return;
        }
        
        throw new Error(`Failed to download document: ${response.status}`);
      }

      // Get the blob from the response
      const blob = await response.blob();
      
      // Create a download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      
      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      showNotification(`Successfully downloaded ${filename}`, 'success');
      
    } catch (err) {
      console.error('Error downloading document:', err);
      showNotification(`Download failed: ${err.message}`, 'error');
      setError('Failed to download document');
    } finally {
      setIsDownloading(false);
    }
  };

  const getDocumentTypeLabel = (type) => {
    // Handle different document formats
    if (typeof type === 'string') {
      return type;
    } else if (typeof type === 'object' && type !== null) {
      // Handle if type is in a nested property
      return type.name || type.label || type.type || 'Document';
    }
    return 'Document';
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

  // Improved image error handler with debug logging
  const handleImageError = (e) => {
    console.log('Image loading error in PropertyDetails');
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

  // Update the document item render to use the new download handler
  const renderDocumentItem = (doc, index) => {
    const filename = doc.document_name || `document_${index}.pdf`;
    const docType = getDocumentTypeLabel(doc.type || 'Document');
    
    // Determine document icon based on file extension
    let documentIcon = '📄';
    if (filename.toLowerCase().endsWith('.pdf')) {
      documentIcon = '📑';
    } else if (filename.toLowerCase().endsWith('.jpg') || 
               filename.toLowerCase().endsWith('.jpeg') || 
               filename.toLowerCase().endsWith('.png')) {
      documentIcon = '🖼️';
    } else if (filename.toLowerCase().endsWith('.docx') || 
               filename.toLowerCase().endsWith('.doc')) {
      documentIcon = '📝';
    }
    
    return (
      <div key={index} className="document-item">
        <div className="document-icon">
          <i className="document-type-icon">{documentIcon}</i>
        </div>
        <div className="document-info">
          <span className="document-title">{docType}</span>
          <span className="document-filename">{filename}</span>
        </div>
        <button 
          className={`download-btn ${isDownloading ? 'loading' : ''}`}
          disabled={!documentsVisible || isDownloading}
          onClick={() => handleDocumentDownload(doc, index)}
          title="Download original document from secure storage"
        >
          Download Original
        </button>
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
        <button onClick={handleGoBack} className="btn btn-primary">
          Back to Properties
        </button>
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

      {/* Notification component */}
      {notification.message && (
        <div className={`notification ${notification.type}`}>
          <span className="notification-message">{notification.message}</span>
          <button 
            className="close-notification" 
            onClick={() => setNotification({ message: '', type: '' })}
          >
            ×
          </button>
        </div>
      )}

      <main className="container full-width">
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
                  <button 
                    key={index} 
                    className={`thumbnail ${index === selectedImageIndex ? 'selected' : ''}`}
                    onClick={() => handleImageClick(index)}
                    type="button"
                  >
                    <img 
                      src={getPublicImageUrl(index)} 
                      alt={`Property view ${index + 1}`}
                      onError={handleImageError}
                    />
                  </button>
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
            
            <div className="property-details-grid">
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
                <span className="detail-value">₹{property.price || '0'}</span>
              </div>
              
              <div className="property-detail-item">
                <span className="detail-label">Address</span>
                <span className="detail-value">{property.address || 'Not specified'}</span>
              </div>
            </div>
            
            {property.documents && property.documents.length > 0 && (
              <div className="property-documents">
                <div className="documents-header">
                  <h3>Property Documents</h3>
                  <button 
                    type="button"
                    className={`toggle-visibility-btn ${documentsVisible ? 'visible' : ''}`}
                    onClick={toggleDocumentVisibility}
                    style={{ cursor: 'pointer', zIndex: 1000 }}
                  >
                    <svg 
                      xmlns="http://www.w3.org/2000/svg" 
                      width="24" 
                      height="24" 
                      viewBox="0 0 24 24" 
                      fill="none" 
                      stroke="currentColor" 
                      strokeWidth="2" 
                      strokeLinecap="round" 
                      strokeLinejoin="round"
                      style={{ pointerEvents: 'none' }}
                    >
                      {documentsVisible ? (
                        <>
                          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                          <circle cx="12" cy="12" r="3" />
                        </>
                      ) : (
                        <>
                          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                          <line x1="1" y1="1" x2="23" y2="23" />
                        </>
                      )}
                    </svg>
                  </button>
                </div>
                
                <div className={`documents-list ${documentsVisible ? '' : 'blurred'}`}>
                  {property.documents.map((doc, index) => renderDocumentItem(doc, index))}
                </div>
              </div>
            )}
            
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
      </main>

      <footer>
        <div className="container full-width">
          <p>&copy; 2025 Online Property Registration Portal. All Rights Reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default PropertyDetails; 