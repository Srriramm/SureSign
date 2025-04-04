import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './PropertyDetails.css';

function PropertyDetails() {
  const { propertyId } = useParams();
  const navigate = useNavigate();
  const [property, setProperty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [sellerData, setSellerData] = useState(null);
  const [documentsVisible, setDocumentsVisible] = useState(false);
  const [documentRequests, setDocumentRequests] = useState([]);
  const [unlockingDocuments, setUnlockingDocuments] = useState(false);

  useEffect(() => {
    const fetchPropertyDetails = async () => {
      try {
        setLoading(true);
        // Check for both generic token and seller-specific token
        const token = localStorage.getItem('token') || localStorage.getItem('seller_token');
        
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
          console.error('Failed to fetch seller data:', sellerResponse.status);
          throw new Error('Failed to fetch seller data');
        }

        const sellerData = await sellerResponse.json();
        console.log('Seller data:', sellerData);
        setSellerData(sellerData);
        
        // Directly fetch the property details from the property endpoint
        const propertyResponse = await fetch(`http://localhost:8000/seller/property/${propertyId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!propertyResponse.ok) {
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

  const handleGoBack = () => {
    navigate('/list-properties');
  };

  const handleImageClick = (index) => {
    setSelectedImageIndex(index);
  };

  const getImageUrl = (image, index) => {
    // Add debugging to understand what image data is available
    console.log(`Getting image URL for index ${index}:`, image);
    
    // Use the public-property-image endpoint for better compatibility
    return `http://localhost:8000/seller/public-property-image/${propertyId}/${index}`;
  };
  
  const getPublicImageUrl = (index) => {
    // Use the public-property-image endpoint that doesn't require authentication
    console.log(`Generating public image URL for property ${propertyId}, index ${index}`);
    return `http://localhost:8000/seller/public-property-image/${propertyId}/${index}`;
  };

  const getDocumentUrl = (doc, index) => {
    // Log document data for debugging
    console.log('Document data:', doc, 'at index:', index);
    
    // Handle different data formats
    if (!doc) {
      console.error('Document is undefined or null');
      return '#'; // Return a placeholder URL that won't cause navigation
    }
    
    // Get token for authentication
    const token = localStorage.getItem('token') || localStorage.getItem('seller_token');
    console.log('Token for document download:', token ? 'Token found' : 'No token');
    
    if (!token) {
      console.error('No token found for document download');
      return '#';
    }
    
    // Generate the document URL with the token as a query parameter
    // Make sure to encode the token properly and use a direct URL format
    return `http://localhost:8000/seller/property-document/${propertyId}/${index}?token=${encodeURIComponent(token)}`;
  };

  // Add a direct download handler to bypass potential URL issues
  const handleDocumentDownload = async (doc, index, e) => {
    e.preventDefault();
    console.log('Handling direct document download for index:', index);
    
    if (!documentsVisible) {
      console.log('Document access blocked - toggle visibility first');
      return;
    }
    
    try {
      // Get token for authentication
      const token = localStorage.getItem('token') || localStorage.getItem('seller_token');
      
      if (!token) {
        console.error('No token found for document download');
        return;
      }
      
      // Get document type and potential filename for proper download
      const docType = doc.type || doc.document_type || 'document';
      let filename = 'property-document.pdf'; // Default fallback
      
      if (typeof doc.filename === 'string' && doc.filename) {
        filename = doc.filename.split('_').pop();
      } else if (typeof doc === 'object' && doc.url && typeof doc.url === 'string') {
        filename = doc.url.split('/').pop().split('?')[0];
      } else {
        filename = `property-${propertyId}-document-${index}.pdf`;
      }
      
      console.log(`Attempting to download document: ${filename}`);
      
      // For Word documents, we need a special approach
      if (filename.toLowerCase().endsWith('.docx') || filename.toLowerCase().endsWith('.doc')) {
        // Create direct link to a new page
        const timestamp = new Date().getTime();
        
        // Create a simplified document viewer page instead of direct download
        const viewerUrl = `/document-viewer?id=${propertyId}&index=${index}&token=${encodeURIComponent(token)}&type=docx`;
        
        // Or use the direct API endpoint for viewing in browser
        const directApiUrl = `http://localhost:8000/seller/property-document/${propertyId}/${index}?token=${encodeURIComponent(token)}&filename=${encodeURIComponent(filename)}&t=${timestamp}&view=true`;
        
        // You can copy the document content to a new tab for viewing
        console.log('Opening document in viewer:', directApiUrl);
        window.open(directApiUrl, '_blank');
      } else {
        // For other document types, use the iframe approach
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        document.body.appendChild(iframe);
        
        // Create a form within the iframe
        iframe.contentWindow.document.open();
        iframe.contentWindow.document.write(`
          <form method="GET" action="http://localhost:8000/seller/property-document/${propertyId}/${index}" target="_blank">
            <input type="hidden" name="token" value="${token}" />
            <input type="hidden" name="filename" value="${filename}" />
          </form>
        `);
        iframe.contentWindow.document.close();
        
        // Submit the form
        const form = iframe.contentWindow.document.querySelector('form');
        form.submit();
        
        // Remove the iframe after a short delay
        setTimeout(() => {
          document.body.removeChild(iframe);
        }, 1000);
      }
    } catch (error) {
      console.error('Error downloading document:', error);
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

  const toggleDocumentVisibility = () => {
    console.log('Toggle document visibility called. Current state:', documentsVisible);
    
    // Force the toggle regardless of current state
    const newState = !documentsVisible;
    console.log('Setting documents visible to:', newState);
    
    // Always set the unlocking indicator for feedback
    if (newState) {
      setUnlockingDocuments(true);
      setTimeout(() => {
        setUnlockingDocuments(false);
      }, 800);
    }
    
    // Update state directly
    setDocumentsVisible(newState);
    
    // Debug log after state update
    console.log('Documents visibility updated to:', newState);
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

      <main className="container full-width">
        <div className="property-content">
          {/* Property images section */}
          <div className="property-images-section">
            <div className="main-image-container">
              <img 
                src={mainImageUrl} 
                alt={property.location || property.area || "Property"} 
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
            <h2>{property.location || property.area || 'Unknown Location'}</h2>
            
            <div className="property-reference">
              <span>Reference #: {property.reference_number || property.id || property._id}</span>
            </div>
            
            <div className="property-details-grid">
              <div className="property-detail-item">
                <span className="detail-label">Property Type</span>
                <span className="detail-value">{property.property_type || 'Not specified'}</span>
              </div>
              
              <div className="property-detail-item">
                <span className="detail-label">Area</span>
                <span className="detail-value">{property.square_feet || 'N/A'} sq.ft</span>
              </div>
              
              <div className="property-detail-item">
                <span className="detail-label">Price</span>
                <span className="detail-value">₹{property.price || '0'}/sq.ft</span>
              </div>
              
              <div className="property-detail-item">
                <span className="detail-label">Area/Location</span>
                <span className="detail-value">{property.area || 'Not specified'}</span>
              </div>
              
              <div className="property-detail-item full-width">
                <span className="detail-label">Description</span>
                <span className="detail-value description">{property.description || 'No description available'}</span>
              </div>
            </div>
            
            {property.documents && property.documents.length > 0 && (
              <div className="property-documents">
                <div className="documents-header">
                  <h3>Property Documents</h3>
                  <div className="toggle-button-container">
                    <button 
                      className={`toggle-visibility-btn ${documentsVisible ? 'visible' : ''}`}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('Eye button clicked');
                        toggleDocumentVisibility();
                      }}
                      aria-label={documentsVisible ? "Hide Documents" : "Show Documents"}
                      title={documentsVisible ? "Click to Hide Documents" : "Click to View Documents"}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        {documentsVisible ? (
                          <>
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                          </>
                        ) : (
                          <>
                            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                            <line x1="1" y1="1" x2="23" y2="23"></line>
                          </>
                        )}
                      </svg>
                      {unlockingDocuments && <span className="spinner-dots"></span>}
                    </button>
                  </div>
                </div>
                
                {/* Fallback text button in case the eye icon doesn't work */}
                <button 
                  className="fallback-toggle-btn"
                  onClick={toggleDocumentVisibility}
                >
                  {documentsVisible ? "Hide Documents" : "Show Documents"}
                </button>
                
                <div className={`documents-list ${documentsVisible ? '' : 'blurred'}`}>
                  {property.documents.map((doc, index) => {
                    // Get original filename and extract the extension
                    let filename = '';
                    let fileExtension = '.docx'; // Default to docx as it's common
                    
                    if (typeof doc.filename === 'string' && doc.filename) {
                      // Extract just the filename portion without path or extra data
                      const lastPart = doc.filename.split('_').pop();
                      filename = lastPart.replace(/[\[\]]/g, '');
                      
                      // Get extension if it exists
                      if (filename.includes('.')) {
                        fileExtension = '.' + filename.split('.').pop();
                      }
                    } else if (typeof doc === 'object' && doc.url && typeof doc.url === 'string') {
                      const urlParts = doc.url.split('/').pop().split('?')[0];
                      filename = urlParts;
                      
                      // Get extension if it exists
                      if (filename.includes('.')) {
                        fileExtension = '.' + filename.split('.').pop();
                      }
                    } else {
                      // Create a filename based on document type if available
                      const docType = doc.type || 'document';
                      filename = `${docType.toLowerCase().replace(/\s+/g, '-')}-${index}${fileExtension}`;
                    }
                    
                    // Ensure filename has the correct extension
                    if (!filename.toLowerCase().endsWith(fileExtension.toLowerCase())) {
                      filename = `${filename}${fileExtension}`;
                    }
                    
                    // Get token for auth
                    const token = localStorage.getItem('token') || localStorage.getItem('seller_token');
                    
                    // Determine document type icon
                    let docIcon = '📄';
                    if (fileExtension.toLowerCase() === '.pdf') {
                      docIcon = '📕';
                    } else if (fileExtension.toLowerCase() === '.doc' || fileExtension.toLowerCase() === '.docx') {
                      docIcon = '📝';
                    }
                    
                    return (
                      <div key={index} className="document-item">
                        <div className="document-icon">
                          <i className="document-type-icon">{docIcon}</i>
                        </div>
                        <div className="document-info">
                          <span className="document-title">{getDocumentTypeLabel(doc.type || doc.document_type)}</span>
                          <span className="document-filename">{filename}</span>
                        </div>
                        <button 
                          className="download-btn"
                          disabled={!documentsVisible}
                          onClick={(e) => {
                            if (!documentsVisible) {
                              console.log('Document access blocked - toggle visibility first');
                              return;
                            }
                            
                            // Show options to the user
                            const downloadOptions = document.createElement('div');
                            downloadOptions.className = 'download-options';
                            downloadOptions.innerHTML = `
                              <div class="download-options-inner">
                                <h4>Document Access Options</h4>
                                <p>Select how you want to access the document:</p>
                                <button class="download-option-btn original">Download Original</button>
                                <button class="download-option-btn verified">Download with Verification</button>
                                <button class="download-option-btn view">View in Browser</button>
                                <button class="download-option-btn cancel">Cancel</button>
                              </div>
                            `;
                            
                            // Style the options modal
                            const style = document.createElement('style');
                            style.textContent = `
                              .download-options {
                                position: fixed;
                                top: 0;
                                left: 0;
                                right: 0;
                                bottom: 0;
                                background: rgba(0,0,0,0.7);
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                z-index: 1000;
                              }
                              .download-options-inner {
                                background: white;
                                padding: 20px;
                                border-radius: 8px;
                                max-width: 400px;
                                width: 100%;
                                text-align: center;
                              }
                              .download-option-btn {
                                display: block;
                                width: 100%;
                                padding: 10px;
                                margin: 10px 0;
                                border: none;
                                border-radius: 4px;
                                cursor: pointer;
                              }
                              .download-option-btn.original {
                                background: #2563eb;
                                color: white;
                              }
                              .download-option-btn.verified {
                                background: #10b981;
                                color: white;
                              }
                              .download-option-btn.view {
                                background: #9ca3af;
                                color: white;
                              }
                              .download-option-btn.cancel {
                                background: #f3f4f6;
                                color: #111827;
                              }
                            `;
                            
                            document.head.appendChild(style);
                            document.body.appendChild(downloadOptions);
                            
                            // Handle option clicks
                            const originalBtn = downloadOptions.querySelector('.original');
                            const verifiedBtn = downloadOptions.querySelector('.verified');
                            const viewBtn = downloadOptions.querySelector('.view');
                            const cancelBtn = downloadOptions.querySelector('.cancel');
                            
                            // Download original document (for admin/debug use)
                            originalBtn.addEventListener('click', () => {
                              const timestamp = new Date().getTime();
                              const url = `http://localhost:8000/seller/property-document/${propertyId}/${index}?token=${encodeURIComponent(token)}&filename=${encodeURIComponent(filename)}&t=${timestamp}&raw=true`;
                              
                              const link = document.createElement('a');
                              link.href = url;
                              link.setAttribute('download', filename);
                              document.body.appendChild(link);
                              link.click();
                              document.body.removeChild(link);
                              
                              document.body.removeChild(downloadOptions);
                              document.head.removeChild(style);
                            });
                            
                            // Download document with verification certificate
                            verifiedBtn.addEventListener('click', () => {
                              const timestamp = new Date().getTime();
                              const url = `http://localhost:8000/seller/property-document/${propertyId}/${index}?token=${encodeURIComponent(token)}&filename=${encodeURIComponent(filename)}&t=${timestamp}&verified=true`;
                              
                              const link = document.createElement('a');
                              link.href = url;
                              link.setAttribute('download', filename);
                              document.body.appendChild(link);
                              link.click();
                              document.body.removeChild(link);
                              
                              document.body.removeChild(downloadOptions);
                              document.head.removeChild(style);
                            });
                            
                            viewBtn.addEventListener('click', () => {
                              // View in browser option
                              const timestamp = new Date().getTime();
                              const url = `http://localhost:8000/seller/property-document/${propertyId}/${index}?token=${encodeURIComponent(token)}&filename=${encodeURIComponent(filename)}&t=${timestamp}&view=true`;
                              
                              window.open(url, '_blank');
                              
                              // Remove the options
                              document.body.removeChild(downloadOptions);
                              document.head.removeChild(style);
                            });
                            
                            cancelBtn.addEventListener('click', () => {
                              // Remove the options
                              document.body.removeChild(downloadOptions);
                              document.head.removeChild(style);
                            });
                          }}
                        >
                          Download
                        </button>
                      </div>
                    );
                  })}
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