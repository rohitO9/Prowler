# Azure AD RBAC System for Prowler SaaS

This document provides a comprehensive guide for implementing and using the Azure AD Role-Based Access Control (RBAC) system for the Prowler SaaS platform.

## Overview

The Azure AD RBAC system provides:
- **Multi-tenant architecture** with company-level isolation
- **Azure AD integration** for authentication and user management
- **Role-based access control** with granular permissions
- **Group synchronization** from Azure AD to application role
- **Comprehensive audit logging** for compliance
- **Secure credential management** with encryption at rest

## Architecture

### Core Components

1. **Company Management**: Multi-tenant company registration and configuration
2. **Azure AD Integration**: OAuth2/OIDC authentication flow
3. **Role Management**: Flexible role system with Azure AD group mapping
4. **User Management**: User profiles with Azure AD synchronization
5. **Permission System**: Granular permissions for fine-grained access control
6. **Audit Logging**: Comprehensive logging for compliance and security
7. **Authorization Middleware**: Request-level permission enforcement

### Database Schema

```
Companies
├── Azure AD Configuration (tenant_id, client_id, client_secret)
├── Company Settings (domain, subscription_tier, trial_info)
└── Relationships to Users, Roles, Audit Logs

Enhanced Roles
├── Role Definition (name, permissions, priority)
├── Azure AD Integration (group mapping, auto-sync)
└── Relationships to Users, Permissions

User Role Assignments
├── User-Role Mapping (assignment source, expiration)
├── Company Context (multi-tenant isolation)
└── Audit Trail (assigned_by, assigned_at)

Audit Logs
├── Action Tracking (login, role changes, data access)
├── Request Context (IP, user agent, method, path)
└── Company Context (multi-tenant logging)
```

## Setup Instructions

### 1. Environment Configuration

Add the following environment variables to your `.env` file:

```bash
# Azure AD Configuration (per company)
AZURE_AD_TENANT_ID=your-tenant-id
AZURE_AD_CLIENT_ID=your-client-id
AZURE_AD_CLIENT_SECRET=your-client-secret
AZURE_AD_REDIRECT_URI=http://localhost:3000/api/auth/callback/azure

# Encryption Key for Secrets
DJANGO_SECRETS_ENCRYPTION_KEY=your-32-byte-base64-encoded-key

# Azure AD Feature Flags
AZURE_AD_ENABLED=true
AZURE_AD_AUTO_CREATE_USERS=true
AZURE_AD_SYNC_GROUPS=true
AZURE_AD_ALLOWED_DOMAINS=yourdomain.com,anotherdomain.com
```

### 2. Database Migration

Run the database migrations to create the new tables:

```bash
python manage.py migrate
```

### 3. URL Configuration

Add the Azure RBAC URLs to your main URL configuration:

```python
# config/urls.py
from django.urls import path, include

urlpatterns = [
    # ... existing patterns
    path('api/v1/azure-rbac/', include('api.v1.urls.azure_rbac')),
]
```

### 4. Middleware Configuration

Add the Azure RBAC middleware to your Django settings:

```python
# config/django/base.py
MIDDLEWARE = [
    # ... existing middleware
    "api.middleware.azure_rbac.AzureADRBACMiddleware",
]
```

### 5. Permission Configuration

Create default permissions in your database:

```python
# management/commands/setup_permissions.py
from django.core.management.base import BaseCommand
from api.models.azure_rbac import Permission

class Command(BaseCommand):
    def handle(self, *args, **options):
        permissions = [
            # User Management
            {'name': 'users.create', 'display_name': 'Create Users', 'category': 'user_management', 'action': 'create'},
            {'name': 'users.read', 'display_name': 'View Users', 'category': 'user_management', 'action': 'read'},
            {'name': 'users.update', 'display_name': 'Update Users', 'category': 'user_management', 'action': 'update'},
            {'name': 'users.delete', 'display_name': 'Delete Users', 'category': 'user_management', 'action': 'delete'},
            
            # Role Management
            {'name': 'roles.manage', 'display_name': 'Manage Roles', 'category': 'user_management', 'action': 'manage'},
            
            # Provider Management
            {'name': 'providers.create', 'display_name': 'Create Providers', 'category': 'provider_management', 'action': 'create'},
            {'name': 'providers.read', 'display_name': 'View Providers', 'category': 'provider_management', 'action': 'read'},
            {'name': 'providers.update', 'display_name': 'Update Providers', 'category': 'provider_management', 'action': 'update'},
            {'name': 'providers.delete', 'display_name': 'Delete Providers', 'category': 'provider_management', 'action': 'delete'},
            
            # Scan Management
            {'name': 'scans.create', 'display_name': 'Create Scans', 'category': 'scan_management', 'action': 'create'},
            {'name': 'scans.read', 'display_name': 'View Scans', 'category': 'scan_management', 'action': 'read'},
            {'name': 'scans.execute', 'display_name': 'Execute Scans', 'category': 'scan_management', 'action': 'execute'},
            
            # Audit Access
            {'name': 'audit.access', 'display_name': 'Access Audit Logs', 'category': 'audit_access', 'action': 'read'},
        ]
        
        for perm_data in permissions:
            Permission.objects.get_or_create(
                name=perm_data['name'],
                defaults=perm_data
            )
        
        self.stdout.write(self.style.SUCCESS('Permissions created successfully'))
```

