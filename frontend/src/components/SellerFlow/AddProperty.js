import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './AddProperty.css';

function AddProperty() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [propertyData, setPropertyData] = useState({
    location: '',
    squareFeet: '',
    rate: '',
    propertyType: '',
    area: '',
    description: '',
    legalDocuments: [],
    documentTypes: [],
    images: [],
    secureFilenames: []
  });
  const [previewImages, setPreviewImages] = useState([]);
  const [errors, setErrors] = useState({});
  const [documentType, setDocumentType] = useState('');
  const [propertyId, setPropertyId] = useState(null);

  // Function to handle image upload errors and retry with different methods
  const handleImageError = (e, index) => {
    e.target.onerror = null; // Prevent infinite error loops
    
    // Extract the secure filename and container from the image data attributes
    const secureFilename = e.target.dataset.secureFilename;
    const container = e.target.dataset.container || 'property-images';
    
    // First try direct image endpoint with container/filename
    if (secureFilename) {
      console.log(`Image error: trying direct endpoint with ${container}/${secureFilename}`);
      e.target.src = `http://localhost:8000/seller/images/${container}/${secureFilename}`;
      return;
    }
    
    // If no secure filename is available or the above fails, use placeholder
    console.log('Image error: using placeholder');
    e.target.src = "http://localhost:8000/seller/placeholder/320/240";
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setPropertyData({ ...propertyData, [name]: value });

    // Clear error for the field if it exists
    if (errors[name]) {
      setErrors({...errors, [name]: null});
    }
  };

  const handleImageUpload = (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    // Limit to max 10 images
    if (previewImages.length + files.length > 10) {
      setErrors({...errors, images: "Maximum 10 images allowed"});
      return;
    }

    // Create preview URLs for the images
    const newPreviewImages = [...previewImages];
    const newImages = [...propertyData.images];

    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = (event) => {
        newPreviewImages.push(event.target.result);
        setPreviewImages([...newPreviewImages]);
      };
      reader.readAsDataURL(file);
      newImages.push(file);
    });

    setPropertyData({...propertyData, images: newImages});

    // Clear error for images if it exists
    if (errors.images) {
      setErrors({...errors, images: null});
    }
  };

  const removeImage = (index) => {
    const updatedPreviews = [...previewImages];
    const updatedImages = [...propertyData.images];

    updatedPreviews.splice(index, 1);
    updatedImages.splice(index, 1);

    setPreviewImages(updatedPreviews);
    setPropertyData({...propertyData, images: updatedImages});
  };

  const handleDocumentUpload = (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0 || !documentType) {
      setErrors({...errors, documents: "Please select a document type before uploading"});
      return;
    }

    const newDocuments = [...propertyData.legalDocuments];
    const newDocumentTypes = [...propertyData.documentTypes];
    
    files.forEach(file => {
      newDocuments.push(file);
      newDocumentTypes.push(documentType);
    });
    
    setPropertyData({
      ...propertyData, 
      legalDocuments: newDocuments,
      documentTypes: newDocumentTypes
    });
    
    // Reset document type selection
    setDocumentType('');
    
    // Clear error if it exists
    if (errors.documents) {
      setErrors({...errors, documents: null});
    }
  };

  const removeDocument = (index) => {
    const updatedDocuments = [...propertyData.legalDocuments];
    const updatedTypes = [...propertyData.documentTypes];

    updatedDocuments.splice(index, 1);
    updatedTypes.splice(index, 1);

    setPropertyData({
      ...propertyData, 
      legalDocuments: updatedDocuments,
      documentTypes: updatedTypes
    });
  };

  const validateStep1 = () => {
    const newErrors = {};

    if (propertyData.images.length < 5) {
      newErrors.images = "Please upload at least 5 images";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validateStep2 = () => {
    const newErrors = {};

    if (!propertyData.location.trim()) {
      newErrors.location = "Location is required";
    }

    if (!propertyData.area.trim()) {
      newErrors.area = "Area is required";
    }

    if (!propertyData.squareFeet) {
      newErrors.squareFeet = "Square feet is required";
    } else if (isNaN(propertyData.squareFeet) || propertyData.squareFeet <= 0) {
      newErrors.squareFeet = "Please enter a valid area";
    }

    if (!propertyData.rate) {
      newErrors.rate = "Rate is required";
    } else if (isNaN(propertyData.rate) || propertyData.rate <= 0) {
      newErrors.rate = "Please enter a valid rate";
    }

    if (!propertyData.propertyType) {
      newErrors.propertyType = "Property type is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (step === 1 && validateStep1()) {
      setStep(2);
    }
  };

  const handleBack = () => {
    setStep(1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateStep2()) {
      return;
    }

    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        alert('Please login to continue');
        navigate('/login');
        return;
      }

      // Create FormData for the multipart/form-data request
      const formData = new FormData();
      formData.append('property_type', propertyData.propertyType);
      formData.append('square_feet', propertyData.squareFeet);
      formData.append('price', propertyData.rate);
      formData.append('area', propertyData.area);
      formData.append('description', propertyData.description || '');
      formData.append('location', propertyData.location);

      // Add images
      propertyData.images.forEach(image => {
        formData.append('images', image);
      });

      // Add documents and their types
      propertyData.legalDocuments.forEach(doc => {
        formData.append('documents', doc);
      });

      propertyData.documentTypes.forEach(type => {
        formData.append('document_types', type);
      });

      // Send request to backend API
      const response = await fetch('http://localhost:8000/seller/property', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create property listing');
      }

      const responseData = await response.json();
      console.log('Property created successfully:', responseData);
      
      // Store the property ID for potential image loading
      if (responseData.property && responseData.property.id) {
        setPropertyId(responseData.property.id);
      }
      
      // If we have image filenames, store them for direct access
      if (responseData.property && responseData.property.images && responseData.property.images.length > 0) {
        const imageData = responseData.property.images.map(img => {
          let secureFilename = null;
          let container = 'property-images';
          
          if (img.url && img.url.secure_filename) {
            secureFilename = img.url.secure_filename;
            container = img.url.container || container;
          }
          
          return { secureFilename, container };
        });
        
        // We could store this data if needed for later use
        console.log('Image data for direct access:', imageData);
        setPropertyData({...propertyData, secureFilenames: imageData});
      }
      
      alert('Property listed successfully!');
      navigate('/list-properties');
    } catch (error) {
      console.error('Error listing property:', error);
      alert(`Failed to list property: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="add-property">
      <header>
        <div className="container header-container">
          <div className="logo-title-section">
            <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign Logo" className="add-logo-image" />
            <h1 className="add-header-title">ADD NEW PROPERTY</h1>
          </div>
        </div>
      </header>

      <main className="container">
        <div className="progress-bar">
          <div className={`step ${step >= 1 ? 'active' : ''}`}>
            <div className="step-number">1</div>
            <div className="step-text">Upload Images</div>
          </div>
          <div className="step-line"></div>
          <div className={`step ${step >= 2 ? 'active' : ''}`}>
            <div className="step-number">2</div>
            <div className="step-text">Property Details</div>
          </div>
        </div>

        <div className="form-card">
          <form onSubmit={handleSubmit}>
            {step === 1 && (
              <div className="form-step">
                <h2>Upload Property Images</h2>
                <p className="form-subtitle">Please upload 5-10 images of your property</p>

                <div className="upload-container">
                  <div className="upload-area">
                    <input
                      type="file"
                      id="property-images"
                      multiple
                      accept="image/*"
                      onChange={handleImageUpload}
                      className="file-input"
                    />
                    <label htmlFor="property-images" className="upload-label">
                      <div className="upload-icon">+</div>
                      <p>Click or drag images here</p>
                      <span className="upload-hint">5-10 images required</span>
                    </label>
                  </div>

                  {errors.images && <p className="error-message">{errors.images}</p>}

                  {previewImages.length > 0 && (
                    <div className="image-preview-container">
                      <h3>Uploaded Images ({previewImages.length}/10)</h3>
                      <div className="image-preview-grid">
                        {previewImages.map((preview, index) => (
                          <div key={index} className="image-preview-item">
                            <img 
                              src={preview} 
                              alt={`Property ${index + 1}`} 
                              data-secure-filename={propertyData.secureFilenames && propertyData.secureFilenames[index] ? propertyData.secureFilenames[index].secureFilename : ''}
                              data-container={propertyData.secureFilenames && propertyData.secureFilenames[index] ? propertyData.secureFilenames[index].container : 'property-images'}
                              onError={(e) => handleImageError(e, index)}
                            />
                            <button
                              type="button"
                              className="remove-image-btn"
                              onClick={() => removeImage(index)}
                            >
                              ×
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="form-buttons">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => navigate('/list-properties')}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleNext}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="form-step">
                <h2>Property Details</h2>
                <p className="form-subtitle">Please provide details about your property</p>

                <div className="form-group">
                  <label htmlFor="location">Location</label>
                  <input
                    type="text"
                    id="location"
                    name="location"
                    value={propertyData.location}
                    onChange={handleChange}
                    className={errors.location ? 'form-control error' : 'form-control'}
                    placeholder="Enter property location"
                  />
                  {errors.location && <p className="error-message">{errors.location}</p>}
                </div>

                <div className="form-group">
                  <label htmlFor="area">Area/Neighborhood</label>
                  <input
                    type="text"
                    id="area"
                    name="area"
                    value={propertyData.area}
                    onChange={handleChange}
                    className={errors.area ? 'form-control error' : 'form-control'}
                    placeholder="Enter area or neighborhood"
                  />
                  {errors.area && <p className="error-message">{errors.area}</p>}
                </div>

                <div className="form-group">
                  <label htmlFor="propertyType">Property Type</label>
                  <select
                    id="propertyType"
                    name="propertyType"
                    value={propertyData.propertyType}
                    onChange={handleChange}
                    className={errors.propertyType ? 'form-control error' : 'form-control'}
                  >
                    <option value="">Select property type</option>
                    <option value="Residential">Residential</option>
                    <option value="Commercial">Commercial</option>
                    <option value="Land">Land</option>
                  </select>
                  {errors.propertyType && <p className="error-message">{errors.propertyType}</p>}
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="squareFeet">Square Feet</label>
                    <input
                      type="number"
                      id="squareFeet"
                      name="squareFeet"
                      value={propertyData.squareFeet}
                      onChange={handleChange}
                      className={errors.squareFeet ? 'form-control error' : 'form-control'}
                      placeholder="Enter area in sq ft"
                    />
                    {errors.squareFeet && <p className="error-message">{errors.squareFeet}</p>}
                  </div>

                  <div className="form-group">
                    <label htmlFor="rate">Rate (per sq ft)</label>
                    <input
                      type="number"
                      id="rate"
                      name="rate"
                      value={propertyData.rate}
                      onChange={handleChange}
                      className={errors.rate ? 'form-control error' : 'form-control'}
                      placeholder="Enter rate per sq ft"
                    />
                    {errors.rate && <p className="error-message">{errors.rate}</p>}
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="description">Description</label>
                  <textarea
                    id="description"
                    name="description"
                    value={propertyData.description}
                    onChange={handleChange}
                    className="form-control"
                    placeholder="Describe your property"
                    rows="4"
                  ></textarea>
                </div>

                <div className="form-group">
                  <label>Legal Documents</label>
                  <div className="document-upload-container">
                    <div className="document-type-selection">
                      <select
                        value={documentType}
                        onChange={(e) => setDocumentType(e.target.value)}
                        className="form-control"
                      >
                        <option value="">Select document type</option>
                        <option value="Title Deed">Title Deed</option>
                        <option value="Land Survey">Land Survey</option>
                        <option value="Property Tax Receipt">Property Tax Receipt</option>
                        <option value="Ownership Certificate">Ownership Certificate</option>
                        <option value="Zoning Approval">Zoning Approval</option>
                        <option value="Other">Other</option>
                      </select>
                    </div>
                    
                    <div className="upload-area">
                      <input
                        type="file"
                        id="legalDocuments"
                        accept=".pdf,.doc,.docx"
                        onChange={handleDocumentUpload}
                        className="file-input"
                      />
                      <label htmlFor="legalDocuments" className="upload-label">
                        <div className="upload-icon">+</div>
                        <p>Click to upload document</p>
                        <span className="upload-hint">Upload legal documents (PDF, DOC)</span>
                      </label>
                    </div>
                  </div>
                  
                  {errors.documents && <p className="error-message">{errors.documents}</p>}
                  
                  {propertyData.legalDocuments.length > 0 && (
                    <div className="document-list">
                      <h3>Uploaded Documents</h3>
                      <ul>
                        {propertyData.legalDocuments.map((doc, index) => (
                          <li key={index} className="document-item">
                            <span className="document-name">{doc.name}</span>
                            <span className="document-type">({propertyData.documentTypes[index]})</span>
                            <button
                              type="button"
                              className="remove-document-btn"
                              onClick={() => removeDocument(index)}
                            >
                              ×
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                <div className="form-buttons">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleBack}
                  >
                    Back
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={loading}
                  >
                    {loading ? 'Submitting...' : 'Submit Property'}
                  </button>
                </div>
              </div>
            )}
          </form>
        </div>
      </main>

      <footer>
        <div className="container">
          <p>&copy; {new Date().getFullYear()} Online Property Registration Portal. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default AddProperty;