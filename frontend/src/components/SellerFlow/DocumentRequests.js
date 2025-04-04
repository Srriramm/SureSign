import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getToken } from '../../utils/authUtils';
import './DocumentRequests.css';

function DocumentRequests() {
  const navigate = useNavigate();
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [detailedRequest, setDetailedRequest] = useState(null);
  const [viewMode, setViewMode] = useState('list'); // list or detail
  const [processing, setProcessing] = useState(false);
  const [notification, setNotification] = useState(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [expiryDays, setExpiryDays] = useState(7);

  useEffect(() => {
    const fetchDocumentRequests = async () => {
      try {
        setLoading(true);
        const token = getToken('seller');
        if (!token) {
          navigate('/login/seller');
          return;
        }

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
        setRequests(data);
      } catch (err) {
        console.error('Error fetching document requests:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDocumentRequests();
  }, [navigate]);

  const fetchRequestDetails = async (requestId) => {
    try {
      setLoading(true);
      const token = getToken('seller');
      if (!token) {
        navigate('/login/seller');
        return;
      }

      const response = await fetch(`http://localhost:8000/seller/document-requests/${requestId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch request details');
      }
      
      const data = await response.json();
      console.log('Request details:', data);
      setDetailedRequest(data);
      setViewMode('detail');
    } catch (err) {
      console.error('Error fetching request details:', err);
      setNotification({
        type: 'error',
        message: err.message
      });
    } finally {
      setLoading(false);
    }
  };

  const handleApproveRequest = async () => {
    await handleRequestStatus('approved');
  };

  const handleRejectRequest = async () => {
    if (!rejectionReason.trim()) {
      setNotification({
        type: 'error',
        message: 'Please provide a reason for rejecting the request'
      });
      return;
    }
    await handleRequestStatus('rejected');
  };

  const handleRequestStatus = async (status) => {
    try {
      setProcessing(true);
      const token = getToken('seller');
      if (!token) {
        navigate('/login/seller');
        return;
      }

      const requestBody = {
        status,
        expiry_days: expiryDays
      };

      if (status === 'rejected') {
        requestBody.rejection_reason = rejectionReason;
      }

      console.log(`Sending ${status} request to:`, `/seller/document-requests/${detailedRequest.id}`);
      console.log('Request payload:', requestBody);

      const response = await fetch(`http://localhost:8000/seller/document-requests/${detailedRequest.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(requestBody)
      });
      
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to ${status} request`);
      }
      
      const data = await response.json();
      console.log(`Request ${status} response:`, data);
      
      // Update the request in the local state
      setRequests(prevRequests => 
        prevRequests.map(req => 
          req.id === detailedRequest.id 
            ? { ...req, status, updated_at: new Date().toISOString() } 
            : req
        )
      );
      
      // Set notification
      setNotification({
        type: 'success',
        message: `Request ${status === 'approved' ? 'approved' : 'rejected'} successfully`
      });
      
      // Reset and go back to list view
      setRejectionReason('');
      setDetailedRequest(null);
      setViewMode('list');
    } catch (err) {
      console.error(`Error ${status} request:`, err);
      setNotification({
        type: 'error',
        message: err.message
      });
    } finally {
      setProcessing(false);
    }
  };

  const handleBackToList = () => {
    setDetailedRequest(null);
    setViewMode('list');
    setRejectionReason('');
  };

  if (loading && requests.length === 0) {
    return (
      <div className="document-requests-page">
        <header>
          <div className="container header-container full-width">
            <div className="header-left">
              <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign Logo" className="logo-image" />
            </div>
            <div className="header-center">
              <h1>Document Requests</h1>
            </div>
            <div className="header-right"></div>
          </div>
        </header>
        <main className="container">
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Loading document requests...</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="document-requests-page">
      <header>
        <div className="container header-container full-width">
          <div className="header-left">
            <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign Logo" className="logo-image" />
          </div>
          <div className="header-center">
            <h1>Document Requests</h1>
          </div>
          <div className="header-right"></div>
        </div>
      </header>

      <main className="container">
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

        {viewMode === 'list' && (
          <div className="requests-list-container">
            <h2>Received Document Requests</h2>
            
            {requests.length === 0 ? (
              <div className="no-requests">
                <p>No document requests have been received yet.</p>
              </div>
            ) : (
              <div className="requests-list">
                {requests.map(request => (
                  <div key={request.id} className={`request-card status-${request.status}`} onClick={() => fetchRequestDetails(request.id)}>
                    <div className="request-header">
                      <h3>{request.property_location || 'Unknown property'}</h3>
                      <span className={`status-badge ${request.status}`}>{request.status}</span>
                    </div>
                    <div className="request-details">
                      <div className="request-info">
                        <span className="info-label">From</span>
                        <span className="info-value">{request.buyer_name || 'Unknown buyer'}</span>
                      </div>
                      <div className="request-info">
                        <span className="info-label">Property Ref</span>
                        <span className="info-value">{request.property_reference || 'No reference'}</span>
                      </div>
                      <div className="request-info">
                        <span className="info-label">Requested</span>
                        <span className="info-value">{new Date(request.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {viewMode === 'detail' && detailedRequest && (
          <div className="request-detail-container">
            <div className="detail-header">
              <button className="back-button" onClick={handleBackToList}>
                &larr; Back to all requests
              </button>
              <h2>Document Request Details</h2>
            </div>
            
            <div className="detail-card">
              <div className="detail-section">
                <h3>Request Information</h3>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="detail-label">Status</span>
                    <span className={`status-badge ${detailedRequest.status}`}>{detailedRequest.status}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Requested On</span>
                    <span className="detail-value">{new Date(detailedRequest.created_at).toLocaleString()}</span>
                  </div>
                  {detailedRequest.message && (
                    <div className="detail-item full-width">
                      <span className="detail-label">Message from Buyer</span>
                      <div className="detail-message">{detailedRequest.message}</div>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="detail-section">
                <h3>Buyer Information</h3>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="detail-label">Name</span>
                    <span className="detail-value">{detailedRequest.buyer_name || 'Not available'}</span>
                  </div>
                  {detailedRequest.buyer_email && (
                    <div className="detail-item">
                      <span className="detail-label">Email</span>
                      <span className="detail-value">{detailedRequest.buyer_email}</span>
                    </div>
                  )}
                  {detailedRequest.buyer_phone && (
                    <div className="detail-item">
                      <span className="detail-label">Phone</span>
                      <span className="detail-value">{detailedRequest.buyer_phone}</span>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="detail-section">
                <h3>Property Information</h3>
                <div className="detail-grid">
                  <div className="detail-item">
                    <span className="detail-label">Location</span>
                    <span className="detail-value">{detailedRequest.property_location || 'Not available'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Reference</span>
                    <span className="detail-value">{detailedRequest.property_reference || 'Not available'}</span>
                  </div>
                  {detailedRequest.property_type && (
                    <div className="detail-item">
                      <span className="detail-label">Type</span>
                      <span className="detail-value">{detailedRequest.property_type}</span>
                    </div>
                  )}
                  {detailedRequest.property_price && (
                    <div className="detail-item">
                      <span className="detail-label">Price</span>
                      <span className="detail-value">₹{detailedRequest.property_price.toLocaleString()}</span>
                    </div>
                  )}
                </div>
              </div>
              
              {detailedRequest.status === 'pending' && (
                <div className="detail-section actions-section">
                  <h3>Handle Request</h3>
                  
                  <div className="action-options">
                    <div className="action-option">
                      <h4>Approve Access</h4>
                      <div className="form-group">
                        <label htmlFor="expiryDays">Access will expire after (days)</label>
                        <input 
                          type="number" 
                          id="expiryDays" 
                          min="1" 
                          max="30" 
                          value={expiryDays}
                          onChange={(e) => setExpiryDays(parseInt(e.target.value))}
                          className="form-control"
                        />
                      </div>
                      <button 
                        className="action-button approve-button"
                        onClick={handleApproveRequest}
                        disabled={processing}
                      >
                        {processing ? 'Processing...' : 'Approve Request'}
                      </button>
                    </div>
                    
                    <div className="action-option">
                      <h4>Reject Access</h4>
                      <div className="form-group">
                        <label htmlFor="rejectionReason">Reason for rejection</label>
                        <textarea 
                          id="rejectionReason"
                          value={rejectionReason}
                          onChange={(e) => setRejectionReason(e.target.value)}
                          placeholder="Explain why you're rejecting this request..."
                          rows={3}
                          className="form-control"
                        ></textarea>
                      </div>
                      <button 
                        className="action-button reject-button"
                        onClick={handleRejectRequest}
                        disabled={processing}
                      >
                        {processing ? 'Processing...' : 'Reject Request'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
              
              {detailedRequest.status === 'approved' && (
                <div className="detail-section">
                  <h3>Approval Information</h3>
                  <div className="detail-grid">
                    <div className="detail-item">
                      <span className="detail-label">Approved On</span>
                      <span className="detail-value">
                        {detailedRequest.approved_at ? new Date(detailedRequest.approved_at).toLocaleString() : 'Not recorded'}
                      </span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Access Expires On</span>
                      <span className="detail-value">
                        {detailedRequest.expiry_date ? new Date(detailedRequest.expiry_date).toLocaleString() : 'No expiration'}
                      </span>
                    </div>
                  </div>
                </div>
              )}
              
              {detailedRequest.status === 'rejected' && (
                <div className="detail-section">
                  <h3>Rejection Information</h3>
                  <div className="detail-grid">
                    <div className="detail-item">
                      <span className="detail-label">Rejected On</span>
                      <span className="detail-value">
                        {detailedRequest.rejected_at ? new Date(detailedRequest.rejected_at).toLocaleString() : 'Not recorded'}
                      </span>
                    </div>
                    {detailedRequest.rejection_reason && (
                      <div className="detail-item full-width">
                        <span className="detail-label">Reason for Rejection</span>
                        <div className="detail-message">{detailedRequest.rejection_reason}</div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      <footer>
        <div className="container full-width">
          <p>&copy; 2025 SureSign - Online Property Registration Portal. All Rights Reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default DocumentRequests; 