Run the command:

```bash
python manage.py setup_permissions
```

## Usage Examples

### 1. Company Registration

Register a new company with Azure AD configuration:

```python
# POST /api/v1/azure-rbac/companies/register/
{
    "name": "Acme Corporation",
    "domain": "acme.com",
    "azure_tenant_id": "12345678-1234-1234-1234-123456789012",
    "azure_client_id": "87654321-4321-4321-4321-210987654321",
    "azure_client_secret": "your-client-secret",
    "azure_redirect_uri": "https://your-app.com/api/auth/callback/azure"
}
```

### 2. Azure AD Authentication Flow

#### Frontend Integration

```javascript
// Get Azure AD configuration
const configResponse = await fetch('/api/v1/azure-rbac/auth/azure/config/?company=acme.com');
const config = await configResponse.json();

// Initialize MSAL
const msalInstance = new msal.PublicClientApplication({
    auth: {
        clientId: config.client_id,
        authority: config.authority,
        redirectUri: config.redirect_uri
    }
});

// Login
const loginResponse = await msalInstance.loginPopup({
    scopes: config.scopes
});

// Exchange code for tokens
const authResponse = await fetch('/api/v1/azure-rbac/auth/azure/login/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        company: 'acme.com',
        code: loginResponse.authorizationCode
    })
});

const authData = await authResponse.json();
// Store tokens and user data
localStorage.setItem('access_token', authData.access_token);
localStorage.setItem('user', JSON.stringify(authData.user));
```

#### Backend Authentication

```python
from api.services.azure_ad_auth import AzureADAuthService

# Initialize auth service for company
company = Company.objects.get(domain='acme.com')
auth_service = AzureADAuthService(company)

# Authenticate user
success, auth_result = auth_service.authenticate_user(auth_code)

if success:
    user = auth_result['user']
    access_token = auth_result['access_token']
    # User is authenticated and authorized
```

### 3. Role Management

#### Create Custom Role

```python
# POST /api/v1/azure-rbac/roles/
{
    "name": "security_analyst",
    "display_name": "Security Analyst",
    "description": "Can view scans and findings, manage compliance",
    "role_type": "custom",
    "manage_scans": true,
    "unlimited_visibility": true,
    "priority": 50
}
```

#### Assign Role to User

```python
# POST /api/v1/azure-rbac/user-roles/
{
    "user_id": "user-uuid",
    "role_id": "role-uuid",
    "assignment_source": "direct",
    "expires_at": "2024-12-31T23:59:59Z"
}
```

### 4. Azure AD Group Synchronization

#### Sync Groups to Roles

```python
# POST /api/v1/azure-rbac/azure/groups/sync/
{
    "access_token": "azure-access-token"
}
```

#### Configure Group Mapping

```python
from api.models.azure_rbac import AzureADGroupMapping

# Map Azure AD group to application role
mapping = AzureADGroupMapping.objects.create(
    company=company,
    azure_group_id="azure-group-id",
    azure_group_name="Security Team",
    role=security_analyst_role,
    auto_sync=True
)
```

### 5. Permission Enforcement

#### View-Level Permissions

```python
from api.middleware.azure_rbac import HasPermission, HasRole

class ScanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasPermission(['scans.read'])]
    
    def create(self, request):
        # Requires 'scans.create' permission
        pass
    
    def destroy(self, request, pk=None):
        # Requires 'scans.delete' permission
        pass

class AdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRole(['admin'])]
    
    def list(self, request):
        # Requires admin role
        pass
```

#### Function-Level Permissions

```python
from api.middleware.azure_rbac import require_permission, require_role

@require_permission(['users.manage'])
def manage_users(request):
    # Function requires users.manage permission
    pass

@require_role(['admin', 'user_manager'])
def admin_function(request):
    # Function requires admin or user_manager role
    pass
```

### 6. Audit Logging

#### View Audit Logs

