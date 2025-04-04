import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { getToken } from '../../utils/authUtils';

/**
 * ProtectedRoute component that checks for authentication
 * before rendering child components.
 * 
 * If not authenticated, redirects to login page.
 */
function ProtectedRoute({ children, userType = 'seller' }) {
  const [isAuthenticated, setIsAuthenticated] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const location = useLocation();

  useEffect(() => {
    const checkAuth = async () => {
      const token = getToken(userType);
      
      if (!token) {
        setIsAuthenticated(false);
        setIsLoading(false);
        return;
      }

      try {
        // Validate the token by making a request to the backend
        const response = await fetch(`http://localhost:8000/auth/validate-token`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }).catch(() => {
          // If fetch fails (network error, etc.), consider user not authenticated
          setIsAuthenticated(false);
          return null;
        });

        // If the response is ok and token is valid
        if (response && response.ok) {
          setIsAuthenticated(true);
        } else {
          // If token is invalid, clear localStorage
          localStorage.removeItem(`${userType}_token`);
          setIsAuthenticated(false);
        }
      } catch (error) {
        console.error('Error validating token:', error);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, [userType]);

  if (isLoading) {
    // Return loading indicator if still checking authentication
    return <div className="loading">Loading...</div>;
  }

  if (!isAuthenticated) {
    // Redirect to login page if not authenticated
    // Save the current location for redirection after login
    return <Navigate to={`/login/${userType}`} state={{ from: location }} replace />;
  }

  // Render children if authenticated
  return children;
}

export default ProtectedRoute; 