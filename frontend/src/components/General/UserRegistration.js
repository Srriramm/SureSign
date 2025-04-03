import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './UserRegistration.css';
import WebcamCapture from './WebcamCapture';

function UserRegistration({ userType }) {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    mobile_number: '',
    password: '',
    confirmPassword: '',
    selfie: null
  });
  const [passwordError, setPasswordError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    if (name === 'password' || name === 'confirmPassword') {
      setPasswordError('');
    }
  };

  const handleSelfieCapture = (imageData) => {
    setFormData(prev => ({ ...prev, selfie: imageData }));
  };

  const validatePasswords = () => {
    if (formData.password !== formData.confirmPassword) {
      setPasswordError('Passwords do not match');
      return false;
    }

    if (formData.password.length < 8) {
      setPasswordError('Password must be at least 8 characters long');
      return false;
    }

    return true;
  };

  const handleBack = () => {
    setStep(prev => Math.max(1, prev - 1));
  };

  const completeRegistration = async () => {
    setLoading(true);
    try {
      // Prepare form data for registration
      const formDataToSend = new FormData();
      formDataToSend.append('name', formData.name);
      formDataToSend.append('mobile_number', formData.mobile_number);
      formDataToSend.append('email', formData.email);
      formDataToSend.append('password', formData.password);

      // Prepare selfie file
      const selfieFile = dataURLtoFile(formData.selfie, 'selfie.jpg');
      formDataToSend.append('selfie', selfieFile);

      // Send complete registration request
      const response = await fetch(`http://localhost:8000/auth/complete_registration/${userType}`, {
        method: 'POST',
        body: formDataToSend
      });

      const data = await response.json();
      
      if (response.ok) {
        alert('Registration successful!');
        // Navigate based on user type
        navigate(userType === 'seller' ? '/list-properties' : '/dashboard');
        return true;
      } else {
        const errorMessage = data.detail || 'Registration failed';
        console.error('Registration error:', errorMessage);
        alert(errorMessage);
        return false;
      }
    } catch (error) {
      console.error('Error during registration:', error);
      alert('Registration failed. Please check your connection and try again.');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const dataURLtoFile = (dataurl, filename) => {
    const arr = dataurl.split(',');
    const mime = arr[0].match(/:(.*?);/)[1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
      u8arr[n] = bstr.charCodeAt(n);
    }
    return new File([u8arr], filename, { type: mime });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (step === 1) {
      if (!formData.name || !formData.email || !formData.mobile_number || !formData.password || !formData.confirmPassword) {
        alert('Please fill all required fields');
        return;
      }

      if (!validatePasswords()) {
        return;
      }

      // Move to selfie capture step
      setStep(2);
    } else if (step === 2) {
      if (!formData.selfie) {
        alert('Please capture your selfie');
        return;
      }

      // Complete registration with all details
      const success = await completeRegistration();
      if (success) {
        // Reset form or navigate away
        setFormData({
          name: '',
          email: '',
          mobile_number: '',
          password: '',
          confirmPassword: '',
          selfie: null
        });
      }
    }
  };

  return (
    <div className="user-registration">

      <header>
        <div className="container header-container">
          <button onClick={() => navigate(-1)} className="back-button">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            Back
          </button>
          <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign Logo" className="registration-logo-image" />
          <h1 className="registration-header-title">{userType.toUpperCase()} REGISTRATION</h1>
        </div>
      </header>

      <main className="container">
        <div className="progress-bar">
          <div className={`step ${step >= 1 ? 'active' : ''}`}>
            <div className="step-number">1</div>
            <div className="step-text">Personal</div>
          </div>
          <div className="step-line"></div>
          <div className={`step ${step >= 2 ? 'active' : ''}`}>
            <div className="step-number">2</div>
            <div className="step-text">Identity</div>
          </div>
        </div>

        <div className="form-card compact-form">
          <form onSubmit={handleSubmit}>
            {step === 1 && (
              <div className="form-step">
                <h2>Personal Information</h2>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="name">Full Name*</label>
                    <input
                      type="text"
                      id="name"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="email">Email Address*</label>
                    <input
                      type="email"
                      id="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="mobile_number">Mobile Number*</label>
                    <input
                      type="tel"
                      id="mobile_number"
                      name="mobile_number"
                      value={formData.mobile_number}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="password">Password*</label>
                    <input
                      type="password"
                      id="password"
                      name="password"
                      value={formData.password}
                      onChange={handleChange}
                      minLength="8"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="confirmPassword">Confirm Password*</label>
                    <input
                      type="password"
                      id="confirmPassword"
                      name="confirmPassword"
                      value={formData.confirmPassword}
                      onChange={handleChange}
                      minLength="8"
                      required
                    />
                  </div>
                </div>

                {passwordError && (
                  <div className="form-error">
                    {passwordError}
                  </div>
                )}

                <div className="password-hint">
                  Minimum 8 characters required. Both passwords must match.
                </div>

                <div className="form-buttons">
                  <button type="submit" className="btn btn-primary">
                    Next
                  </button>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="form-step">
                <h2>Identity Verification</h2>
                <p className="form-subtitle">Take a selfie for identity verification</p>

                <div className="selfie-container">
                  <WebcamCapture onCapture={handleSelfieCapture} />
                </div>

                {formData.selfie && (
                  <div className="selfie-preview">
                    <h3>Preview:</h3>
                    <img src={formData.selfie} alt="Captured selfie" />
                  </div>
                )}

                <div className="form-buttons">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleBack}
                    disabled={loading}
                  >
                    Back
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={loading || !formData.selfie}
                  >
                    {loading ? 'Processing...' : 'Complete Registration'}
                  </button>
                </div>
              </div>
            )}
          </form>
        </div>
      </main>

      <footer>
        <div className="container">
          <p>&copy; 2025 Online Property Registration Portal. All Rights Reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default UserRegistration;