```python
# GET /api/v1/azure-rbac/audit/logs/
# Query parameters:
# - action_type: Filter by action type
# - user_id: Filter by user
# - start_date: Start date filter
# - end_date: End date filter
# - success_only: Show only successful actions
# - page: Page number
# - page_size: Items per page

response = requests.get('/api/v1/azure-rbac/audit/logs/', params={
    'action_type': 'login',
    'start_date': '2024-01-01',
    'page': 1,
    'page_size': 50
})
```

#### Custom Audit Logging

```python
from api.models.azure_rbac import AuditLog

# Log custom action
AuditLog.log_action(
    user=request.user,
    company=request.company,
    action_type='data_modified',
    action_description='User updated scan configuration',
    resource_type='scan',
    resource_id=str(scan.id),
    success=True,
    details={'scan_name': scan.name, 'changes': changes}
)
```

## Security Considerations

### 1. Secret Management

- Azure client secrets are encrypted at rest using Fernet encryption
- Use strong, unique encryption keys for each environment
- Rotate encryption keys regularly
- Store encryption keys securely (e.g., AWS Secrets Manager, Azure Key Vault)

### 2. Token Security

- JWT tokens include company context for multi-tenant isolation
- Tokens have appropriate expiration times
- Refresh tokens are securely stored and rotated
- Access tokens are validated on each request

### 3. Permission Enforcement

- All API endpoints require explicit permission checks
- Row-level security ensures data isolation between companies
- Audit logging tracks all permission checks and denials
- Failed authentication attempts are logged and monitored

### 4. Azure AD Integration

- Validate Azure AD tokens using Microsoft's public keys
- Implement proper error handling for token validation failures
- Use HTTPS for all Azure AD communication
- Implement proper CORS policies for frontend integration

## Monitoring and Compliance

### 1. Audit Logging

The system provides comprehensive audit logging for:
- User authentication and authorization
- Role assignments and removals
- Permission grants and denials
- Data access and modifications
- Azure AD synchronization events
- System errors and security events

### 2. Compliance Features

- **SOC 2**: Comprehensive audit trails and access controls
- **GDPR**: User data management and deletion capabilities
- **HIPAA**: Secure credential management and access logging
- **ISO 27001**: Security controls and monitoring

### 3. Monitoring Integration

```python
# Example: Send audit events to SIEM
import logging

class SIEMHandler(logging.Handler):
    def emit(self, record):
        # Send to SIEM system
        send_to_siem(record)

# Configure logging
logger = logging.getLogger('api.audit')
logger.addHandler(SIEMHandler())
```

## Troubleshooting

### Common Issues

1. **Token Validation Failures**
   - Check Azure AD tenant ID and client ID
   - Verify token expiration times
   - Ensure proper clock synchronization

2. **Permission Denied Errors**
   - Verify user has required permissions
   - Check role assignments are active
   - Confirm company context is correct

3. **Group Sync Issues**
   - Verify Azure AD group IDs are correct
   - Check group mapping configuration
   - Ensure proper Azure AD permissions

4. **Database Connection Issues**
   - Verify database migrations are applied
   - Check database permissions
   - Ensure proper indexing for performance

### Debug Mode

Enable debug logging for troubleshooting:

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'api.services.azure_ad_auth': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'api.middleware.azure_rbac': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

## API Reference

### Authentication Endpoints

- `POST /api/v1/azure-rbac/companies/register/` - Register new company
- `POST /api/v1/azure-rbac/auth/azure/login/` - Azure AD login
- `GET /api/v1/azure-rbac/auth/azure/config/` - Get Azure AD config

### Role Management Endpoints

- `GET /api/v1/azure-rbac/roles/` - List roles
- `POST /api/v1/azure-rbac/roles/` - Create role
- `GET /api/v1/azure-rbac/user-roles/` - List user role assignments
- `POST /api/v1/azure-rbac/user-roles/` - Assign role to user
- `DELETE /api/v1/azure-rbac/user-roles/` - Remove role assignment

### Azure AD Integration Endpoints

- `POST /api/v1/azure-rbac/azure/groups/sync/` - Sync Azure AD groups

### Audit Endpoints

- `GET /api/v1/azure-rbac/audit/logs/` - View audit logs

## Contributing

1. Follow the existing code style and patterns
2. Add comprehensive tests for new functionality
3. Update documentation for API changes
4. Ensure all security considerations are addressed
5. Test with multiple Azure AD tenants

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review audit logs for error details
3. Consult Azure AD documentation
4. Contact the development team

---

This Azure AD RBAC system provides a robust, secure, and scalable foundation for multi-tenant SaaS applications with comprehensive audit logging and compliance features.
