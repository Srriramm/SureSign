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
        (property.location && property.location.toLowerCase().includes(searchTermLower))
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
                    alt={`${property.title || 'Property'}`}
                    onError={handleImageError}
                  />
                </div>
                <div className="property-details">
                  <h3 className="property-address">{property.title || property.location || 'Property'}</h3>
                  <div className="property-type">{property.property_type || 'N/A'}</div>
                  <div className="property-price">₹ {property.price ? Number(property.price).toLocaleString() : 'N/A'}</div>
                  <div className="property-area">
                    <span className="area-label">Area:</span> {property.area || 'N/A'}
                  </div>
                  <div className="property-size">
                    <span className="size-label">Size:</span> {property.square_feet || property.area_sq_ft || 'N/A'} sq.ft
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