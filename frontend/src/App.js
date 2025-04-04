import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import HomePage from './components/General/HomePage';
import ListProperties from './components/SellerFlow/ListProperties';
import AddProperty from './components/SellerFlow/AddProperty';
import UserLogin from './components/General/UserLogin';
import UserRegistration from './components/General/UserRegistration';
import RegistrationRouter from './components/General/RegistrationRouter';
import EditProfile from './components/SellerFlow/EditProfile';
import PropertyDetails from './components/SellerFlow/PropertyDetails';
import BuyerDashboard from './components/BuyerFlow/BuyerDashboard';
import BuyerProperties from './components/BuyerFlow/BuyerProperties';
import BuyerPropertyDetails from './components/BuyerFlow/BuyerPropertyDetails';
import EditBuyerProfile from './components/BuyerFlow/EditBuyerProfile';
import ProtectedRoute from './components/Auth/ProtectedRoute';
import DocumentRequests from './components/SellerFlow/DocumentRequests';

function App() {
  return (
    <Router>
      <Routes>
         <Route path="/" element={<HomePage />} />
          <Route path="/login/:userType" element={<UserLogin />} /> 
          <Route path="/register/:userType" element={<RegistrationRouter />} />
          <Route 
            path="/list-properties" 
            element={
              <ProtectedRoute userType="seller">
                <ListProperties />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/add-property" 
            element={
              <ProtectedRoute userType="seller">
                <AddProperty />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/edit-profile" 
            element={
              <ProtectedRoute userType="seller">
                <EditProfile />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/property-details/:propertyId" 
            element={
              <ProtectedRoute userType="seller">
                <PropertyDetails />
              </ProtectedRoute>
            } 
          />
          <Route path="/document-requests" element={<ProtectedRoute userType="seller"><DocumentRequests /></ProtectedRoute>} />
          {/* Buyer Routes */}
          <Route
            path="/buyer-dashboard"
            element={
              <ProtectedRoute userType="buyer">
                <BuyerDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/buyer-properties"
            element={
              <ProtectedRoute userType="buyer">
                <BuyerProperties />
              </ProtectedRoute>
            }
          />
          <Route
            path="/buyer-property/:propertyId"
            element={
              <ProtectedRoute userType="buyer">
                <BuyerPropertyDetails />
              </ProtectedRoute>
            }
          />
          <Route
            path="/edit-buyer-profile"
            element={
              <ProtectedRoute userType="buyer">
                <EditBuyerProfile />
              </ProtectedRoute>
            }
          />
      </Routes>
    </Router>
  );
}

export default App;