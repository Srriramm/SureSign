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
import ProtectedRoute from './components/Auth/ProtectedRoute';

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
      </Routes>
    </Router>
  );
}

export default App;