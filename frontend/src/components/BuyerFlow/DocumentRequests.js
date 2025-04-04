import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './DocumentRequests.css';

function DocumentRequests() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeFilter, setActiveFilter] = useState('all');

  useEffect(() => {
    const fetchDocumentRequests = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          setError('You must be logged in to view document requests');
          setLoading(false);
          return;
        }

        const response = await fetch('http://localhost:8000/buyer/document-requests', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch document requests');
        }

        const data = await response.json();
        setRequests(data.requests || []);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching document requests:', err);
        setError(err.message);
        setLoading(false);
      }
    };

    fetchDocumentRequests();
  }, []);

  const getFilteredRequests = () => {
    if (activeFilter === 'all') {
      return requests;
    }
    return requests.filter(request => request.status === activeFilter);
  };

  const formatDate = (dateString) => {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  const getStatusClass = (status) => {
    switch (status) {
      case 'pending':
        return 'status-pending';
      case 'approved':
        return 'status-approved';
      case 'rejected':
        return 'status-rejected';
      default:
        return '';
    }
  };

  const getPropertyImage = (request) => {
    if (!request.property_image) {
      return '/assets/property-placeholder.jpg';
    }
    
    return `http://localhost:8000/property/image/${request.property_id}/0`;
  };

  const handleImageError = (e) => {
    e.target.src = '/assets/property-placeholder.jpg';
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading document requests...</p>
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

  const filteredRequests = getFilteredRequests();

  return (
    <div className="document-requests">
      <header>
        <div className="container header-container full-width">
          <div className="header-left">
            <Link to="/buyer-dashboard">
              <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign Logo" className="logo-image" />
            </Link>
          </div>
          
          <div className="header-center">
            <h1>Document Requests</h1>
          </div>
          
          <div className="header-right">
            <Link to="/buyer-dashboard" className="nav-link">Dashboard</Link>
            <Link to="/buyer-properties" className="nav-link">Browse Properties</Link>
          </div>
        </div>
      </header>

      <main className="container">
        <div className="filter-section">
          <div className="filter-buttons">
            <button
              className={`filter-button ${activeFilter === 'all' ? 'active' : ''}`}
              onClick={() => setActiveFilter('all')}
            >
              All Requests
            </button>
            <button
              className={`filter-button ${activeFilter === 'pending' ? 'active' : ''}`}
              onClick={() => setActiveFilter('pending')}
            >
              Pending
            </button>
            <button
              className={`filter-button ${activeFilter === 'approved' ? 'active' : ''}`}
              onClick={() => setActiveFilter('approved')}
            >
              Approved
            </button>
            <button
              className={`filter-button ${activeFilter === 'rejected' ? 'active' : ''}`}
              onClick={() => setActiveFilter('rejected')}
            >
              Rejected
            </button>
          </div>
          <div className="requests-count">
            Showing {filteredRequests.length} {filteredRequests.length === 1 ? 'request' : 'requests'}
          </div>
        </div>

        {filteredRequests.length === 0 ? (
          <div className="no-requests">
            <p>No document requests found matching the selected filter.</p>
            {activeFilter !== 'all' && (
              <button className="reset-button" onClick={() => setActiveFilter('all')}>
                Show All Requests
              </button>
            )}
            {requests.length === 0 && (
              <div className="get-started">
                <p>Get started by browsing properties and requesting access to documents.</p>
                <Link to="/buyer-properties" className="browse-button">
                  Browse Properties
                </Link>
              </div>
            )}
          </div>
        ) : (
          <div className="requests-grid">
            {filteredRequests.map(request => (
              <div key={request.id} className="request-card">
                <div className="request-property">
                  <div className="property-image">
                    <img
                      src={getPropertyImage(request)}
                      alt={request.property_address}
                      onError={handleImageError}
                    />
                  </div>
                  <div className="property-info">
                    <h3 className="property-address">{request.property_address}</h3>
                    <div className="property-type">{request.property_type}</div>
                    <Link to={`/buyer-property/${request.property_id}`} className="view-property">
                      View Property
                    </Link>
                  </div>
                </div>
                <div className="request-details">
                  <div className="request-info">
                    <div className="request-row">
                      <span className="info-label">Seller:</span>
                      <span className="info-value">{request.seller_name}</span>
                    </div>
                    <div className="request-row">
                      <span className="info-label">Requested:</span>
                      <span className="info-value">{formatDate(request.request_date)}</span>
                    </div>
                    {request.response_date && (
                      <div className="request-row">
                        <span className="info-label">Response:</span>
                        <span className="info-value">{formatDate(request.response_date)}</span>
                      </div>
                    )}
                  </div>
                  <div className="request-status">
                    <span className={`status-badge ${getStatusClass(request.status)}`}>
                      {request.status === 'pending' && 'Pending'}
                      {request.status === 'approved' && 'Approved'}
                      {request.status === 'rejected' && 'Rejected'}
                    </span>
                    {request.status === 'approved' && (
                      <Link to={`/buyer-property/${request.property_id}`} className="view-documents">
                        View Documents
                      </Link>
                    )}
                  </div>
                </div>
                {request.status === 'rejected' && request.rejection_reason && (
                  <div className="rejection-reason">
                    <span className="reason-label">Reason:</span>
                    <span className="reason-text">{request.rejection_reason}</span>
                  </div>
                )}
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

export default DocumentRequests; 