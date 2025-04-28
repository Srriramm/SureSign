import React, { useEffect, useState } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { Container, Typography, Box, Button, Paper, Grid, Chip, CircularProgress, Divider } from '@mui/material';
import LawyerService from '../services/lawyerService';
import { toast } from 'react-toastify';

const LawyerVerificationPage = () => {
  const { propertyId } = useParams();
  const location = useLocation();
  const [loading, setLoading] = useState(true);
  const [property, setProperty] = useState(null);
  const [token, setToken] = useState(null);
  const [verificationStatus, setVerificationStatus] = useState(null);

  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const tokenParam = queryParams.get('token');
    
    if (tokenParam) {
      setToken(tokenParam);
      fetchPropertyDetails(tokenParam);
    } else {
      setLoading(false);
      toast.error('Invalid verification link. Missing token.');
    }
  }, [location, propertyId]);

  const fetchPropertyDetails = async (tokenValue) => {
    try {
      setLoading(true);
      const data = await LawyerService.getVerificationDetails(propertyId, tokenValue);
      setProperty(data.property);
      setVerificationStatus(data.status || 'pending');
      setLoading(false);
    } catch (error) {
      console.error('Error fetching property details:', error);
      toast.error('Error loading property details: ' + (error.response?.data?.message || error.message));
      setLoading(false);
    }
  };

  const handleDownloadDocument = async (documentIndex) => {
    try {
      const response = await LawyerService.getPropertyDocument(propertyId, documentIndex, token);
      
      // Create blob link to download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const fileName = property.documents[documentIndex].name || 'document.pdf';
      link.setAttribute('download', fileName);
      
      // Append to html link element page
      document.body.appendChild(link);
      
      // Start download
      link.click();
      
      // Clean up and remove the link
      link.parentNode.removeChild(link);
    } catch (error) {
      toast.error('Error downloading document: ' + (error.response?.data?.message || error.message));
    }
  };

  const handleVerification = async (verified) => {
    try {
      setLoading(true);
      const data = {
        verified,
        comments: verified ? 'Documents verified successfully' : 'Documents verification rejected'
      };
      
      await LawyerService.updateVerificationStatus(propertyId, token, data);
      setVerificationStatus(verified ? 'verified' : 'rejected');
      toast.success(`Property ${verified ? 'verified' : 'rejected'} successfully`);
      setLoading(false);
    } catch (error) {
      console.error('Error updating verification:', error);
      toast.error('Error updating verification: ' + (error.response?.data?.message || error.message));
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Container sx={{ mt: 4, textAlign: 'center' }}>
        <CircularProgress />
        <Typography variant="h6" mt={2}>Loading property details...</Typography>
      </Container>
    );
  }

  if (!property) {
    return (
      <Container sx={{ mt: 4 }}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h5" color="error">Property not found or invalid verification link</Typography>
          <Typography mt={2}>
            The property you're trying to verify either doesn't exist or the verification link is invalid.
          </Typography>
        </Paper>
      </Container>
    );
  }

  return (
    <Container sx={{ my: 4 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          Legal Document Verification
        </Typography>
        
        <Divider sx={{ my: 2 }} />
        
        <Box sx={{ mb: 3 }}>
          <Chip 
            label={
              verificationStatus === 'verified' ? 'Verified' : 
              verificationStatus === 'rejected' ? 'Rejected' : 'Pending Verification'
            }
            color={
              verificationStatus === 'verified' ? 'success' : 
              verificationStatus === 'rejected' ? 'error' : 'warning'
            }
            sx={{ fontSize: '1rem', py: 1, px: 1 }}
          />
        </Box>
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Typography variant="h6">Property Details</Typography>
            <Box sx={{ mt: 2 }}>
              <Typography><strong>ID:</strong> {property.id}</Typography>
              <Typography><strong>Address:</strong> {property.address}</Typography>
              <Typography><strong>Type:</strong> {property.type}</Typography>
              <Typography><strong>Area:</strong> {property.area} sq.ft</Typography>
              <Typography><strong>Seller:</strong> {property.seller?.name || 'N/A'}</Typography>
            </Box>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Typography variant="h6">Documents</Typography>
            <Box sx={{ mt: 2 }}>
              {property.documents?.map((doc, index) => (
                <Box key={index} sx={{ mb: 1 }}>
                  <Button 
                    variant="outlined" 
                    onClick={() => handleDownloadDocument(index)}
                  >
                    {doc.name || `Document ${index + 1}`}
                  </Button>
                </Box>
              ))}
              {(!property.documents || property.documents.length === 0) && (
                <Typography color="text.secondary">No documents available</Typography>
              )}
            </Box>
          </Grid>
        </Grid>
        
        <Box sx={{ mt: 4, display: 'flex', justifyContent: 'space-between' }}>
          {verificationStatus === 'pending' && (
            <>
              <Button 
                variant="contained" 
                color="error" 
                size="large"
                onClick={() => handleVerification(false)}
              >
                Reject Documents
              </Button>
              <Button 
                variant="contained" 
                color="success" 
                size="large"
                onClick={() => handleVerification(true)}
              >
                Verify Documents
              </Button>
            </>
          )}
          
          {verificationStatus !== 'pending' && (
            <Typography variant="h6" color={verificationStatus === 'verified' ? 'green' : 'error'}>
              {verificationStatus === 'verified' 
                ? 'Documents have been successfully verified' 
                : 'Documents have been rejected'
              }
            </Typography>
          )}
        </Box>
      </Paper>
    </Container>
  );
};

export default LawyerVerificationPage; 