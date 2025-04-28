import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getToken, clearAuthData, getAuthHeaders } from '../../utils/authUtils';
import './BuyerDashboard.css';

function BuyerDashboard() {
  const [profile, setProfile] = useState(null);
  const [properties, setProperties] = useState([]);
  const [filteredProperties, setFilteredProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const profileRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Add click outside handler for profile dropdown
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

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const token = getToken('buyer');
        if (!token) {
          setError('You must be logged in to view this page');
          setLoading(false);
          return;
        }

        // Fetch buyer profile
        const profileResponse = await fetch('http://localhost:8000/buyer/get-buyer', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!profileResponse.ok) {
          throw new Error('Failed to fetch profile');
        }

        const profileData = await profileResponse.json();
        setProfile(profileData);

        // Fetch all properties
        const propertiesResponse = await fetch('http://localhost:8000/buyer/properties', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!propertiesResponse.ok) {
          throw new Error('Failed to fetch properties');
        }

        const propertiesData = await propertiesResponse.json();
        setProperties(propertiesData || []);
        setFilteredProperties(propertiesData || []);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError(err.message);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    if (searchTerm.trim() === '') {
      setFilteredProperties(properties);
      return;
    }

    const results = properties.filter(property => {
      const searchTermLower = searchTerm.toLowerCase();
      return (
        (property.area && property.area.toLowerCase().includes(searchTermLower)) ||
        (property.property_type && property.property_type.toLowerCase().includes(searchTermLower)) ||
        (property.description && property.description.toLowerCase().includes(searchTermLower)) ||
        (property.title && property.title.toLowerCase().includes(searchTermLower)) ||
        (property.location && property.location.toLowerCase().includes(searchTermLower))
      );
    });

    setFilteredProperties(results);
  }, [searchTerm, properties]);

  const toggleProfileMenu = () => {
    setShowProfileMenu(!showProfileMenu);
  };

  const handleLogout = () => {
    clearAuthData('buyer');
    navigate('/login/buyer');
  };

  const handleEditProfile = () => {
    navigate('/edit-buyer-profile');
  };

  const handlePropertyClick = (propertyId) => {
    navigate(`/buyer-property/${propertyId}`);
  };

  const getImageUrl = (property) => {
    if (!property.images || property.images.length === 0) {
      return '/assets/property-placeholder.jpg';
    }
    
    // Use public endpoint for image URL
    return `http://localhost:8000/buyer/property-image/${property.id}/0`;
  };

  const handleImageError = (e) => {
    console.log('Image failed to load, using placeholder');
    e.target.src = '/assets/property-placeholder.jpg';
  };

  // Format price to display properly
  const formatPrice = (price) => {
    if (!price) return 'N/A';
    return `₹ ${Number(price).toLocaleString()}`;
  };

  // Helper to display the most appropriate property name/location
  const getPropertyTitle = (property) => {
    return property.address || 
           property.location || 
           property.area || 
           (property.survey_number ? `Plot ${property.survey_number}` : 'Property');
  };

  // Helper to get appropriate property size
  const getPropertySize = (property) => {
    return property.plot_size || 
           property.square_feet || 
           property.area_sq_ft || 
           'N/A';
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error-message">
          <h3>Error</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="buyer-dashboard">
      <header>
        <div className="header-container full-width">
          <div className="logo-container">
            <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign Logo" className="logo-image" />
          </div>
          
          <div className="logo-title-section">
            <h1 className="dashboard-title">Buyer Dashboard</h1>
          </div>
          
          <div className="profile-dropdown-container" ref={profileRef}>
            <div className="buyer-profile" onClick={toggleProfileMenu}>
              <div className="buyer-avatar">
                {profile?.selfie_url ? (
                  <img 
                    src={profile.selfie_url} 
                    alt={profile.name} 
                    className="profile-image"
                    onError={(e) => {
                      e.target.src = '/assets/user-placeholder.png';
                    }}
                  />
                ) : (
                  <div className="avatar-placeholder">
                    {profile?.name ? profile.name.charAt(0).toUpperCase() : 'B'}
                  </div>
                )}
              </div>
              <span className="buyer-name">{profile?.name}</span>
            </div>
            
            {showProfileMenu && (
              <div className="profile-dropdown">
                <div className="profile-dropdown-header">
                  {profile?.selfie_url ? (
                    <img 
                      src={profile.selfie_url} 
                      alt={profile.name} 
                      className="profile-image"
                      onError={(e) => {
                        e.target.src = '/assets/user-placeholder.png';
                      }}
                    />
                  ) : (
                    <div className="avatar-placeholder large">
                      {profile?.name ? profile.name.charAt(0).toUpperCase() : 'B'}
                    </div>
                  )}
                  <div className="profile-dropdown-info">
                    <h3>{profile?.name || 'Buyer'}</h3>
                    <p>{profile?.email || 'No email'}</p>
                  </div>
                </div>
                <div className="profile-dropdown-content">
                  <div className="profile-details">
                    <div className="profile-detail-item">
                      <span className="detail-label">Phone</span>
                      <span className="detail-value">{profile?.mobile_number || 'Not provided'}</span>
                    </div>
                  </div>
                  <button className="dropdown-btn edit-profile-btn" onClick={handleEditProfile}>
                    Edit Profile
                  </button>
                </div>
                <div className="profile-dropdown-footer">
                  <button className="dropdown-btn logout-btn" onClick={handleLogout}>
                    Logout
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="container">
        <div className="search-section">
          <div className="search-bar">
            <input
              type="text"
              placeholder="Search by location, property type, or title..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
            {searchTerm && (
              <button className="clear-search" onClick={() => setSearchTerm('')}>
                ×
              </button>
            )}
          </div>
          <div className="search-results-count">
            Showing {filteredProperties.length} {filteredProperties.length === 1 ? 'property' : 'properties'}
          </div>
        </div>

        {filteredProperties.length === 0 ? (
          <div className="no-properties">
            <p>No properties found matching your search criteria.</p>
            {searchTerm && (
              <button className="reset-button" onClick={() => setSearchTerm('')}>
                Reset Search
              </button>
            )}
          </div>
        ) : (
          <div className="properties-list">
            {filteredProperties.map(property => (
              <div key={property.id} className="property-card">
                <div className="property-details-wrapper">
                  <div className="property-images">
                    <img
                      src={getImageUrl(property)}
                      alt={getPropertyTitle(property)}
                      className="property-image"
                      onError={handleImageError}
                    />
                  </div>
                  <div className="property-details">
                    <h3 className="property-location">{getPropertyTitle(property)}</h3>
                    <div className="property-meta">
                      <div className="property-meta-item">
                        <span className="meta-label">Type:</span>
                        <span className="meta-value">{property.property_type || 'Land'}</span>
                      </div>
                      <div className="property-meta-item">
                        <span className="meta-label">Area:</span>
                        <span className="meta-value">{getPropertySize(property)} sq.ft</span>
                      </div>
                      <div className="property-meta-item">
                        <span className="meta-label">Price:</span>
                        <span className="meta-value">{formatPrice(property.price)}</span>
                      </div>
                      <div className="property-meta-item">
                        <span className="meta-label">Survey #:</span>
                        <span className="meta-value">{property.survey_number || 'N/A'}</span>
                      </div>
                      <div className="property-meta-item">
                        <span className="meta-label">Listed:</span>
                        <span className="meta-value">{property.created_at ? new Date(property.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : 'N/A'}</span>
                      </div>
                      <div className="property-meta-item">
                        <span className="meta-label">Status:</span>
                        <span className={`status-badge ${(property.status || 'live').toLowerCase()}`}>
                          {property.status || 'LIVE'}
                        </span>
                      </div>
                    </div>
                    <div className="property-buttons">
                      <button className="btn btn-primary" onClick={() => handlePropertyClick(property.id)}>View Details</button>
                      {/* Optionally add Edit button if needed */}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      <footer>
        <div className="container full-width">
          <p>&copy; 2025 Online Property Registration Portal. All Rights Reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default BuyerDashboard; 