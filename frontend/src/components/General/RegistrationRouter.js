
import React from 'react';
import { useParams } from 'react-router-dom';
import UserRegistration from './UserRegistration';

function RegistrationRouter() {
  const { userType } = useParams();

  // Validate user type
  if (!['seller', 'buyer'].includes(userType)) {
    return <div>Invalid registration type</div>;
  }

  return <UserRegistration userType={userType} />;
}

export default RegistrationRouter;