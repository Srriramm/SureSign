import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './BuyerProperties.css';

function BuyerProperties() {
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredProperties, setFilteredProperties] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchProperties = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          setError('You must be logged in to view properties');
          setLoading(false);
          return;
        }

        const response = await fetch('http://localhost:8000/buyer/properties', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch properties');
        }

        const data = await response.json();
        setProperties(data || []);
        setFilteredProperties(data || []);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching properties:', err);
        setError(err.message);
        setLoading(false);
      }
    };

    fetchProperties();
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
        (property.location && property.location.toLowerCase().includes(searchTermLower)) ||
        (property.address && property.address.toLowerCase().includes(searchTermLower)) ||
        (property.survey_number && property.survey_number.toString().includes(searchTermLower))
      );
    });

    setFilteredProperties(results);
  }, [searchTerm, properties]);

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
        <p>Loading properties...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <div className="error-message">
          <h3>Error</h3>
          <p>{error}</p>
          <Link to="/buyer-dashboard" className="back-link">Back to Dashboard</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="buyer-properties">
      <header>
        <div className="container header-container full-width">
          <div className="header-left">
            <Link to="/buyer-dashboard">
              <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign Logo" className="logo-image" />
            </Link>
          </div>
          
          <div className="header-center">
            <h1>Available Properties</h1>
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
          <div className="properties-grid">
            {filteredProperties.map(property => (
              <div 
                key={property.id} 
                className="property-card" 
                onClick={() => handlePropertyClick(property.id)}
              >
                <div className="property-image">
                  <img
                    src={getImageUrl(property)}
                    alt={getPropertyTitle(property)}
                    onError={handleImageError}
                  />
                </div>
                <div className="property-details">
                  <h3 className="property-title">{getPropertyTitle(property)}</h3>
                  
                  <div className="property-info-grid">
                    <div className="property-info-item">
                      <span className="info-label">Type:</span>
                      <span className="info-value">{property.property_type || 'Land'}</span>
                    </div>
                    <div className="property-info-item">
                      <span className="info-label">Area:</span>
                      <span className="info-value">{getPropertySize(property)} sq.ft</span>
                    </div>
                    <div className="property-info-item">
                      <span className="info-label">Price:</span>
                      <span className="info-value">{formatPrice(property.price)}</span>
                    </div>
                    <div className="property-info-item">
                      <span className="info-label">Survey #:</span>
                      <span className="info-value">{property.survey_number || 'N/A'}</span>
                    </div>
                    <div className="property-info-item">
                      <span className="info-label">Listed:</span>
                      <span className="info-value">{property.created_at ? new Date(property.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'numeric', day: 'numeric' }) : 'N/A'}</span>
                    </div>
                    <div className="property-info-item">
                      <span className="info-label">Status:</span>
                      <span className="info-value">
                        <span className={`status-badge ${(property.status || 'live').toLowerCase()}`}>
                          {property.status || 'LIVE'}
                        </span>
                      </span>
                    </div>
                  </div>
                  
                  <div className="property-actions">
                    <button className="view-details-btn">View Details</button>
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

export default BuyerProperties; 