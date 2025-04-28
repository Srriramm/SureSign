import API from './api';

const LawyerService = {
  // Get verification details for a lawyer using token
  getVerificationDetails: async (propertyId, token) => {
    try {
      const response = await API.get(`/lawyer/verification/${propertyId}?token=${token}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Update verification status
  updateVerificationStatus: async (propertyId, token, data) => {
    try {
      const response = await API.post(`/lawyer/verification/${propertyId}?token=${token}`, data);
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // Get document for verification
  getPropertyDocument: async (propertyId, documentIndex, token) => {
    try {
      const response = await API.get(
        `/lawyer/property-document/${propertyId}/${documentIndex}?token=${token}`,
        { responseType: 'blob' }
      );
      return response;
    } catch (error) {
      throw error;
    }
  }
};

export default LawyerService; 