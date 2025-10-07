# Azure AD Integration Setup Guide

This guide will help you set up Azure Active Directory (Azure AD) integration for the Prowler application, enabling single sign-on (SSO) authentication for your users.

## Prerequisites

- An Azure AD tenant with administrative access
- Access to the Azure Portal
- Basic understanding of OAuth 2.0 and OpenID Connect protocols

## Step 1: Register Application in Azure AD

### 1.1 Access Azure Portal
1. Sign in to the [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**

### 1.2 Create New Registration
1. Click **New registration**
2. Fill in the application details:
   - **Name**: `Prowler Security Scanner` (or your preferred name)
   - **Supported account types**: `Accounts in this organizational directory only`
   - **Redirect URI**: 
     - **Type**: `Web`
     - **URI**: `http://localhost:3000/azure/callback` (for development)
     - **URI**: `https://yourdomain.com/azure/callback` (for production)
3. Click **Register**

### 1.3 Note Application Details
After registration, note down:
- **Application (client) ID**: Found in the Overview page
- **Directory (tenant) ID**: Found in the Overview page

## Step 2: Configure Application Permissions

### 2.1 Add API Permissions
1. In your registered application, go to **API permissions**
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Choose **Delegated permissions**
5. Add the following permissions:
   - `User.Read` - Read user profile
   - `User.Read.All` - Read all users (for user sync)
   - `GroupMember.Read.All` - Read group membership (for role mapping)
6. Click **Add permissions**

### 2.2 Grant Admin Consent
1. Click **Grant admin consent for [Your Organization]**
2. Confirm the permissions

## Step 3: Create Client Secret

### 3.1 Generate Secret
1. Go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description (e.g., "Prowler Integration")
4. Select expiration period (recommend 12 months)
5. Click **Add**

### 3.2 Copy Secret Value
**Important**: Copy the generated secret value immediately - you won't be able to see it again!

## Step 4: Configure Backend Environment Variables

Azure AD is configured through backend environment variables for secure single-tenant setup. The frontend automatically detects the configuration from the backend.

### 4.1 Backend Environment Variables
Add the following variables to your backend `.env` file:

```bash
# Azure AD Configuration
AZURE_AD_ENABLED=True
AZURE_AD_CLIENT_ID=your_client_id_here
AZURE_AD_CLIENT_SECRET=your_client_secret_here
AZURE_AD_TENANT_ID=your_tenant_id_here
AZURE_AD_REDIRECT_URI=http://localhost:3000/azure/callback

# Azure AD Graph API Settings
AZURE_AD_GRAPH_API_VERSION=v1.0
AZURE_AD_GRAPH_API_BASE_URL=https://graph.microsoft.com

# Azure AD Authentication Settings
AZURE_AD_AUTHORITY=https://login.microsoftonline.com/your_tenant_id_here
AZURE_AD_SCOPES=openid,profile,email,User.Read

# Azure AD Feature Flags
AZURE_AD_AUTO_CREATE_USERS=True
AZURE_AD_SYNC_GROUPS=False
AZURE_AD_REQUIRE_EMAIL_VERIFICATION=False
```

## Step 5: Configure Frontend Routes

### 5.1 Update Next.js Configuration
Ensure your `next.config.js` includes the Azure AD callback route:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // ... other config
  async redirects() {
    return [
      {
        source: '/azure/callback',
        destination: '/azure/callback',
        permanent: false,
      },
    ];
  },
};

module.exports = nextConfig;
```

### 5.2 Verify Route Structure
Ensure you have the following route structure:
```
ui/app/(auth)/azure/
├── page.tsx              # Configuration page
├── callback/
│   └── page.tsx          # OAuth callback handler
├── test/
│   └── page.tsx          # Test page
└── dashboard/
    └── page.tsx          # Dashboard page
```

## Step 6: Test the Integration

### 6.1 Start the Application
1. Start your frontend application: `npm run dev`
2. Start your backend API server
3. Navigate to `http://localhost:3000/sign-in`

