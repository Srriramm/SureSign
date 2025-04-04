/**
 * Authentication utility functions
 */

/**
 * Get the token for the specified user type
 * @param {string} userType - The user type ('buyer' or 'seller')
 * @returns {string|null} The token or null if not found
 */
export const getToken = (userType) => {
  // If userType is provided, get the specific token
  if (userType) {
    return localStorage.getItem(`${userType}_token`);
  }
  
  // Otherwise, try to determine from userType in localStorage
  const currentUserType = localStorage.getItem('userType');
  if (currentUserType) {
    return localStorage.getItem(`${currentUserType}_token`);
  }
  
  // Fallback to checking both tokens
  const buyerToken = localStorage.getItem('buyer_token');
  const sellerToken = localStorage.getItem('seller_token');
  
  // Return whichever token exists (prioritize the one matching the URL)
  if (window.location.pathname.includes('/buyer')) {
    return buyerToken || sellerToken;
  } else if (window.location.pathname.includes('/seller')) {
    return sellerToken || buyerToken;
  }
  
  // Final fallback
  return buyerToken || sellerToken || localStorage.getItem('token');
};

/**
 * Store authentication data in localStorage
 * @param {string} userType - The user type ('buyer' or 'seller')
 * @param {Object} data - Authentication data including token, user ID, etc.
 */
export const storeAuthData = (userType, data) => {
  localStorage.setItem(`${userType}_token`, data.access_token);
  localStorage.setItem(`${userType}_userId`, data.user_id);
  localStorage.setItem(`${userType}_userEmail`, data.email || '');
  localStorage.setItem('userType', userType);
};

/**
 * Clear authentication data for the specified user type
 * @param {string} userType - The user type ('buyer' or 'seller')
 */
export const clearAuthData = (userType) => {
  localStorage.removeItem(`${userType}_token`);
  localStorage.removeItem(`${userType}_userId`);
  localStorage.removeItem(`${userType}_userEmail`);
  
  // Only clear userType if it matches the current one
  if (localStorage.getItem('userType') === userType) {
    localStorage.removeItem('userType');
  }
};

/**
 * Check if user is authenticated for the specified user type
 * @param {string} userType - The user type ('buyer' or 'seller')
 * @returns {boolean} True if authenticated, false otherwise
 */
export const isAuthenticated = (userType) => {
  return !!getToken(userType);
};

/**
 * Get the appropriate headers for API requests including auth token
 * @param {string} userType - The user type ('buyer' or 'seller')
 * @returns {Object} Headers object with Authorization and Content-Type
 */
export const getAuthHeaders = (userType) => {
  const token = getToken(userType);
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
}; 