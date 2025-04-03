import React, { useState } from 'react';
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
    description: '',
    legalDocuments: [],
    images: []
  });
  const [previewImages, setPreviewImages] = useState([]);
  const [errors, setErrors] = useState({});

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
    setPropertyData({...propertyData, legalDocuments: [...propertyData.legalDocuments, ...files]});
  };

  const validateStep1 = () => {
    const newErrors = {};

    if (previewImages.length < 5) {
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

  const generateReferenceNumber = () => {
    const prefix = "PROP";
    const randomDigits = Math.floor(10000 + Math.random() * 90000);
    const timestamp = Date.now().toString().slice(-4);
    return `${prefix}-${randomDigits}-${timestamp}`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateStep2()) {
      return;
    }

    setLoading(true);

    // In a real app, upload to server
    // For demo, we'll simulate API call and store in localStorage

    try {
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1500));

      const referenceNumber = generateReferenceNumber();

      // Get existing properties or initialize empty array
      const existingProperties = localStorage.getItem('sellerProperties')
        ? JSON.parse(localStorage.getItem('sellerProperties'))
        : [];

      // Create new property object with reference number
      const newProperty = {
        ...propertyData,
        referenceNumber,
        createdAt: new Date().toISOString(),
        status: 'active',
        // Convert File objects to URLs for demo (in real app, you'd have URLs from server)
        images: previewImages,
        legalDocuments: propertyData.legalDocuments.map(doc => doc.name)
      };

      // Add to existing properties
      const updatedProperties = [...existingProperties, newProperty];

      // Save to localStorage
      localStorage.setItem('sellerProperties', JSON.stringify(updatedProperties));

      alert('Property listed successfully!');
      navigate('/list-properties');
    } catch (error) {
      console.error('Error listing property:', error);
      alert('Failed to list property. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="add-property">
      <div className="gov-banner">Government of India</div>

      <header>
        <div className="container">
          <div className="logo-placeholder">Logo</div>
          <h1 className="header-title">ADD NEW PROPERTY</h1>
          <p className="header-subtitle">Ministry of Housing and Urban Affairs</p>
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
                            <img src={preview} alt={`Property ${index + 1}`} />
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
                    className="btn btn-primary"
                    onClick={handleNext}
                  >
                    Next
                  </button>
                </div>
              </div>