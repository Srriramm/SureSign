import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import './LawyerVerificationPage.css';

function LawyerVerificationPage() {
  const { propertyId } = useParams();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [property, setProperty] = useState(null);
  const [verification, setVerification] = useState(null);
  const [buyerName, setBuyerName] = useState('');
  const [documents, setDocuments] = useState([]);
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [showVerificationForm, setShowVerificationForm] = useState(false);
  const [verificationData, setVerificationData] = useState({
    status: 'pending',
    notes: '',
    issues_details: ''
  });
  const [notification, setNotification] = useState(null);
  const [verificationSubmitted, setVerificationSubmitted] = useState(false);

  useEffect(() => {
    if (!token || !propertyId) {
      setError('Missing required parameters');
      setLoading(false);
      return;
    }
    
    const fetchVerificationDetails = async () => {
      try {
        setLoading(true);
        
        const response = await fetch(
          `http://localhost:8000/buyer/lawyer/verification/${propertyId}?token=${encodeURIComponent(token)}`
        );
        
        if (!response.ok) {
          if (response.status === 401) {
            throw new Error('Verification link has expired or is invalid');
          } else {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to load verification details');
          }
        }
        
        const data = await response.json();
        setVerification(data.verification);
        setProperty(data.property);
        setBuyerName(data.buyer_name);
        
        // If status is already set, pre-fill the form
        if (data.verification.verification_status !== 'pending') {
          setVerificationData({
            status: data.verification.verification_status,
            notes: data.verification.verification_notes || '',
            issues_details: data.verification.issues_details || ''
          });
          setVerificationSubmitted(true);
        }
        
        // Format documents for display
        if (data.property.documents && data.property.documents.length > 0) {
          setDocuments(data.property.documents);
        }
        
      } catch (err) {
        console.error('Error fetching verification details:', err);
        setError(err.message || 'Failed to load verification details');
      } finally {
        setLoading(false);
      }
    };
    
    fetchVerificationDetails();
  }, [propertyId, token]);
  
  const getPublicImageUrl = (index) => {
    // Create a URL that will be handled by the backend to serve property images
    return `http://localhost:8000/buyer/property-image/${propertyId}/${index}`;
  };
  
  const handleImageClick = (index) => {
    setSelectedImageIndex(index);
  };
  
  const handleImageError = (e) => {
    console.log('Image loading error');
    e.target.src = '/placeholder.jpg';
  };
  
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setVerificationData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  const handleStatusChange = (e) => {
    const status = e.target.value;
    setVerificationData(prev => ({
      ...prev,
      status
    }));
  };
  
  const handleSubmitVerification = async (e) => {
    e.preventDefault();
    
    try {
      setLoading(true);
      
      const response = await fetch(
        `http://localhost:8000/buyer/lawyer/verification/${propertyId}?token=${encodeURIComponent(token)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(verificationData)
        }
      );
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to submit verification');
      }
      
      const data = await response.json();
      setVerification(data.verification);
      setVerificationSubmitted(true);
      setShowVerificationForm(false);
      
      setNotification({
        type: 'success',
        message: `Verification status updated to "${data.verification.verification_status}"`
      });
      
      // Clear notification after 5 seconds
      setTimeout(() => {
        setNotification(null);
      }, 5000);
      
    } catch (err) {
      console.error('Error submitting verification:', err);
      setNotification({
        type: 'error',
        message: err.message || 'Failed to submit verification'
      });
    } finally {
      setLoading(false);
    }
  };
  
  const handleDocumentDownload = (documentIndex) => {
    if (!token || !propertyId) {
      setNotification({
        type: 'error',
        message: 'Missing required parameters for download'
      });
      return;
    }
    
    // Create the download URL with token
    const downloadUrl = `http://localhost:8000/buyer/lawyer/property-document/${propertyId}/${documentIndex}?token=${encodeURIComponent(token)}`;
    
    // Open in a new tab to trigger download
    window.open(downloadUrl, '_blank');
    
    setNotification({
      type: 'info',
      message: 'Document download started...'
    });
    
    // Clear notification after 3 seconds
    setTimeout(() => {
      setNotification(null);
    }, 3000);
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
  
  if (loading) {
    return (
      <div className="lawyer-verification-page">
        <header className="header">
          <div className="logo">
            <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign" />
            <h1>SureSign Legal Verification</h1>
          </div>
        </header>
        <main className="main-content">
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Loading verification details...</p>
          </div>
        </main>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="lawyer-verification-page">
        <header className="header">
          <div className="logo">
            <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign" />
            <h1>SureSign Legal Verification</h1>
          </div>
        </header>
        <main className="main-content">
          <div className="error-container">
            <div className="error-icon">⚠️</div>
            <h2>Error</h2>
            <p>{error}</p>
            <p>The verification link may have expired or is invalid. Please contact the buyer for a new verification link.</p>
          </div>
        </main>
      </div>
    );
  }
  
  if (!property || !verification) {
    return (
      <div className="lawyer-verification-page">
        <header className="header">
          <div className="logo">
            <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign" />
            <h1>SureSign Legal Verification</h1>
          </div>
        </header>
        <main className="main-content">
          <div className="error-container">
            <h2>Error</h2>
            <p>Property or verification details not found.</p>
          </div>
        </main>
      </div>
    );
  }
  
  return (
    <div className="lawyer-verification-page">
      <header className="header">
        <div className="logo">
          <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign" />
          <h1>SureSign Legal Verification</h1>
        </div>
      </header>
      
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
      
      <main className="main-content">
        <div className="verification-details-card">
          <h2>Legal Verification Request</h2>
          
          <div className="verification-info">
            <p><strong>Requested by:</strong> {buyerName}</p>
            <p><strong>Requested on:</strong> {new Date(verification.created_at).toLocaleString()}</p>
            <p><strong>Verification Status:</strong> {verification.verification_status}</p>
            
            {verification.updated_at && (
              <p><strong>Last Updated:</strong> {new Date(verification.updated_at).toLocaleString()}</p>
            )}
            
            {!verificationSubmitted && (
              <div className="verification-actions">
                <button 
                  className="btn-verify" 
                  onClick={() => setShowVerificationForm(true)}
                  disabled={loading}
                >
                  Submit Verification
                </button>
              </div>
            )}
          </div>
          
          {showVerificationForm && (
            <div className="verification-form-container">
              <h3>Submit Your Verification</h3>
              <form onSubmit={handleSubmitVerification} className="verification-form">
                <div className="form-group">
                  <label>Verification Status:</label>
                  <div className="radio-group">
                    <label className="radio-label">
                      <input
                        type="radio"
                        name="status"
                        value="verified"
                        checked={verificationData.status === 'verified'}
                        onChange={handleStatusChange}
                      />
                      <span className="radio-text">Verified - Documents are valid</span>
                    </label>
                    
                    <label className="radio-label">
                      <input
                        type="radio"
                        name="status"
                        value="issues_found"
                        checked={verificationData.status === 'issues_found'}
                        onChange={handleStatusChange}
                      />
                      <span className="radio-text">Issues Found - There are problems with the documents</span>
                    </label>
                  </div>
                </div>
                
                <div className="form-group">
                  <label htmlFor="notes">Notes:</label>
                  <textarea
                    id="notes"
                    name="notes"
                    value={verificationData.notes}
                    onChange={handleInputChange}
                    placeholder="Add any additional notes or comments about your verification..."
                    rows={3}
                  ></textarea>
                </div>
                
                {verificationData.status === 'issues_found' && (
                  <div className="form-group">
                    <label htmlFor="issues_details">
                      <span className="required">*</span> 
                      Please describe the issues found:
                    </label>
                    <textarea
                      id="issues_details"
                      name="issues_details"
                      value={verificationData.issues_details}
                      onChange={handleInputChange}
                      placeholder="Provide details about the issues found in the documents..."
                      rows={4}
                      required={verificationData.status === 'issues_found'}
                    ></textarea>
                  </div>
                )}
                
                <div className="form-actions">
                  <button
                    type="button"
                    className="btn-cancel"
                    onClick={() => setShowVerificationForm(false)}
                    disabled={loading}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn-submit"
                    disabled={loading || (verificationData.status === 'issues_found' && !verificationData.issues_details)}
                  >
                    {loading ? 'Submitting...' : 'Submit Verification'}
                  </button>
                </div>
              </form>
            </div>
          )}
        </div>
        
        <div className="property-details-card">
          <h2>Property Details</h2>
          
          <div className="property-header">
            <h3>{property.address || 'Unknown Location'}</h3>
            <p className="survey-number">Survey Number: {property.survey_number || 'Not specified'}</p>
          </div>
          
          <div className="property-info-grid">
            <div className="property-info-item">
              <span className="info-label">Plot Size</span>
              <span className="info-value">{property.plot_size || 'N/A'} sq.ft</span>
            </div>
            
            <div className="property-info-item">
              <span className="info-label">Price</span>
              <span className="info-value">₹{property.price ? property.price.toLocaleString() : '0'}</span>
            </div>
            
            <div className="property-info-item full-width">
              <span className="info-label">Address</span>
              <span className="info-value">{property.address || 'Not specified'}</span>
            </div>
          </div>
          
          <div className="property-images">
            <h3>Property Images</h3>
            
            {property.images && property.images.length > 0 ? (
              <div className="image-gallery">
                <div className="main-image">
                  <img 
                    src={getPublicImageUrl(selectedImageIndex)} 
                    alt={`Property view ${selectedImageIndex + 1}`}
                    onError={handleImageError}
                  />
                </div>
                
                {property.images.length > 1 && (
                  <div className="thumbnail-row">
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
            ) : (
              <p className="no-images">No images available</p>
            )}
          </div>
        </div>
        
        <div className="documents-card">
          <h2>Property Documents</h2>
          
          {documents.length > 0 ? (
            <div className="documents-list">
              {documents.map((doc, index) => (
                <div key={index} className="document-item">
                  <div className="document-icon">📄</div>
                  <div className="document-info">
                    <span className="document-title">{getDocumentTypeLabel(doc.type) || `Document ${index + 1}`}</span>
                    <span className="document-filename">{doc.document_name || `document-${index + 1}`}</span>
                  </div>
                  <button 
                    className="btn-download" 
                    onClick={() => handleDocumentDownload(index)}
                    disabled={loading}
                  >
                    Download
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-documents">No documents available</p>
          )}
          
          <div className="verification-notice">
            <p>
              <strong>Note:</strong> Please download and carefully review all documents before submitting your verification.
              Your legal expertise is crucial for ensuring the property documents are valid and free from issues.
            </p>
          </div>
        </div>
      </main>
      
      <footer className="footer">
        <p>&copy; {new Date().getFullYear()} SureSign. All rights reserved.</p>
        <p>This verification link is temporary and will expire. Please complete your verification promptly.</p>
      </footer>
    </div>
  );
}

export default LawyerVerificationPage; 