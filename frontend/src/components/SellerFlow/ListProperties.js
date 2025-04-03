import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './ListProperties.css';

function ListProperties() {
  const [sellerData, setSellerData] = useState(null);
  const [properties, setProperties] = useState([]);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selfieUrl, setSelfieUrl] = useState(null);
  const [selfieLoading, setSelfieLoading] = useState(true);
  const profileRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Add click outside handler
    function handleClickOutside(event) {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setShowProfileMenu(false);
      }
    }

    // Bind the event listener
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      // Unbind the event listener on cleanup
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Helper function to fetch images with token
  const fetchImageWithToken = async (url) => {
    const token = localStorage.getItem('token');
    try {
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Cache-Control': 'no-cache'
        },
        credentials: 'include'
      });
      
      if (response.ok) {
        // Return the URL directly since we're using authenticated URLs
        return url;
      }
      return null;
    } catch (error) {
      console.error('Error fetching image:', error);
      return null;
    }
  };

  // Function to load seller selfie with retries
  const loadSellerSelfie = async (sellerId) => {
    if (!sellerId) return;
    
    setSelfieLoading(true);
    
    try {
      const token = localStorage.getItem('token');
      
      // First get the seller data to access the actual filename
      const sellerResponse = await fetch('http://localhost:8000/seller/get-seller', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (sellerResponse.ok) {
        const sellerData = await sellerResponse.json();
        
        // Check if the seller has selfie data in the database
        if (sellerData.selfie_filename) {
          // Use the actual filename from the database
          const directUrl = `http://localhost:8000/seller/images/sec-user-kyc-images/${sellerData.selfie_filename}`;
          console.log('Using database filename:', sellerData.selfie_filename);
          setSelfieUrl(directUrl);
        } else if (sellerData.selfie_url) {
          // If there's a selfie URL but no filename, use the URL directly
          console.log('Using direct selfie URL from database');
          setSelfieUrl(sellerData.selfie_url);
        } else {
          // Fallback to constructing a URL based on ID patterns
          const directUrl = `http://localhost:8000/seller/public-image/${sellerId}`;
          console.log('No selfie info in database, using public image endpoint');
          setSelfieUrl(directUrl);
        }
      } else {
        // Fallback if we can't get seller data
        setSelfieUrl(`http://localhost:8000/seller/public-image/${sellerId}`);
      }
    } catch (error) {
      console.error('Error setting selfie URL:', error);
      // Fallback to public image endpoint
      setSelfieUrl(`http://localhost:8000/seller/public-image/${sellerId}`);
    } finally {
      setSelfieLoading(false);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const token = localStorage.getItem('token');
        if (!token) {
          navigate('/login');
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
        
        // Sort properties by date (most recent first)
        if (Array.isArray(propsData)) {
          propsData.sort((a, b) => {
            const dateA = new Date(a.created_at || 0);
            const dateB = new Date(b.created_at || 0);
            return dateB - dateA;
          });
        }
        
        setProperties(propsData);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError(err.message);
        setLoading(false);
      }
    };
    
    fetchData();
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_type');
    navigate('/login');
  };

  const toggleProfileMenu = () => {
    setShowProfileMenu(!showProfileMenu);
  };

  const handleEditProfile = () => {
    navigate('/edit-profile');
  };

  const handleViewPropertyDetails = (propertyId) => {
    navigate(`/property-details/${propertyId}`);
  };

  const handleEditProperty = (propertyId) => {
    navigate(`/edit-property/${propertyId}`);
  };

  const getImageUrl = (property) => {
    // Skip if property has no images
    if (!property || !property.images || property.images.length === 0) {
      return '/placeholder.jpg';
    }

    const image = property.images[0]; // Get first image
    const propertyId = property.id;

    if (!image || !propertyId) {
      console.log('Missing image data or property ID:', image, propertyId);
      return '/placeholder.jpg';
    }

    // Use the public property image endpoint
    return `http://localhost:8000/seller/public-property-image/${propertyId}/0`;
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

  // Helper function to get image URL from secure_filename
  const getImageUrlFromSecureFilename = (secure_filename) => {
    if (!secure_filename) return '/placeholder.jpg';
    // Return the placeholder directly since we don't use this function anymore
    return '/placeholder.jpg';
  };
  
  // Helper function to debug image loading
  const debugImageLoading = async (url, propertyId) => {
    try {
      console.log(`Attempting to load image for property ${propertyId} from: ${url}`);
      
      // Fetch the image directly to check status
      const response = await fetch(url);
      
      if (!response.ok) {
        console.error(`Image fetch failed with status ${response.status}: ${response.statusText}`);
        return false;
      }
      
      // Check content type
      const contentType = response.headers.get('content-type');
      console.log(`Image content type: ${contentType}`);
      
      // Check content length
      const contentLength = response.headers.get('content-length');
      console.log(`Image size: ${contentLength} bytes`);
      
      // Additional checks
      if (contentLength && parseInt(contentLength) < 100) {
        console.warn('Image size suspiciously small, might be broken');
      }
      
      if (!contentType || !contentType.startsWith('image/')) {
        console.warn(`Content type "${contentType}" might not be a valid image`);
      }
      
      console.log('Image appears to be valid and loadable');
      return true;
    } catch (e) {
      console.error(`Error debugging image: ${e.message}`);
      return false;
    }
  };

  // Helper function to get a data URL version of an image
  const getImageDataUrl = async (secure_filename, propertyId) => {
    if (!secure_filename) return null;
    
    try {
      const response = await fetch(`http://localhost:8000/seller/property-image-data-url/${secure_filename}`);
      if (!response.ok) {
        console.error(`Failed to get data URL for ${secure_filename}`);
        return null;
      }
      
      const data = await response.json();
      console.log(`Successfully loaded data URL for property ${propertyId}`);
      return data.data_url;
    } catch (e) {
      console.error(`Error getting data URL: ${e.message}`);
      return null;
    }
  };
  
  // Helper function to handle image loading with fallback to data URL
  const handleImageLoad = async (imageElement, secure_filename, propertyId) => {
    // Try normal image loading first
    imageElement.src = getImageUrlFromSecureFilename(secure_filename);
    
    // Add error handler that will try data URL if direct loading fails
    imageElement.onerror = async () => {
      console.log(`Trying data URL fallback for property ${propertyId}`);
      const dataUrl = await getImageDataUrl(secure_filename, propertyId);
      if (dataUrl) {
        imageElement.src = dataUrl;
      } else {
        imageElement.src = '/placeholder.jpg';
      }
    };
  };

  const handlePropertyImageError = (e, property) => {
    console.log('Image loading error for property:', property.id);
    e.target.onerror = null; // Prevent infinite error loops
    e.target.src = '/placeholder.jpg';
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
          <div className="logo-title-section">
            <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign Logo" className="list-logo-image" />
            <h1 className="list-header-title">PROPERTY LISTINGS</h1>
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
      </header>

      <main className="container">
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
                      alt={property.location || property.area || "Property"} 
                      className="property-image"
                      onError={(e) => handlePropertyImageError(e, property)}
                    />
                  </div>
                  <div className="property-details">
                    <h3 className="property-location">
                      {property.location || property.area || "Unknown Location"}
                    </h3>
                    <div className="property-meta">
                      <div className="property-meta-item">
                        <span className="meta-label">Type:</span>
                        <span className="meta-value">{property.property_type || "N/A"}</span>
                      </div>
                      <div className="property-meta-item">
                        <span className="meta-label">Area:</span>
                        <span className="meta-value">{property.square_feet} sq.ft</span>
                      </div>
                      <div className="property-meta-item">
                        <span className="meta-label">Price:</span>
                        <span className="meta-value">₹{property.price}/sq.ft</span>
                      </div>
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
                        onClick={() => handleViewPropertyDetails(property.id)}
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
      </main>

      <footer>
        <div className="container">
          <p>&copy; 2025 Online Property Registration Portal. All Rights Reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default ListProperties;