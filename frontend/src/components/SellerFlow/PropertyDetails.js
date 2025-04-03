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

  useEffect(() => {
    const fetchPropertyDetails = async () => {
      try {
        setLoading(true);
        const token = localStorage.getItem('token');
        if (!token) {
          navigate('/login');
          return;
        }

        // Get seller data for user info
        const sellerResponse = await fetch('http://localhost:8000/seller/get-seller', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!sellerResponse.ok) {
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
    
    // Use the seller route for document access
    return `http://localhost:8000/seller/property-document/${propertyId}/${index}`;
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
            <h1>Property Marketplace</h1>
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
                <h3>Documents</h3>
                <div className="documents-list">
                  {property.documents.map((doc, index) => {
                    console.log('Rendering document:', doc);
                    return (
                      <a 
                        key={index} 
                        href={getDocumentUrl(doc, index)} 
                        className="document-item"
                        target="_blank" 
                        rel="noopener noreferrer"
                      >
                        <div className="document-icon">
                          <i className="document-type-icon">📄</i>
                        </div>
                        <div className="document-info">
                          <span className="document-title">{getDocumentTypeLabel(doc.type)}</span>
                          <span className="document-filename">
                            {typeof doc.filename === 'string' && doc.filename 
                              ? doc.filename.split('_').pop() 
                              : typeof doc === 'object' && doc.url && typeof doc.url === 'string'
                                ? doc.url.split('/').pop().split('?')[0]
                                : 'Document'}
                          </span>
                        </div>
                      </a>
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