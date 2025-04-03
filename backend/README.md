# SureSign Backend

This is the backend server for the SureSign property registration platform.

## Security Features

The SureSign application includes enhanced security features for handling sensitive user data and documents:

### Azure Blob Storage Security

The application uses a secure container structure with the following features:

1. **Secure Container Naming**:
   - `sec-user-kyc-images` - For user selfies and identity verification
   - `sec-property-legal-docs` - For legal property documents
   - `sec-property-verification-images` - For property images

2. **Access Control**:
   - Private container access by default
   - SAS token generation for time-limited access
   - User-based access control for personal data

3. **Secure File Handling**:
   - Non-guessable filenames using SHA-256 hashing
   - Metadata-based tracking and auditing
   - Content verification and validation

4. **Authentication**:
   - JWT-based API authentication
   - SAS token expiry management
   - Automatic token refresh mechanisms

### Database Security

1. **User Data Protection**:
   - Password hashing with bcrypt
   - Tokenized access to user files
   - Metadata-only blob references

2. **Blockchain Integration**:
   - Ethereum-based property registry records
   - Transaction verification

## Container Migration

The application includes a robust migration system for transitioning from legacy containers to the new secure structure.

### Migration Features

1. **Background Migration**:
   - Asynchronous processing
   - Progress tracking
   - Detailed logging

2. **On-Demand Migration**:
   - Just-in-time file migration during access
   - Transparent to end users

3. **Migration Script**:
   - Command-line utility for admin-initiated migration
   - Dry-run option for validation

### Running Migrations

To migrate data to the new secure container structure:

1. **API-based migration**:
   ```
   POST /auth/migrate-selfies
   Authorization: Bearer <admin_token>
   ```

2. **Script-based migration**:
   ```bash
   cd backend/scripts
   python migrate_images.py
   ```

   Options:
   - `--dry-run` - Show what would be migrated without making changes
   - `--container=CONTAINER_NAME` - Migrate a specific container only

## API Documentation

### Authentication Endpoints

- `POST /auth/register/{user_type}` - Register a new user
- `POST /auth/complete_registration/{user_type}` - Complete registration with selfie
- `POST /auth/login/{user_type}` - User login
- `POST /auth/upload_selfie/{user_type}/{user_id}` - Upload user selfie
- `GET /auth/user-selfie/{user_type}/{user_id}` - Get user selfie URL
- `POST /auth/migrate-selfies` - [Admin] Migrate all selfies to secure containers
- `GET /auth/migration-status/{task_id}` - [Admin] Check migration status

### Seller Endpoints

- `GET /seller/get-seller` - Get seller profile
- `GET /seller/properties` - List seller properties
- `POST /seller/properties` - Create property listing
- `GET /seller/images/{container_name}/{blob_name}` - Securely serve images
- `GET /seller/direct-image/{user_id}` - Get user selfie image with security checks

## Environment Configuration

Security-related environment variables:

```
# Azure Container Names
AZURE_CONTAINER_USER_SELFIES=sec-user-kyc-images
AZURE_CONTAINER_PROPERTY_DOCUMENTS=sec-property-legal-docs
AZURE_CONTAINER_PROPERTY_IMAGES=sec-property-verification-images

# Azure Security Configuration
AZURE_CONTAINER_PUBLIC_ACCESS=false
AZURE_BLOB_ENCRYPTION_ENABLED=true
AZURE_CONTAINER_DEFAULT_POLICY=private

# Encryption Configuration  
FILE_ENCRYPTION_KEY=<your-encryption-key>
ENCRYPTION_SALT=<your-encryption-salt>
```

## Running the Server

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
``` 