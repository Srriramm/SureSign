import React, { useState, useEffect } from 'react';
import { getToken } from '../../utils/authUtils';
import './LawyerVerification.css';

function LawyerVerification({ propertyId, onVerificationUpdated }) {
  const [loading, setLoading] = useState(false);
  const [verificationStatus, setVerificationStatus] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    lawyer_name: '',
    lawyer_email: '',
    lawyer_phone: ''
  });
  const [formErrors, setFormErrors] = useState({});
  const [notification, setNotification] = useState({ message: '', type: '' });

  // Fetch existing verification status
  useEffect(() => {
    const fetchVerificationStatus = async () => {
      try {
        setLoading(true);
        const token = getToken('buyer');
        if (!token) return;

        const response = await fetch(
          `http://localhost:8000/buyer/property/${propertyId}/lawyer-verification`, 
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );

        if (response.ok) {
          const data = await response.json();
          setVerificationStatus(data);
          
          // If there's active verification, don't show the form
          if (data.has_verification) {
            setShowForm(false);
          }
        }
      } catch (error) {
        console.error('Error fetching verification status:', error);
        setNotification({
          message: 'Failed to get verification status',
          type: 'error'
        });
      } finally {
        setLoading(false);
      }
    };

    if (propertyId) {
      fetchVerificationStatus();
    }
  }, [propertyId]);

  const handleShowForm = () => {
    setShowForm(true);
    setFormErrors({});
  };

  const handleCancel = () => {
    setShowForm(false);
    setFormData({
      lawyer_name: '',
      lawyer_email: '',
      lawyer_phone: ''
    });
    setFormErrors({});
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    // Clear error when user types
    if (formErrors[name]) {
      setFormErrors(prev => ({
        ...prev,
        [name]: null
      }));
    }
  };

  const validateForm = () => {
    const errors = {};
    
    if (!formData.lawyer_name.trim()) {
      errors.lawyer_name = 'Lawyer name is required';
    }
    
    if (!formData.lawyer_email.trim()) {
      errors.lawyer_email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.lawyer_email)) {
      errors.lawyer_email = 'Please enter a valid email address';
    }
    
    if (!formData.lawyer_phone.trim()) {
      errors.lawyer_phone = 'Phone number is required';
    } else if (!/^[0-9]{10}$/.test(formData.lawyer_phone.replace(/\D/g, ''))) {
      errors.lawyer_phone = 'Please enter a valid 10-digit phone number';
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    try {
      setLoading(true);
      const token = getToken('buyer');
      
      if (!token) {
        setNotification({
          message: 'You need to be logged in to add a lawyer',
          type: 'error'
        });
        return;
      }
      
      const response = await fetch(
        `http://localhost:8000/buyer/property/${propertyId}/verify-with-lawyer`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(formData)
        }
      );
      
      if (response.ok) {
        const data = await response.json();
        setShowForm(false);
        
        // Refresh verification status
        setVerificationStatus({
          has_verification: true,
          verification: data.lawyer_verification,
          is_expired: false
        });
        
        setNotification({
          message: `Lawyer verification request sent to ${formData.lawyer_email}`,
          type: 'success'
        });
        
        // Clear form
        setFormData({
          lawyer_name: '',
          lawyer_email: '',
          lawyer_phone: ''
        });
        
        // Notify parent component
        if (onVerificationUpdated) {
          onVerificationUpdated(data.lawyer_verification);
        }
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to add lawyer');
      }
    } catch (error) {
      console.error('Error adding lawyer:', error);
      setNotification({
        message: error.message || 'Failed to add lawyer for verification',
        type: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'verified':
        return <span className="status-badge verified">Verified</span>;
      case 'issues_found':
        return <span className="status-badge issues">Issues Found</span>;
      case 'pending':
      default:
        return <span className="status-badge pending">Pending Verification</span>;
    }
  };

  const renderVerificationStatus = () => {
    if (!verificationStatus || !verificationStatus.has_verification) {
      return (
        <div className="no-verification">
          <p>No lawyer has been assigned to verify this property's documents.</p>
          <button 
            className="btn-add-lawyer" 
            onClick={handleShowForm}
            disabled={loading}
          >
            Add a Lawyer for Verification
          </button>
        </div>
      );
    }
    
    const verification = verificationStatus.verification;
    const isExpired = verificationStatus.is_expired;
    
    return (
      <div className="verification-status">
        <div className="lawyer-info">
          <h4>Lawyer Details</h4>
          <p><strong>Name:</strong> {verification.lawyer_name}</p>
          <p><strong>Email:</strong> {verification.lawyer_email}</p>
          <p><strong>Phone:</strong> {verification.lawyer_phone}</p>
        </div>
        
        <div className="verification-details">
          <div className="status-section">
            <span className="status-label">Status:</span>
            {getStatusBadge(verification.verification_status)}
          </div>
          
          {verification.verification_notes && (
            <div className="notes-section">
              <p><strong>Notes:</strong> {verification.verification_notes}</p>
            </div>
          )}
          
          {verification.issues_details && verification.verification_status === 'issues_found' && (
            <div className="issues-section">
              <p><strong>Issues Found:</strong> {verification.issues_details}</p>
            </div>
          )}
          
          <div className="dates-section">
            <p><strong>Requested on:</strong> {new Date(verification.created_at).toLocaleString()}</p>
            {verification.updated_at && (
              <p><strong>Last updated:</strong> {new Date(verification.updated_at).toLocaleString()}</p>
            )}
          </div>
          
          {isExpired && (
            <div className="expired-notice">
              <p>The verification link has expired. You may need to request a new verification.</p>
              <button 
                className="btn-add-lawyer" 
                onClick={handleShowForm}
                disabled={loading}
              >
                Add New Lawyer
              </button>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="lawyer-verification-section">
      <h3>Legal Verification</h3>
      
      {notification.message && (
        <div className={`notification ${notification.type}`}>
          <span>{notification.message}</span>
          <button 
            className="close-notification"
            onClick={() => setNotification({ message: '', type: '' })}
          >
            ×
          </button>
        </div>
      )}
      
      {loading ? (
        <div className="loading-indicator">Loading verification status...</div>
      ) : showForm ? (
        <div className="lawyer-form-container">
          <h4>Add a Lawyer for Document Verification</h4>
          <form onSubmit={handleSubmit} className="lawyer-form">
            <div className="form-group">
              <label htmlFor="lawyer_name">Lawyer Name *</label>
              <input
                type="text"
                id="lawyer_name"
                name="lawyer_name"
                value={formData.lawyer_name}
                onChange={handleChange}
                className={formErrors.lawyer_name ? 'error' : ''}
                placeholder="Enter lawyer's full name"
              />
              {formErrors.lawyer_name && <div className="error-message">{formErrors.lawyer_name}</div>}
            </div>
            
            <div className="form-group">
              <label htmlFor="lawyer_email">Lawyer Email *</label>
              <input
                type="email"
                id="lawyer_email"
                name="lawyer_email"
                value={formData.lawyer_email}
                onChange={handleChange}
                className={formErrors.lawyer_email ? 'error' : ''}
                placeholder="Enter lawyer's email address"
              />
              {formErrors.lawyer_email && <div className="error-message">{formErrors.lawyer_email}</div>}
            </div>
            
            <div className="form-group">
              <label htmlFor="lawyer_phone">Lawyer Phone *</label>
              <input
                type="tel"
                id="lawyer_phone"
                name="lawyer_phone"
                value={formData.lawyer_phone}
                onChange={handleChange}
                className={formErrors.lawyer_phone ? 'error' : ''}
                placeholder="Enter lawyer's phone number"
              />
              {formErrors.lawyer_phone && <div className="error-message">{formErrors.lawyer_phone}</div>}
            </div>
            
            <div className="form-actions">
              <button 
                type="button" 
                className="btn-cancel" 
                onClick={handleCancel}
                disabled={loading}
              >
                Cancel
              </button>
              <button 
                type="submit" 
                className="btn-submit" 
                disabled={loading}
              >
                {loading ? 'Sending...' : 'Add Lawyer'}
              </button>
            </div>
          </form>
        </div>
      ) : (
        renderVerificationStatus()
      )}
    </div>
  );
}

export default LawyerVerification; 