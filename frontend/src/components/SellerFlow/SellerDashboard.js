import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

const SellerDashboard = () => {
  const [properties, setProperties] = useState([]);

  useEffect(() => {
    // Fetch properties from the backend
  }, []);

  return (
    <div className="dashboard-container">
      <div className="dashboard-actions">
        <Link to="/add-property" className="dashboard-action-card">
          <div className="action-icon">
            <i className="fas fa-plus-circle"></i>
          </div>
          <div className="action-content">
            <h3 className="action-title">Add Property</h3>
            <p className="action-description">List a new property for sale</p>
          </div>
        </Link>
        
        <Link to="/list-properties" className="dashboard-action-card">
          <div className="action-icon">
            <i className="fas fa-list"></i>
          </div>
          <div className="action-content">
            <h3 className="action-title">My Properties</h3>
            <p className="action-description">View and manage your properties</p>
          </div>
        </Link>
        
        <Link to="/document-requests" className="dashboard-action-card">
          <div className="action-icon">
            <i className="fas fa-file-alt"></i>
          </div>
          <div className="action-content">
            <h3 className="action-title">Document Requests</h3>
            <p className="action-description">Manage document access requests</p>
          </div>
        </Link>
      </div>
    </div>
  );
};

export default SellerDashboard; 