### 6.2 Test Authentication Flow
1. Click "Continue with Azure AD" button
2. You should be redirected to Microsoft login
3. Sign in with your Azure AD credentials
4. You should be redirected back to the application
5. Verify that you're successfully authenticated

### 6.3 Test Configuration
1. Navigate to `http://localhost:3000/azure/test`
2. Test the authentication flow
3. Check trial status for users

## Step 7: Production Deployment

### 7.1 Update Redirect URIs
For production, update the redirect URI in Azure AD:
1. Go to your app registration in Azure Portal
2. Navigate to **Authentication**
3. Update the redirect URI to your production domain:
   - `https://yourdomain.com/azure/callback`

### 7.2 Update Environment Variables
Update your production environment variables with the production redirect URI.

### 7.3 SSL Certificate
Ensure your production domain has a valid SSL certificate, as Azure AD requires HTTPS for production redirect URIs.

## Troubleshooting

### Common Issues

#### 1. "Invalid redirect URI" Error
- Verify the redirect URI in Azure AD matches exactly with your environment variable
- Check for trailing slashes or protocol mismatches

#### 2. "Application not found" Error
- Verify the Client ID and Tenant ID are correct
- Ensure the application is registered in the correct Azure AD tenant

#### 3. "Insufficient permissions" Error
- Verify all required permissions are granted
- Ensure admin consent is provided for the permissions

#### 4. "Token exchange failed" Error
- Verify the Client Secret is correct
- Check that the Client Secret hasn't expired
- Ensure the application has the correct redirect URI configured

### Debug Steps

1. **Check Browser Console**: Look for JavaScript errors in the browser console
2. **Check Network Tab**: Monitor network requests for failed API calls
3. **Check Backend Logs**: Review backend logs for authentication errors
4. **Verify Environment Variables**: Ensure all environment variables are set correctly

### Getting Help

If you encounter issues:
1. Check the [Azure AD documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
2. Review the application logs
3. Contact your Azure AD administrator
4. Open an issue in the project repository

## Security Considerations

### 1. Client Secret Security
- Store client secrets securely
- Never commit secrets to version control
- Use environment variables or secure secret management
- Rotate secrets regularly

### 2. Redirect URI Security
- Use HTTPS in production
- Validate redirect URIs on the backend
- Avoid wildcard redirect URIs

### 3. Token Security
- Validate tokens on the backend
- Implement proper token storage
- Use secure session management

### 4. User Permissions
- Implement proper role-based access control
- Validate user permissions on each request
- Log authentication events

## Advanced Configuration

### Custom Claims Mapping
You can customize how Azure AD user attributes are mapped to your application:

```python
# In your backend settings
AZURE_AD_USER_MAPPING = {
    'id': 'azure_ad_id',
    'mail': 'email',
    'userPrincipalName': 'email',
    'givenName': 'first_name',
    'surname': 'last_name',
    'displayName': 'full_name',
}
```

### Group Synchronization
Enable group synchronization to map Azure AD groups to application roles:

```python
# Enable group sync
AZURE_AD_SYNC_GROUPS = True

# Configure group mappings
AZURE_AD_GROUP_MAPPING = {
    'admin_group_id': 'your_admin_group_id',
    'user_group_id': 'your_user_group_id',
}
```

### Domain Restrictions
Restrict access to specific email domains:

```python
# Allow only specific domains
AZURE_AD_ALLOWED_DOMAINS = ['yourcompany.com', 'partner.com']
```

## Support and Resources

- [Azure AD Documentation](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- [Microsoft Graph API Documentation](https://docs.microsoft.com/en-us/graph/)
- [OAuth 2.0 Specification](https://tools.ietf.org/html/rfc6749)
- [OpenID Connect Specification](https://openid.net/connect/)

For additional support, please refer to the project documentation or contact the development team.
