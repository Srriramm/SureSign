import React, { useState } from 'react';
import { Link, useParams, useNavigate, useLocation } from 'react-router-dom';
import { storeAuthData } from '../../utils/authUtils';
import './UserLogin.css';

function UserLogin() {
  const { userType } = useParams(); // Get user type from URL
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  // Check if we were redirected from a protected route
  const from = location.state?.from?.pathname || null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });

    // Clear error for the field if it exists
    if (errors[name]) {
      setErrors({...errors, [name]: null});
    }
  };

  const validateForm = () => {
    const newErrors = {};

    // Email validation
    if (!formData.email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = "Please enter a valid email address";
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = "Password is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate form fields
    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      // Create FormData to match backend route
      const formDataToSend = new FormData();
      formDataToSend.append('email', formData.email);
      formDataToSend.append('password', formData.password);

      // Send login request to the backend
      const response = await fetch(`http://localhost:8000/auth/login/${userType}`, {
        method: 'POST',
        body: formDataToSend
      });

      // Parse the response
      const data = await response.json();

      // Handle errors from the backend
      if (!response.ok) {
        throw new Error(data.detail || 'Login failed');
      }

      // Store auth data using our utilities
      storeAuthData(userType, {
        access_token: data.access_token,
        user_id: data.user_id,
        email: formData.email
      });

      // If we have a previous location, navigate back to it
      if (from) {
        navigate(from, { replace: true });
      } else {
        // Otherwise, navigate based on user type
        const navigationRoutes = {
          'seller': '/list-properties',
          'buyer': '/buyer-dashboard'
        };
        navigate(navigationRoutes[userType] || '/dashboard');
      }

    } catch (error) {
      // Set error message for display
      setErrors({
        auth: error.message || "An error occurred during login. Please try again.",
      });
    } finally {
      // Ensure loading state is reset
      setLoading(false);
    }
  };

  return (
    <div className="user-login">
      <header>
        <div className="container">
        <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign Logo" className="login-logo-image" />
          <h1 className="login-header-title">{userType.toUpperCase()} LOGIN</h1>
        </div>
      </header>

      <main className="container">
        <div className="login-card">
          <h2>Login to Your {userType.charAt(0).toUpperCase() + userType.slice(1)} Account</h2>
          <p className="form-subtitle">
            {userType === 'seller' 
              ? 'Access your property listings and manage your profile'
              : 'Browse and explore available properties'}
          </p>

          {errors.auth && (
            <div className="auth-error">
              {errors.auth}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="email">Email Address</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="Enter your email"
              />
              {errors.email && <p className="field-error">{errors.email}</p>}
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Enter your password"
              />
              {errors.password && <p className="field-error">{errors.password}</p>}
            </div>

            <div className="form-actions">
              <div className="remember-forgot">
                <label className="remember-me">
                  <input type="checkbox" /> Remember me
                </label>
                <Link to="/forgot-password" className="forgot-password">
                  Forgot Password?
                </Link>
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-login"
                disabled={loading}
              >
                {loading ? 'Logging in...' : 'Login'}
              </button>
            </div>
          </form>

          <div className="register-prompt">
            <p>Don't have an account?</p>
            <Link to={`/register/${userType}`} className="btn btn-secondary btn-register">
              Register as a {userType === 'seller' ? 'Property Seller' : 'Property Buyer'}
            </Link>
          </div>
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

export default UserLogin;