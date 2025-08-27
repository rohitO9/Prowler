# Azure AD Integration Module

This module provides comprehensive Azure AD (Azure Active Directory) integration for the Prowler security scanner application.

## Features

- **Single Sign-On (SSO)**: Users can authenticate using their Azure AD credentials
- **Automatic User Provisioning**: Users are automatically created/updated from Azure AD
- **Group Synchronization**: Azure AD groups can be mapped to local roles
- **Tenant Mapping**: Azure AD groups can be mapped to local tenants
- **Token Management**: Secure token handling and refresh mechanisms
- **Audit Logging**: Comprehensive audit trail for Azure AD operations
- **User Profile Sync**: Extended user profile information from Azure AD
- **Management Commands**: CLI commands for user synchronization

## Architecture

```
api/v1/
├── views/
│   └── azure_ad.py              # Azure AD authentication views
├── models/
│   └── azure_ad.py              # Azure AD data models
├── serializers/
│   └── azure_ad.py              # Azure AD serializers
├── utils/
│   └── azure_ad_utils.py        # Azure AD utility functions
├── admin/
│   └── azure_ad.py              # Django admin interface
└── tests/
    └── test_azure_ad.py         # Azure AD tests
```

## Models

### AzureADGroupMapping
Maps Azure AD groups to local roles for automatic role assignment.

### AzureADTenantMapping
Maps Azure AD groups to local tenants for multi-tenant scenarios.

### AzureADUserSync
Tracks user synchronization operations and their status.

### AzureADTokenCache
Caches Azure AD tokens for improved performance and reduced API calls.

### AzureADUserProfile
Extended user profile information from Azure AD (job title, department, etc.).

### AzureADAuditLog
Comprehensive audit trail for all Azure AD operations.

## API Endpoints

### Authentication
- `POST /api/v1/tokens/azure` - Azure AD authentication
- `GET /api/v1/tokens/azure/config` - Azure AD configuration

### User Management
- `GET /api/v1/users/` - List users (includes Azure AD users)
- `POST /api/v1/users/sync/azure` - Manual user synchronization

## Configuration

### Environment Variables

```bash
# Required
AZURE_AD_ENABLED=true
AZURE_AD_CLIENT_ID=your_client_id
AZURE_AD_CLIENT_SECRET=your_client_secret
AZURE_AD_TENANT_ID=your_tenant_id
AZURE_AD_REDIRECT_URI=http://localhost:3000/auth/callback/azure

# Optional
AZURE_AD_AUTO_CREATE_USERS=true
AZURE_AD_SYNC_GROUPS=false
AZURE_AD_REQUIRE_EMAIL_VERIFICATION=false
AZURE_AD_ALLOWED_DOMAINS=yourdomain.com,anotherdomain.com
AZURE_AD_LOG_LEVEL=INFO
```

### Django Settings

```python
# settings.py
from api.settings.azure_ad import *

INSTALLED_APPS = [
    # ... existing apps
    'api.v1.models.azure_ad',
]
```

## Usage

### 1. Setup Azure AD Application

1. Register application in Azure AD
2. Configure permissions (User.Read, GroupMember.Read.All)
3. Create client secret
4. Note application details

### 2. Configure Environment

Set required environment variables as shown above.

### 3. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Configure Group Mappings

Use Django admin to create group mappings:

```python
from api.v1.models.azure_ad import AzureADGroupMapping
from api.v1.models import Role

role = Role.objects.get(name='admin')
AzureADGroupMapping.objects.create(
    azure_group_id='your_azure_group_id',
    azure_group_name='Your Azure Group',
    role=role
)
```

### 5. Test Authentication

```bash
# Test user sync
python manage.py sync_azure_ad_users --all --dry-run

# Sync specific user
python manage.py sync_azure_ad_users --email user@example.com
```

## Management Commands

### sync_azure_ad_users

Synchronizes users from Azure AD to local database.

```bash
# Sync all users
python manage.py sync_azure_ad_users --all

# Sync specific user by Azure AD ID
python manage.py sync_azure_ad_users --user-id azure_user_id

# Sync specific user by email
python manage.py sync_azure_ad_users --email user@example.com

# Force update existing users
python manage.py sync_azure_ad_users --all --force

# Dry run (show what would be synced)
python manage.py sync_azure_ad_users --all --dry-run
```

## Frontend Integration

### React/Next.js Example

```javascript
import { useMsal } from "@azure/msal-react";

const AzureADLogin = () => {
  const { instance } = useMsal();

  const handleLogin = async () => {
    try {
      const response = await instance.loginPopup({
        scopes: ["openid", "profile", "email", "User.Read"]
      });
      
      // Send authorization code to backend
      const authResponse = await fetch('/api/v1/tokens/azure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: response.accessToken })
      });
      
      const tokens = await authResponse.json();
      // Store tokens and redirect
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <button onClick={handleLogin}>
      Sign in with Azure AD
    </button>
  );
};
```

## Security Considerations

### Token Security
- Tokens are validated using Azure AD public keys
- Token expiration is checked before use
- Refresh tokens are securely stored

### User Data Protection
- Sensitive data is encrypted at rest
- Audit logs track all operations
- Domain restrictions can be configured

### API Security
- All endpoints require proper authentication
- CORS is configured for security
- Rate limiting is implemented

## Testing

Run the Azure AD tests:

```bash
# Run all Azure AD tests
python manage.py test api.tests.test_azure_ad

# Run specific test class
python manage.py test api.tests.test_azure_ad.AzureADViewsTestCase

# Run with coverage
coverage run --source='.' manage.py test api.tests.test_azure_ad
coverage report
```

## Troubleshooting

### Common Issues

1. **Invalid Redirect URI**
   - Ensure redirect URI matches exactly in Azure AD
   - Check protocol (http vs https)

2. **Permission Denied**
   - Verify admin consent is granted
   - Check application permissions

3. **Token Validation Errors**
   - Verify tenant ID is correct
   - Check client ID and secret

4. **User Sync Failures**
   - Ensure Microsoft Graph permissions
   - Check application permissions

### Debug Mode

Enable debug logging:

```bash
AZURE_AD_LOG_LEVEL=DEBUG
```

### Logs

Check Django logs for Azure AD operations:

```python
import logging
logger = logging.getLogger('api.v1.views.azure_ad')
```

## Contributing

When contributing to the Azure AD integration:

1. Follow the existing code style
2. Add tests for new functionality
3. Update documentation
4. Test with real Azure AD tenant
5. Consider security implications

## Dependencies

See `requirements-azure-ad.txt` for specific Azure AD dependencies.

## License

This module is part of the Prowler project and follows the same license terms.

## Support

For issues and questions:

1. Check the [Azure AD setup guide](../../../docs/tutorials/azure/azure-ad-setup.md)
2. Review the [Azure AD documentation](https://docs.microsoft.com/en-us/azure/active-directory/)
3. Open an issue on the Prowler GitHub repository
4. Contact your Azure AD administrator for tenant-specific issues 