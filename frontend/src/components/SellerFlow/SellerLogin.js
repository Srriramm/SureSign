import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './SellerLogin.css';

function SellerLogin() {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

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

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      // In a real app, this would be an API call to authenticate
      // For demo purposes, we'll simulate a login check
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Mock authentication logic
      // In a real app, you would verify credentials against a backend
      const mockUsers = JSON.parse(localStorage.getItem('sellers') || '[]');
      const user = mockUsers.find(user => user.email === formData.email);

      if (user && user.password === formData.password) {
        // Store user info in localStorage (in a real app, store a token)
        localStorage.setItem('currentSellerId', user.id);
        localStorage.setItem('sellerName', user.name);
        localStorage.setItem('sellerEmail', user.email);

        // Navigate to list properties page
        navigate('/list-properties');
      } else {
        setErrors({
          auth: "Invalid email or password"
        });
      }
    } catch (error) {
      console.error('Login error:', error);
      setErrors({
        auth: "An error occurred during login. Please try again."
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="seller-login">
      <div className="gov-banner">Government of India</div>

      <header>
        <div className="container">
          <div className="logo-placeholder">Logo</div>
          <h1 className="header-title">SELLER LOGIN</h1>
          <p className="header-subtitle">Ministry of Housing and Urban Affairs</p>
        </div>
      </header>

      <main className="container">
        <div className="login-card">
          <h2>Login to Your Seller Account</h2>
          <p className="form-subtitle">Access your property listings and manage your profile</p>

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
                <Link to="/seller-forgot-password" className="forgot-password">
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
            <Link to="/seller-registration" className="btn btn-secondary btn-register">
              Register as a Seller
            </Link>
          </div>
        </div>
      </main>

      <footer>
        <div className="container">
          <p>&copy; 2025 Online Property Registration Portal. All Rights Reserved.</p>
          <p>Government of India</p>
        </div>
      </footer>
    </div>
  );
}

export default SellerLogin;