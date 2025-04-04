import React, { useEffect, useState } from 'react';

function TestConnection() {
  const [status, setStatus] = useState('Testing connection...');
  const [error, setError] = useState(null);

  useEffect(() => {
    const testConnection = async () => {
      try {
        // First try the root endpoint
        console.log('Testing connection to backend root endpoint');
        const rootResponse = await fetch('http://localhost:8000/', {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          }
        });
        
        if (!rootResponse.ok) {
          throw new Error(`Root endpoint returned ${rootResponse.status}`);
        }
        
        const rootData = await rootResponse.json();
        console.log('Root endpoint response:', rootData);

        // Then try auth login endpoint with OPTIONS preflight request
        console.log('Testing connection to login endpoint');
        const loginResponse = await fetch('http://localhost:8000/auth/login/seller', {
          method: 'OPTIONS',
          headers: {
            'Accept': 'application/json',
            'Origin': window.location.origin,
          }
        });

        if (!loginResponse.ok) {
          throw new Error(`Login OPTIONS preflight returned ${loginResponse.status}`);
        }

        setStatus('Connection successful! Backend is reachable.');
      } catch (err) {
        console.error('Connection test failed:', err);
        setStatus('Connection failed');
        setError(err.message);
      }
    };

    testConnection();
  }, []);

  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto' }}>
      <h2>Backend Connection Test</h2>
      <div>Status: <strong>{status}</strong></div>
      {error && (
        <div style={{ color: 'red', marginTop: '10px' }}>
          Error: {error}
          <p>Please check:</p>
          <ul>
            <li>Backend server is running at http://localhost:8000</li>
            <li>No network issues (firewalls, proxies)</li>
            <li>CORS is properly configured in the backend</li>
            <li>No browser extensions blocking the request</li>
          </ul>
        </div>
      )}
      <div style={{ marginTop: '20px' }}>
        <p><strong>Browser Console:</strong> Check the browser console (F12) for more detailed information.</p>
      </div>
    </div>
  );
}

export default TestConnection; 