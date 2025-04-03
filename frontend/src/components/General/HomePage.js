import React from 'react';
import { Link } from 'react-router-dom';
import './HomePage.css';

function HomePage() {
  return (
    <div className="home-page">
      <header>
        <div className="container">
          <img src="/assets/Blue Modern Technology Company Logo (1).png" alt="SureSign Logo" className="home-logo-image" />
          <h1 className="home-header-title">ONLINE PROPERTY REGISTRATION PORTAL</h1>
        </div>
      </header>

      <main>
        <div className="container">
          <div className="portal-description">
            <h2>Digital Property Registration System</h2>
            <div className="divider"></div>
            <p>Welcome to the official <span className="highlight">Online Property Registration Portal</span>, a secure platform for property transactions with enhanced digital verification.</p>
            <p>Our system offers <span className="highlight">faceless registration</span> with AI-powered verification, Aadhaar integration, and blockchain-backed document security to ensure transparent and tamper-proof property transactions.</p>
          </div>

          <div className="button-container">
            <Link to="/login/seller" className="action-button">
              <div className="button-icon">🏠</div>
              <span className="button-text">Sell Property</span>
            </Link>

            <Link to="/login/buyer" className="action-button">
              <div className="button-icon">🔑</div>
              <span className="button-text">Buy Property</span>
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

export default HomePage;