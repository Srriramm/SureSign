import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getToken } from '../../utils/authUtils';
import './ListProperties.css';

function ListProperties() {
  const [sellerData, setSellerData] = useState(null);
  const [properties, setProperties] = useState([]);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showRequestsMenu, setShowRequestsMenu] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selfieUrl, setSelfieUrl] = useState(null);
  const [documentRequests, setDocumentRequests] = useState([]);
  const [requestsLoading, setRequestsLoading] = useState(false);
  const [notification, setNotification] = useState(null);
  const profileRef = useRef(null);
  const requestsRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Add click outside handler
    function handleClickOutside(event) {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setShowProfileMenu(false);
      }
      if (requestsRef.current && !requestsRef.current.contains(event.target)) {
        setShowRequestsMenu(false);
      }
    }

    // Bind the event listener
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      // Unbind the event listener on cleanup
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const token = getToken('seller');
        if (!token) {
          navigate('/login/seller');
          return;
        }

        // Get seller profile
        const response = await fetch('http://localhost:8000/seller/get-seller', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch seller data');
        }
        
        const data = await response.json();
        console.log('Seller data:', data);
        setSellerData(data);
        
        // In the new structure, properties are always fetched from the dedicated API
        // as they're stored in a separate collection
        const propsResponse = await fetch('http://localhost:8000/seller/properties', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!propsResponse.ok) {
          throw new Error('Failed to fetch properties');
        }
        
        const propsData = await propsResponse.json();
        console.log('Properties data from API:', propsData);
        
        // Add additional processing for property data
        if (Array.isArray(propsData)) {
          // Log each property's key fields to help debug
          propsData.forEach((property, index) => {
            console.log(`Property ${index} (${property.id}):`, {
              address: property.address,
              location: property.location,
              area: property.area,
              survey_number: property.survey_number,
              plot_size: property.plot_size,
              square_feet: property.square_feet,
              price: property.price,
              status: property.status
            });
          });
          
          // Sort properties by date (most recent first)
          propsData.sort((a, b) => {
            const dateA = new Date(a.created_at || 0);
            const dateB = new Date(b.created_at || 0);
            return dateB - dateA;
          });
        }
        
        setProperties(propsData);
        
        // Fetch document requests
        fetchDocumentRequests();
        
        setLoading(false);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError(err.message);
        setLoading(false);
      }
    };
    
    fetchData();
  }, [navigate]);
  
  const fetchDocumentRequests = async () => {
    try {
      setRequestsLoading(true);
      const token = getToken('seller');
      if (!token) return;
      
      const response = await fetch('http://localhost:8000/seller/document-requests', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch document requests');
      }
      
      const data = await response.json();
      console.log('Document requests:', data);
      
      // Transform the data to include property details
      if (Array.isArray(data)) {
        const transformedRequests = await Promise.all(data.map(async (request) => {
          // Fetch property details if not included
          if (!request.property_details && request.property_id) {
            try {
              const propertyResponse = await fetch(`http://localhost:8000/seller/property/${request.property_id}`, {
                headers: {
                  'Authorization': `Bearer ${token}`
                }
              });
              
              if (propertyResponse.ok) {
                const propertyData = await propertyResponse.json();
                request.property_details = propertyData;
                
                // Add additional display-friendly fields
                request.property_title = propertyData.location || propertyData.area || 
                                        (propertyData.survey_number ? `Plot ${propertyData.survey_number}` : 
                                        propertyData.id || "Unknown Property");
                
                request.property_address = propertyData.address || propertyData.location || "No address";
                request.property_type = propertyData.property_type || "Land";
                request.property_price = propertyData.price || 0;
              } else {
                console.error('Failed to fetch property details, status:', propertyResponse.status);
                // Set fallback property info
                request.property_title = `Property ${request.property_id}`;
              }
            } catch (error) {
              console.error('Error fetching property details for request:', error);
              // Set fallback property info on error
              request.property_title = `Property ${request.property_id}`;
            }
          }
          
          // Fetch buyer details if not included
          if (!request.buyer_details && request.buyer_id) {
            try {
              // Note: There's no need to fetch the full buyer profile here since
              // the document request already includes buyer_name, buyer_email fields
              // If name not present in request, set defaults
              if (!request.buyer_name) {
                request.buyer_name = 'Buyer';
              }
              
              // Set buyer_details from fields already in the request
              request.buyer_details = {
                name: request.buyer_name || 'Buyer',
                email: request.buyer_email || '',
                _id: request.buyer_id
              };
              
              // If absolutely needed, we can fetch just the buyer image
              // using the existing image endpoint which already works for both sellers and buyers
              request.buyer_details.image_url = `http://localhost:8000/seller/image/${request.buyer_id}`;
            } catch (error) {
              console.error('Error setting buyer details for request:', error);
            }
          }
          
          return request;
        }));
        
        setDocumentRequests(transformedRequests);
      } else {
        setDocumentRequests([]);
      }
    } catch (err) {
      console.error('Error fetching document requests:', err);
    } finally {
      setRequestsLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('buyer_token');
    localStorage.removeItem('seller_token');
    localStorage.removeItem('userType');
    navigate('/login');
  };

  const toggleProfileMenu = () => {
    setShowProfileMenu(!showProfileMenu);
  };
  
  const toggleRequestsMenu = () => {
    setShowRequestsMenu(!showRequestsMenu);
  };

  const handleEditProfile = () => {
    navigate('/edit-profile');
  };
  
  const handleUpdateRequestStatus = async (requestId, newStatus) => {
    try {
      const token = getToken('seller');
      if (!token) {
        console.error('No seller token found');
        return;
      }
      
      console.log(`Updating request ${requestId} status to ${newStatus}`);
      
      const response = await fetch(`http://localhost:8000/seller/document-requests/${requestId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          status: newStatus,
          expiry_days: 7
        })
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        throw new Error('Failed to update request status');
      }
      
      const data = await response.json();
      console.log('Update response:', data);
      
      // Update the local state
      setDocumentRequests(prevRequests => 
        prevRequests.map(req => 
          req.id === requestId 
            ? { ...req, status: newStatus } 
            : req
        )
      );
      
      // Show success notification
      setNotification({
        type: 'success',
        message: `Document request ${newStatus === 'approved' ? 'approved' : 'rejected'} successfully`
      });
      
      // Clear notification after some time
      setTimeout(() => {
        setNotification(null);
      }, 5000);
      
    } catch (err) {
      console.error('Error updating request status:', err);
      
      // Show error notification
      setNotification({
        type: 'error',
        message: err.message
      });
      
      // Clear notification after some time
      setTimeout(() => {
        setNotification(null);
      }, 5000);
    }
  };
  
  const handleViewProperty = (propertyId) => {
    navigate(`/property-details/${propertyId}`);
  };

  const handleEditProperty = (propertyId) => {
    navigate(`/edit-property/${propertyId}`);
  };

  const getImageUrl = (property) => {
    // Skip if property has no images
    if (!property || !property.images || property.images.length === 0) {
      console.log('Property has no images:', property?.id || 'unknown');
      return '/placeholder.jpg';
    }

    const image = property.images[0]; // Get first image
    const propertyId = property.id;

    if (!image || !propertyId) {
      console.log('Missing image data or property ID:', image, propertyId);
      return '/placeholder.jpg';
    }

    // Check if image contains a direct URL
    if (image.url && typeof image.url === 'string') {
      console.log(`Using direct URL for property ${propertyId}`);
      return image.url;
    }

    // Use the public property image endpoint
    const imageUrl = `http://localhost:8000/seller/public-property-image/${propertyId}/0`;
    console.log(`Generated image URL for property ${propertyId}: ${imageUrl}`);
    return imageUrl;
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

  const filteredProperties = Array.isArray(properties) ? properties.filter(property =>
    property.location?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    property.area?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    property.property_type?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    property.id?.toLowerCase().includes(searchQuery.toLowerCase())
  ) : [];

  console.log('Filtered properties count:', filteredProperties.length);

  const handleImageError = (e) => {
    e.target.onerror = null; // Prevent infinite error loops
    if (sellerData && sellerData._id) {
      // If the current source is already using /image/ endpoint, use a placeholder
      if (e.target.src.includes('/seller/image/')) {
        e.target.src = '/placeholder.jpg';
      } else {
        // Try the image endpoint first
        e.target.src = `http://localhost:8000/seller/image/${sellerData._id}`;
      }
    } else {
      e.target.src = '/placeholder.jpg';
    }
  };

  const getImageUrlFromSecureFilename = (secure_filename) => {
    if (!secure_filename) return null;
    return `http://localhost:8000/seller/property-image/${secure_filename}`;
  };

  const handlePropertyImageError = (e, property) => {
    console.error('Property image error:', e.target.src);
    
    // Fallback 1: Check if property has secure_filenames and try the first one
    if (property.secure_filenames && property.secure_filenames.length > 0) {
      console.log('Trying to load from secure_filenames:', property.secure_filenames[0]);
      const secureUrl = getImageUrlFromSecureFilename(property.secure_filenames[0]);
      e.target.src = secureUrl;
      
      // Add a secondary error handler
      e.target.onerror = () => {
        console.log('Secure filename URL also failed, using placeholder');
        e.target.src = '/placeholder.jpg';
        e.target.onerror = null;
      };
      return;
    }
    
    // Final fallback: placeholder
    console.log('No alternative images available, using placeholder');
    e.target.src = '/placeholder.jpg';
    e.target.onerror = null;
  };

  if (loading) return (
    <div className="loading-container">
      <div className="loading-spinner"></div>
      <p>Loading your properties...</p>
    </div>
  );
  
  if (error) return (
    <div className="error-container">
      <div className="error-message">
        <h3>Error Loading Data</h3>
        <p>{error}</p>
        <button onClick={() => window.location.reload()} className="btn btn-primary">
          Try Again
        </button>
      </div>
    </div>
  );

  return (
    <div className="list-properties">
      <header>
        <div className="container header-container">
          <div className="logo-container">
            <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign Logo" className="list-logo-image" />
          </div>
          
          <div className="logo-title-section">
            <h1 className="list-header-title">PROPERTY LISTINGS</h1>
          </div>
          
          <div className="header-actions">
            {/* Document Requests Menu */}
            <div className="requests-menu-container" ref={requestsRef}>
              <button 
                className="requests-menu-button" 
                onClick={toggleRequestsMenu}
                title="Document Requests"
              >
                <span className="requests-icon">📄</span>
                {documentRequests.length > 0 && (
                  <span className="requests-count">{documentRequests.length}</span>
                )}
              </button>
              
              {showRequestsMenu && (
                <div className="requests-dropdown">
                  <div className="requests-dropdown-header">
                    <h3>Document Requests</h3>
                  </div>
                  <div className="requests-dropdown-content">
                    {requestsLoading ? (
                      <div className="requests-loading">Loading requests...</div>
                    ) : documentRequests.length === 0 ? (
                      <div className="no-requests">No document requests</div>
                    ) : (
                      <ul className="requests-list">
                        {documentRequests.map(request => (
                          <li key={request.id} className="request-item">
                            <div className="request-info">
                              <div className="request-property" onClick={() => handleViewProperty(request.property_id)}>
                                <strong>Property:</strong> {request.property_title || request.property_details?.location || 
                                  request.property_details?.area || request.property_id}
                                {request.property_details && request.property_details.images && request.property_details.images.length > 0 && (
                                  <div className="request-property-thumbnail">
                                    <img 
                                      src={`http://localhost:8000/seller/public-property-image/${request.property_id}/0`}
                                      alt="Property Thumbnail"
                                      onError={(e) => {e.target.src = '/placeholder.jpg'}}
                                    />
                                  </div>
                                )}
                              </div>
                              {request.property_details && (
                                <div className="request-property-details">
                                  <span className="property-address">{request.property_address}</span>
                                  {request.property_details.price && (
                                    <span className="property-price">₹{request.property_details.price.toLocaleString()}</span>
                                  )}
                                </div>
                              )}
                              <div className="request-buyer">
                                <strong>Buyer:</strong> {request.buyer_details?.name || request.buyer_name || 'Unknown Buyer'}
                              </div>
                              <div className="request-date">
                                <strong>Requested:</strong> {new Date(request.created_at).toLocaleDateString()}
                              </div>
                              <div className="request-status">
                                <strong>Status:</strong> <span className={`status-badge ${request.status}`}>{request.status}</span>
                              </div>
                            </div>
                            {request.status === 'pending' && (
                              <div className="request-actions">
                                <button 
                                  className="approve-button"
                                  onClick={() => handleUpdateRequestStatus(request.id, 'approved')}
                                >
                                  Approve
                                </button>
                                <button 
                                  className="reject-button"
                                  onClick={() => handleUpdateRequestStatus(request.id, 'rejected')}
                                >
                                  Reject
                                </button>
                              </div>
                            )}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              )}
            </div>
            
            <div className="profile-dropdown-container" ref={profileRef}>
              <div className="list-seller-profile" onClick={toggleProfileMenu}>
                <div className="seller-avatar">
                  <img 
                    src={selfieUrl || '/placeholder.jpg'}
                    alt="Seller Profile"
                    onError={handleImageError}
                    className="profile-image"
                  />
                </div>
                <span className="seller-name">{sellerData?.name || 'Loading...'}</span>
              </div>
              {showProfileMenu && (
                <div className="profile-dropdown">
                  <div className="profile-dropdown-header">
                    <img 
                      src={selfieUrl || '/placeholder.jpg'}
                      alt="Seller Profile"
                      onError={handleImageError}
                      className="profile-image"
                    />
                    <div className="profile-dropdown-info">
                      <h3>{sellerData?.name}</h3>
                      <p>{sellerData?.email}</p>
                    </div>
                  </div>
                  <div className="profile-dropdown-content">
                    <div className="profile-details">
                      <div className="profile-detail-item">
                        <span className="detail-label">Phone:</span>
                        <span className="detail-value">{sellerData?.mobile_number}</span>
                      </div>
                      <div className="profile-detail-item">
                        <span className="detail-label">Properties Listed:</span>
                        <span className="detail-value">{properties.length}</span>
                      </div>
                    </div>
                    <div className="profile-dropdown-footer">
                      <button 
                        className="btn btn-secondary"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleEditProfile();
                        }}
                      >
                        Edit Profile
                      </button>
                      <button 
                        className="btn btn-outline" 
                        onClick={(e) => {
                          e.stopPropagation();
                          handleLogout();
                        }}
                      >
                        Logout
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main>
        <div className="content-container">
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
          <div className="list-controls">
            <div className="search-bar">
              <input
                type="text"
                placeholder="Search by location or reference number"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <button className="search-button">
                <i className="search-icon">🔍</i>
              </button>
            </div>
            <Link to="/add-property" className="btn btn-add">
              <span className="plus-icon">+</span>
              {properties.length === 0 ? 'List Your First Property' : 'Add Property'}
            </Link>
          </div>

          <div className="properties-list">
            {filteredProperties.length === 0 ? (
              <div className="no-properties">
                <p>No properties found. Add your first property!</p>
                <button 
                  className="btn btn-primary add-property-btn"
                  onClick={() => navigate('/add-property')}
                >
                  Add Property
                </button>
              </div>
            ) : (
              filteredProperties.map((property, index) => (
                <div key={property.id || index} className="property-card">
                  <div className="property-details-wrapper">
                    <div className="property-images">
                      <img 
                        src={getImageUrl(property) || '/placeholder.jpg'}
                        alt={property.location || property.area || property.address || "Property"} 
                        className="property-image"
                        onError={(e) => handlePropertyImageError(e, property)}
                      />
                    </div>
                    <div className="property-details">
                      <h3 className="property-location">
                        {property.address || property.location || property.area || 
                         (property.survey_number ? `Plot ${property.survey_number}` : "Unknown Location")}
                      </h3>
                      <div className="property-meta">
                        <div className="property-meta-item">
                          <span className="meta-label">Type:</span>
                          <span className="meta-value">{property.property_type || "Land"}</span>
                        </div>
                        <div className="property-meta-item">
                          <span className="meta-label">Area:</span>
                          <span className="meta-value">{property.plot_size || property.square_feet || "N/A"} sq.ft</span>
                        </div>
                        <div className="property-meta-item">
                          <span className="meta-label">Price:</span>
                          <span className="meta-value">₹{property.price?.toLocaleString() || "N/A"}</span>
                        </div>
                        {property.survey_number && (
                          <div className="property-meta-item">
                            <span className="meta-label">Survey #:</span>
                            <span className="meta-value">{property.survey_number}</span>
                          </div>
                        )}
                        <div className="property-meta-item">
                          <span className="meta-label">Listed:</span>
                          <span className="meta-value">{formatDate(property.created_at)}</span>
                        </div>
                        <div className="property-meta-item">
                          <span className="meta-label">Status:</span>
                          <span className={`status-badge ${property.status?.toLowerCase() || 'unknown'}`}>
                            {property.status || "Unknown"}
                          </span>
                        </div>
                      </div>
                      <div className="property-buttons">
                        <button 
                          className="btn btn-primary" 
                          onClick={() => handleViewProperty(property.id)}
                        >
                          View Details
                        </button>
                        <button 
                          className="btn btn-secondary" 
                          onClick={() => handleEditProperty(property.id)}
                        >
                          Edit
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </main>

      <footer>
        <div className="content-container">
          <p>&copy; 2025 Online Property Registration Portal. All Rights Reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default ListProperties;