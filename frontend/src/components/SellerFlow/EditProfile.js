import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './EditProfile.css';

function EditProfile() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    mobile_number: '',
    profile_image: null
  });
  const [previewUrl, setPreviewUrl] = useState(null);
  const [submitStatus, setSubmitStatus] = useState({ loading: false, error: null });

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          navigate('/login');
          return;
        }

        const response = await fetch('http://localhost:8000/seller/get-seller', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch profile data');
        }

        const data = await response.json();
        setFormData({
          name: data.name || '',
          email: data.email || '',
          mobile_number: data.mobile_number || '',
          profile_image: null
        });

        // Set the preview URL for the existing profile image
        if (data._id) {
          setPreviewUrl(`http://localhost:8000/seller/image/${data._id}`);
        }

        setLoading(false);
      } catch (err) {
        console.error('Error fetching profile:', err);
        setError(err.message);
        setLoading(false);
      }
    };

    fetchProfile();
  }, [navigate]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData(prev => ({
        ...prev,
        profile_image: file
      }));

      // Create preview URL
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewUrl(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitStatus({ loading: true, error: null });

    try {
      const token = localStorage.getItem('token');
      const formDataToSend = new FormData();
      
      // Append text fields
      formDataToSend.append('name', formData.name);
      formDataToSend.append('email', formData.email);
      formDataToSend.append('mobile_number', formData.mobile_number);
      
      // Append image if selected
      if (formData.profile_image) {
        formDataToSend.append('profile_image', formData.profile_image);
      }

      const response = await fetch('http://localhost:8000/seller/update-profile', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formDataToSend
      });

      if (!response.ok) {
        throw new Error('Failed to update profile');
      }

      // Navigate back to the listings page after successful update
      navigate('/list-properties');
    } catch (err) {
      console.error('Error updating profile:', err);
      setSubmitStatus({ loading: false, error: err.message });
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading profile data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <h3>Error Loading Profile</h3>
        <p>{error}</p>
        <button onClick={() => window.location.reload()} className="btn btn-primary">
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="edit-profile">
      <header>
        <div className="container header-container">
          <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign Logo" className="logo-image" />
          <h1 className="header-title">Edit Profile</h1>
        </div>
      </header>

      <main className="container">
        <div className="edit-profile-form">
          <form onSubmit={handleSubmit}>
            <div className="profile-image-section">
              <div className="profile-image-container">
                <img 
                  src={previewUrl || '/placeholder.jpg'} 
                  alt="Profile Preview" 
                  className="profile-preview"
                />
                <div className="image-upload-overlay">
                  <label htmlFor="profile_image" className="upload-label">
                    Change Photo
                  </label>
                  <input
                    type="file"
                    id="profile_image"
                    name="profile_image"
                    accept="image/*"
                    onChange={handleImageChange}
                    className="hidden-input"
                  />
                </div>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="name">Full Name</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="mobile_number">Mobile Number</label>
              <input
                type="tel"
                id="mobile_number"
                name="mobile_number"
                value={formData.mobile_number}
                onChange={handleInputChange}
                required
              />
            </div>

            {submitStatus.error && (
              <div className="error-message">
                {submitStatus.error}
              </div>
            )}

            <div className="form-actions">
              <button 
                type="button" 
                className="btn btn-outline"
                onClick={() => navigate('/list-properties')}
              >
                Cancel
              </button>
              <button 
                type="submit" 
                className="btn btn-primary"
                disabled={submitStatus.loading}
              >
                {submitStatus.loading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}

export default EditProfile; 