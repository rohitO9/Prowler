# Azure AD SSO + SCIM 2.0 Implementation Plan

## 📊 Current Implementation Status

### ✅ **Already Implemented**
- **Service Architecture**: Core services (TenantService, InviteService, AuthService, etc.)
- **Basic Models**: User, Tenant, TenantMembership, Invitation, Role, SecurityAuditLog
- **Azure AD Models**: Multiple Azure AD models exist but need consolidation
- **SCIM Service**: Basic SCIM service structure exists
- **API Endpoints**: Some tenant onboarding endpoints exist
- **Email Templates**: Basic invitation templates exist

### ❌ **Missing Implementation**
- **Consolidated Azure AD Models**: Multiple conflicting Azure AD model files
- **SCIM 2.0 API Endpoints**: No actual SCIM endpoints implemented
- **Azure AD OAuth Flow**: No working OAuth implementation
- **Frontend Pages**: No tenant registration or SSO setup pages
- **User Management Dashboard**: No admin interface
- **Celery Background Tasks**: No sync tasks
- **Complete Email Templates**: Basic templates need enhancement

---

## 🎯 Implementation Plan

### **Phase 1: Database Models Consolidation**

#### 1.1 Create Unified Azure AD Models
**File**: `api/src/backend/api/models/azure_sso.py`

```python
class AzureSSOConfig(models.Model):
    """OneToOne relationship with Tenant for Azure AD SSO configuration"""
    tenant = models.OneToOneField('Tenant', on_delete=models.CASCADE)
    
    # Azure Credentials
    azure_tenant_id = models.CharField(max_length=255, db_index=True)
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=500)  # Encrypted
    authority = models.URLField()
    authorization_endpoint = models.URLField()
    token_endpoint = models.URLField()
    
    # SCIM Configuration
    scim_enabled = models.BooleanField(default=True)
    scim_token = models.CharField(max_length=255, unique=True)
    scim_base_url = models.URLField()
    
    # Sync Settings
    auto_provision_users = models.BooleanField(default=True)
    auto_deprovision_users = models.BooleanField(default=True)
    sync_user_attributes = models.BooleanField(default=True)
    
    # Mappings (JSON fields)
    attribute_mapping = models.JSONField(default=dict)
    group_role_mapping = models.JSONField(default=dict)
    
    # Sync Status
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial')
    ], default='success')
    last_sync_error = models.TextField(blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class AzureUserSync(models.Model):
    """Audit trail for Azure AD sync events"""
    id = models.UUIDField(primary_key=True, default=uuid4)
    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE)
    user = models.ForeignKey('User', on_delete=models.CASCADE, null=True, blank=True)
    azure_user_id = models.CharField(max_length=255, db_index=True)
    azure_user_data = models.JSONField()
    action = models.CharField(max_length=20, choices=[
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('deleted', 'Deleted'),
        ('disabled', 'Disabled'),
        ('enabled', 'Enabled')
    ])
    changes = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped')
    ])
    error_message = models.TextField(blank=True)
    synced_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'synced_at']),
            models.Index(fields=['azure_user_id']),
        ]
```

#### 1.2 Update User Model
**File**: `api/src/backend/api/models.py`

```python
class User(AbstractUser):
    # ... existing fields ...
    
    # Azure AD Integration
    azure_id = models.CharField(max_length=255, unique=True, null=True, blank=True, db_index=True)
    azure_tenant_id = models.CharField(max_length=255, null=True, blank=True)
    azure_upn = models.CharField(max_length=255, null=True, blank=True)
    
    # Profile Data (synced from Azure AD)
    department = models.CharField(max_length=255, blank=True)
    job_title = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    manager_azure_id = models.CharField(max_length=255, blank=True)
    
    # Status
    is_sso_user = models.BooleanField(default=False)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    deactivation_reason = models.CharField(max_length=50, choices=[
        ('REMOVED_FROM_AZURE', 'Removed from Azure'),
        ('DISABLED_IN_AZURE', 'Disabled in Azure'),
        ('MANUAL', 'Manual'),
        ('SUBSCRIPTION_EXPIRED', 'Subscription Expired')
    ], blank=True)
    
    # Timestamps
    invited_at = models.DateTimeField(null=True, blank=True)
    accepted_invite_at = models.DateTimeField(null=True, blank=True)
    first_login_at = models.DateTimeField(null=True, blank=True)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
```

#### 1.3 Update TenantMembership Model
**File**: `api/src/backend/api/models.py`

```python
class TenantMembership(models.Model):
    # ... existing fields ...
    
    # Prowler-Specific Permissions
    can_run_scans = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    can_manage_integrations = models.BooleanField(default=False)
    can_export_reports = models.BooleanField(default=False)
    
    # Invitation
    invited_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)
    invited_at = models.DateTimeField(null=True, blank=True)
    invite_accepted_at = models.DateTimeField(null=True, blank=True)
    invite_token = models.CharField(max_length=500, blank=True, db_index=True)
    invite_expires_at = models.DateTimeField(null=True, blank=True)
```

---

### **Phase 2: SCIM 2.0 API Implementation**

#### 2.1 SCIM Authentication
**File**: `api/src/backend/api/v1/authentication/scim_auth.py`

```python
class SCIMTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        try:
            sso_config = AzureSSOConfig.objects.get(scim_token=token, is_active=True)
            return (sso_config.tenant, token)
        except AzureSSOConfig.DoesNotExist:
            raise AuthenticationFailed('Invalid SCIM token')
```

#### 2.2 SCIM Views
**File**: `api/src/backend/api/v1/views/scim.py`

```python
@api_view(['GET'])
@authentication_classes([SCIMTokenAuthentication])
@permission_classes([AllowAny])
def scim_list_users(request):
    """GET /scim/v2/Users"""
    tenant = request.user  # From SCIMTokenAuthentication
    start_index = int(request.GET.get('startIndex', 1))
    count = int(request.GET.get('count', 100))
    filter_param = request.GET.get('filter', '')
    
    users = User.objects.filter(
        tenant_memberships__tenant=tenant,
        is_sso_user=True,
        is_active=True
    )
    
    # Apply filter if provided
    if filter_param and 'userName eq' in filter_param:
        email = filter_param.split('"')[1]
        users = users.filter(email=email)
    
    total_results = users.count()
    users = users[start_index-1:start_index+count-1]
    
    resources = []
    for user in users:
        resources.append({
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": user.azure_id,
            "externalId": user.azure_id,
            "userName": user.email,
            "name": {
                "givenName": user.first_name,
                "familyName": user.last_name
            },
            "emails": [{"primary": True, "value": user.email}],
            "active": user.is_active,
            "department": user.department,
            "title": user.job_title,
            "phoneNumbers": [{"primary": True, "value": user.phone_number}] if user.phone_number else [],
            "meta": {
                "created": user.created_at.isoformat(),
                "lastModified": user.updated_at.isoformat()
            }
        })
    
    return Response({
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
        "totalResults": total_results,
        "startIndex": start_index,
        "itemsPerPage": count,
        "Resources": resources
    })

@api_view(['POST'])
@authentication_classes([SCIMTokenAuthentication])
@permission_classes([AllowAny])
def scim_create_user(request):
    """POST /scim/v2/Users"""
    tenant = request.user
    scim_service = AzureSCIMService(tenant)
    
    try:
        user = scim_service.handle_user_create(request.data)
        return Response(scim_service._format_scim_user(user), status=201)
    except Exception as e:
        return Response({
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "500",
            "detail": str(e)
        }, status=500)

@api_view(['PATCH'])
@authentication_classes([SCIMTokenAuthentication])
@permission_classes([AllowAny])
def scim_update_user(request, azure_user_id):
    """PATCH /scim/v2/Users/{azure_user_id}"""
    tenant = request.user
    scim_service = AzureSCIMService(tenant)
    
    try:
        user = scim_service.handle_user_update(azure_user_id, request.data)
        return Response(scim_service._format_scim_user(user))
    except Exception as e:
        return Response({
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "500",
            "detail": str(e)
        }, status=500)

@api_view(['DELETE'])
@authentication_classes([SCIMTokenAuthentication])
@permission_classes([AllowAny])
def scim_delete_user(request, azure_user_id):
    """DELETE /scim/v2/Users/{azure_user_id}"""
    tenant = request.user
    scim_service = AzureSCIMService(tenant)
    
    try:
        scim_service.handle_user_delete(azure_user_id)
        return Response(status=204)
    except Exception as e:
        return Response({
            "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
            "status": "500",
            "detail": str(e)
        }, status=500)
```

#### 2.3 SCIM URLs
**File**: `api/src/backend/api/v1/urls.py`

```python
# SCIM 2.0 Endpoints
path('scim/v2/Users/', scim.scim_list_users, name='scim-list-users'),
path('scim/v2/Users', scim.scim_list_users, name='scim-list-users-no-slash'),
path('scim/v2/Users/', scim.scim_create_user, name='scim-create-user'),
path('scim/v2/Users/<str:azure_user_id>/', scim.scim_get_user, name='scim-get-user'),
path('scim/v2/Users/<str:azure_user_id>/', scim.scim_update_user, name='scim-update-user'),
path('scim/v2/Users/<str:azure_user_id>/', scim.scim_delete_user, name='scim-delete-user'),
```

---

### **Phase 3: Azure AD OAuth Implementation**

#### 3.1 Enhanced Azure SCIM Service
**File**: `api/src/backend/api/services/azure_scim_service.py`

```python
class AzureSCIMService:
    def __init__(self, tenant):
        self.tenant = tenant
        self.sso_config = tenant.azure_sso_config
        
    def handle_user_create(self, scim_user_data):
        """Handle SCIM user creation from Azure AD"""
        azure_id = scim_user_data.get('id')
        email = scim_user_data.get('userName')
        first_name = scim_user_data.get('name', {}).get('givenName', '')
        last_name = scim_user_data.get('name', {}).get('familyName', '')
        department = scim_user_data.get('department', '')
        job_title = scim_user_data.get('title', '')
        active = scim_user_data.get('active', True)
        
        # Determine role from Azure AD groups
        groups = scim_user_data.get('groups', [])
        role = self._determine_role_from_groups(groups)
        
        with transaction.atomic():
            # Create user
            user = User.objects.create(
                azure_id=azure_id,
                azure_tenant_id=self.sso_config.azure_tenant_id,
                email=email,
                first_name=first_name,
                last_name=last_name,
                department=department,
                job_title=job_title,
                is_sso_user=True,
                is_active=active,
                primary_tenant=self.tenant
            )
            
            # Create tenant membership
            membership = TenantMembership.objects.create(
                user=user,
                tenant=self.tenant,
                role=role,
                is_active=active
            )
            
            # Set permissions based on role
            self._set_role_permissions(membership, role)
            
            # Log sync event
            AzureUserSync.objects.create(
                tenant=self.tenant,
                user=user,
                azure_user_id=azure_id,
                azure_user_data=scim_user_data,
                action='created',
                status='success'
            )
            
            # Log audit event
            AuditLogService().log_event(
                tenant=self.tenant,
                user=user,
                event_type='AZURE_USER_SYNCED',
                description=f'User {email} synced from Azure AD',
                details={'azure_id': azure_id, 'role': role}
            )
            
            return user
    
    def handle_user_update(self, azure_user_id, scim_user_data):
        """Handle SCIM user update from Azure AD"""
        try:
            user = User.objects.get(azure_id=azure_user_id, primary_tenant=self.tenant)
            
            # Track changes
            changes = {}
            if 'name' in scim_user_data:
                if 'givenName' in scim_user_data['name']:
                    changes['first_name'] = scim_user_data['name']['givenName']
                if 'familyName' in scim_user_data['name']:
                    changes['last_name'] = scim_user_data['name']['familyName']
            
            if 'department' in scim_user_data:
                changes['department'] = scim_user_data['department']
            if 'title' in scim_user_data:
                changes['job_title'] = scim_user_data['title']
            if 'active' in scim_user_data:
                changes['is_active'] = scim_user_data['active']
            
            # Update user
            for field, value in changes.items():
                setattr(user, field, value)
            user.save()
            
            # Update membership if active status changed
            if 'is_active' in changes:
                membership = user.tenant_memberships.get(tenant=self.tenant)
                membership.is_active = changes['is_active']
                membership.save()
            
            # Log sync event
            AzureUserSync.objects.create(
                tenant=self.tenant,
                user=user,
                azure_user_id=azure_user_id,
                azure_user_data=scim_user_data,
                action='updated',
                changes=changes,
                status='success'
            )
            
            return user
            
        except User.DoesNotExist:
            raise ValueError(f"User with Azure ID {azure_user_id} not found")
    
    def handle_user_delete(self, azure_user_id):
        """Handle SCIM user deletion from Azure AD"""
        try:
            user = User.objects.get(azure_id=azure_user_id, primary_tenant=self.tenant)
            
            if self.sso_config.auto_deprovision_users:
                # Soft delete
                user.is_active = False
                user.deactivated_at = timezone.now()
                user.deactivation_reason = 'REMOVED_FROM_AZURE'
                user.save()
                
                # Deactivate membership
                membership = user.tenant_memberships.get(tenant=self.tenant)
                membership.is_active = False
                membership.save()
                
                # Revoke sessions
                # TODO: Implement session revocation
                
                # Log sync event
                AzureUserSync.objects.create(
                    tenant=self.tenant,
                    user=user,
                    azure_user_id=azure_user_id,
                    azure_user_data={},
                    action='deleted',
                    status='success'
                )
                
                # Log audit event
                AuditLogService().log_event(
                    tenant=self.tenant,
                    user=user,
                    event_type='AZURE_USER_REMOVED',
                    description=f'User {user.email} deactivated from Azure AD',
                    details={'azure_id': azure_user_id}
                )
            
        except User.DoesNotExist:
            raise ValueError(f"User with Azure ID {azure_user_id} not found")
    
    def _determine_role_from_groups(self, groups):
        """Map Azure AD groups to roles"""
        group_role_mapping = self.sso_config.group_role_mapping
        
        for group in groups:
            group_id = group.get('value')
            if group_id in group_role_mapping:
                return group_role_mapping[group_id]
        
        return 'viewer'  # Default role
    
    def _set_role_permissions(self, membership, role):
        """Set permissions based on role"""
        role_permissions = {
            'owner': {
                'can_run_scans': True,
                'can_manage_users': True,
                'can_manage_integrations': True,
                'can_export_reports': True
            },
            'admin': {
                'can_run_scans': True,
                'can_manage_users': True,
                'can_manage_integrations': True,
                'can_export_reports': True
            },
            'auditor': {
                'can_run_scans': True,
                'can_manage_users': False,
                'can_manage_integrations': False,
                'can_export_reports': True
            },
            'viewer': {
                'can_run_scans': False,
                'can_manage_users': False,
                'can_manage_integrations': False,
                'can_export_reports': False
            }
        }
        
        permissions = role_permissions.get(role, role_permissions['viewer'])
        for permission, value in permissions.items():
            setattr(membership, permission, value)
        membership.save()
    
    def _format_scim_user(self, user):
        """Format user data for SCIM response"""
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": user.azure_id,
            "externalId": user.azure_id,
            "userName": user.email,
            "name": {
                "givenName": user.first_name,
                "familyName": user.last_name
            },
            "emails": [{"primary": True, "value": user.email}],
            "active": user.is_active,
            "department": user.department,
            "title": user.job_title,
            "phoneNumbers": [{"primary": True, "value": user.phone_number}] if user.phone_number else [],
            "meta": {
                "created": user.created_at.isoformat(),
                "lastModified": user.updated_at.isoformat()
            }
        }
```

---

### **Phase 4: Frontend Implementation**

#### 4.1 Tenant Registration Page
**File**: `ui/app/(auth)/register/page.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { useToast } from '@/hooks/use-toast'

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    company_name: '',
    subdomain: '',
    admin_email: '',
    admin_first_name: '',
    admin_last_name: '',
    terms_accepted: false
  })
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()
  const { toast } = useToast()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const response = await fetch('/api/v1/tenant/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })

      if (response.ok) {
        const data = await response.json()
        toast({
          title: "Success",
          description: "Tenant created successfully!",
        })
        router.push(`http://${formData.subdomain}.localhost:3000/setup-sso`)
      } else {
        const error = await response.json()
        toast({
          title: "Error",
          description: error.message || "Registration failed",
          variant: "destructive"
        })
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "An unexpected error occurred",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Create Your Organization</CardTitle>
          <CardDescription>
            Set up your Prowler security compliance platform
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="company_name">Company Name</Label>
              <Input
                id="company_name"
                value={formData.company_name}
                onChange={(e) => setFormData(prev => ({ ...prev, company_name: e.target.value }))}
                required
              />
            </div>
            
            <div>
              <Label htmlFor="subdomain">Subdomain</Label>
              <Input
                id="subdomain"
                value={formData.subdomain}
                onChange={(e) => setFormData(prev => ({ ...prev, subdomain: e.target.value.toLowerCase() }))}
                placeholder="yourcompany"
                required
              />
              <p className="text-sm text-gray-500">
                Your dashboard will be at: {formData.subdomain || 'yourcompany'}.localhost:3000
              </p>
            </div>
            
            <div>
              <Label htmlFor="admin_email">Admin Email</Label>
              <Input
                id="admin_email"
                type="email"
                value={formData.admin_email}
                onChange={(e) => setFormData(prev => ({ ...prev, admin_email: e.target.value }))}
                required
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="admin_first_name">First Name</Label>
                <Input
                  id="admin_first_name"
                  value={formData.admin_first_name}
                  onChange={(e) => setFormData(prev => ({ ...prev, admin_first_name: e.target.value }))}
                  required
                />
              </div>
              <div>
                <Label htmlFor="admin_last_name">Last Name</Label>
                <Input
                  id="admin_last_name"
                  value={formData.admin_last_name}
                  onChange={(e) => setFormData(prev => ({ ...prev, admin_last_name: e.target.value }))}
                  required
                />
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <Checkbox
                id="terms"
                checked={formData.terms_accepted}
                onCheckedChange={(checked) => setFormData(prev => ({ ...prev, terms_accepted: !!checked }))}
              />
              <Label htmlFor="terms" className="text-sm">
                I agree to the Terms of Service and Privacy Policy
              </Label>
            </div>
            
            <Button type="submit" className="w-full" disabled={isLoading || !formData.terms_accepted}>
              {isLoading ? "Creating..." : "Create Organization"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
```

#### 4.2 SSO Setup Page
**File**: `ui/app/(dashboard)/setup-sso/page.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useToast } from '@/hooks/use-toast'
import { Copy, Check, ExternalLink } from 'lucide-react'

export default function SetupSSOPage() {
  const [step, setStep] = useState(1)
  const [azureConfig, setAzureConfig] = useState({
    azure_tenant_id: '',
    client_id: '',
    client_secret: ''
  })
  const [scimConfig, setScimConfig] = useState({
    scim_url: '',
    scim_token: ''
  })
  const [isLoading, setIsLoading] = useState(false)
  const [copied, setCopied] = useState('')
  const router = useRouter()
  const { toast } = useToast()

  const handleAzureSetup = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/v1/tenant/setup-sso', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(azureConfig)
      })

      if (response.ok) {
        const data = await response.json()
        setScimConfig({
          scim_url: data.scim_url,
          scim_token: data.scim_bearer_token
        })
        setStep(2)
        toast({
          title: "Success",
          description: "Azure AD SSO configured successfully!",
        })
      } else {
        const error = await response.json()
        toast({
          title: "Error",
          description: error.message || "SSO setup failed",
          variant: "destructive"
        })
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "An unexpected error occurred",
        variant: "destructive"
      })
    } finally {
      setIsLoading(false)
    }
  }

  const copyToClipboard = (text: string, type: string) => {
    navigator.clipboard.writeText(text)
    setCopied(type)
    setTimeout(() => setCopied(''), 2000)
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold">Azure AD SSO Setup</h1>
          <p className="text-gray-600 mt-2">
            Configure Azure Active Directory integration for your organization
          </p>
        </div>

        <Tabs value={step.toString()} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="1">Azure AD Configuration</TabsTrigger>
            <TabsTrigger value="2">SCIM Configuration</TabsTrigger>
            <TabsTrigger value="3">Sync Users</TabsTrigger>
          </TabsList>

          <TabsContent value="1">
            <Card>
              <CardHeader>
                <CardTitle>Azure AD Configuration</CardTitle>
                <CardDescription>
                  Enter your Azure AD application credentials
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="azure_tenant_id">Azure Tenant ID</Label>
                  <Input
                    id="azure_tenant_id"
                    value={azureConfig.azure_tenant_id}
                    onChange={(e) => setAzureConfig(prev => ({ ...prev, azure_tenant_id: e.target.value }))}
                    placeholder="12345678-1234-1234-1234-123456789012"
                  />
                </div>
                
                <div>
                  <Label htmlFor="client_id">Client ID (Application ID)</Label>
                  <Input
                    id="client_id"
                    value={azureConfig.client_id}
                    onChange={(e) => setAzureConfig(prev => ({ ...prev, client_id: e.target.value }))}
                    placeholder="12345678-1234-1234-1234-123456789012"
                  />
                </div>
                
                <div>
                  <Label htmlFor="client_secret">Client Secret</Label>
                  <Input
                    id="client_secret"
                    type="password"
                    value={azureConfig.client_secret}
                    onChange={(e) => setAzureConfig(prev => ({ ...prev, client_secret: e.target.value }))}
                    placeholder="Enter your client secret"
                  />
                </div>
                
                <Button onClick={handleAzureSetup} disabled={isLoading}>
                  {isLoading ? "Testing Connection..." : "Test Connection & Continue"}
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="2">
            <Card>
              <CardHeader>
                <CardTitle>SCIM Configuration</CardTitle>
                <CardDescription>
                  Configure SCIM provisioning in Azure AD Enterprise App
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <Label>SCIM URL</Label>
                  <div className="flex items-center space-x-2">
                    <Input value={scimConfig.scim_url} readOnly />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(scimConfig.scim_url, 'url')}
                    >
                      {copied === 'url' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                
                <div>
                  <Label>Bearer Token</Label>
                  <div className="flex items-center space-x-2">
                    <Input value={scimConfig.scim_token} readOnly type="password" />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(scimConfig.scim_token, 'token')}
                    >
                      {copied === 'token' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h4 className="font-semibold mb-2">Azure AD Enterprise App Setup Instructions:</h4>
                  <ol className="list-decimal list-inside space-y-2 text-sm">
                    <li>Go to Azure Portal → Enterprise Applications</li>
                    <li>Create a new Enterprise Application</li>
                    <li>Go to Provisioning → Configure provisioning</li>
                    <li>Set Provisioning Mode to "Automatic"</li>
                    <li>Enter the SCIM URL and Bearer Token above</li>
                    <li>Test Connection and Save</li>
                  </ol>
                </div>
                
                <Button onClick={() => setStep(3)}>
                  Continue to User Sync
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="3">
            <Card>
              <CardHeader>
                <CardTitle>Sync Users from Azure AD</CardTitle>
                <CardDescription>
                  Import users from your Azure AD directory
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button onClick={() => router.push('/dashboard/users')}>
                  Sync Users Now
                </Button>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
```

---

### **Phase 5: Celery Background Tasks**

#### 5.1 Sync Tasks
**File**: `api/src/backend/api/tasks/sync_tasks.py`

```python
from celery import shared_task
from django.utils import timezone
from api.services.azure_scim_service import AzureSCIMService
from api.models import Tenant, AzureSSOConfig

@shared_task
def sync_azure_users_task(tenant_id):
    """Sync users from Azure AD for a specific tenant"""
    try:
        tenant = Tenant.objects.get(id=tenant_id)
        sso_config = tenant.azure_sso_config
        
        if not sso_config or not sso_config.is_active:
            return {"status": "skipped", "reason": "SSO not configured"}
        
        scim_service = AzureSCIMService(tenant)
        stats = scim_service.sync_all_users()
        
        # Update sync status
        sso_config.last_sync_at = timezone.now()
        sso_config.last_sync_status = 'success' if stats['errors'] == 0 else 'partial'
        sso_config.save()
        
        return {
            "status": "completed",
            "stats": stats
        }
        
    except Exception as e:
        # Update sync status with error
        sso_config.last_sync_at = timezone.now()
        sso_config.last_sync_status = 'failed'
        sso_config.last_sync_error = str(e)
        sso_config.save()
        
        return {
            "status": "failed",
            "error": str(e)
        }

@shared_task
def periodic_azure_sync():
    """Periodic sync for all tenants with SCIM enabled"""
    tenants = Tenant.objects.filter(
        azure_sso_config__is_active=True,
        azure_sso_config__scim_enabled=True
    )
    
    results = []
    for tenant in tenants:
        result = sync_azure_users_task.delay(tenant.id)
        results.append({
            "tenant_id": str(tenant.id),
            "task_id": result.id
        })
    
    return {
        "status": "started",
        "tasks": results
    }

@shared_task
def cleanup_expired_invites():
    """Clean up expired invitations"""
    from api.models import TenantMembership
    from django.utils import timezone
    
    expired_invites = TenantMembership.objects.filter(
        invite_expires_at__lt=timezone.now(),
        invite_accepted_at__isnull=True
    )
    
    count = expired_invites.count()
    expired_invites.update(
        invite_token='',
        invite_expires_at=None
    )
    
    return {
        "status": "completed",
        "expired_invites_cleaned": count
    }
```

---

### **Phase 6: Email Templates Enhancement**

#### 6.1 Enhanced Invitation Email
**File**: `api/src/backend/templates/emails/invitation.html`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>You're Invited to Join {{ tenant.name }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2563eb; color: white; padding: 20px; text-align: center; }
        .content { padding: 30px 20px; }
        .button { display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }
        .footer { background: #f8fafc; padding: 20px; text-align: center; font-size: 14px; color: #666; }
        .role-info { background: #f0f9ff; padding: 15px; border-radius: 6px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>You're Invited to Join {{ tenant.name }}</h1>
        </div>
        
        <div class="content">
            <p>Hello {{ user.first_name }},</p>
            
            <p>You've been invited to join <strong>{{ tenant.name }}</strong> on the Prowler security compliance platform.</p>
            
            <div class="role-info">
                <h3>Your Role: {{ membership.role|title }}</h3>
                <p>With this role, you can:</p>
                <ul>
                    {% if membership.can_run_scans %}<li>Run security scans</li>{% endif %}
                    {% if membership.can_manage_users %}<li>Manage team members</li>{% endif %}
                    {% if membership.can_manage_integrations %}<li>Configure integrations</li>{% endif %}
                    {% if membership.can_export_reports %}<li>Export compliance reports</li>{% endif %}
                </ul>
            </div>
            
            <p>Click the button below to accept your invitation and get started:</p>
            
            <a href="{{ magic_link }}" class="button">Accept Invitation</a>
            
            <p><strong>Important:</strong> This invitation will expire in 7 days.</p>
            
            <p>If you have any questions, please contact your administrator.</p>
            
            <p>Best regards,<br>The {{ tenant.name }} Team</p>
        </div>
        
        <div class="footer">
            <p>This invitation was sent by {{ invited_by.email }} on {{ invited_at|date:"F d, Y" }}</p>
            <p>If you didn't expect this invitation, you can safely ignore this email.</p>
        </div>
    </div>
</body>
</html>
```

---

## 🚀 Implementation Timeline

### **Week 1: Database & Backend**
- [ ] Consolidate Azure AD models
- [ ] Update User and TenantMembership models
- [ ] Create SCIM 2.0 API endpoints
- [ ] Implement AzureSCIMService

### **Week 2: Frontend & OAuth**
- [ ] Create tenant registration page
- [ ] Build SSO setup wizard
- [ ] Implement Azure AD OAuth flow
- [ ] Create user management dashboard

### **Week 3: Integration & Testing**
- [ ] Implement Celery background tasks
- [ ] Enhance email templates
- [ ] End-to-end testing
- [ ] Documentation and deployment

### **Week 4: Polish & Launch**
- [ ] Performance optimization
- [ ] Security audit
- [ ] User acceptance testing
- [ ] Production deployment

---

This comprehensive plan provides a complete implementation roadmap for the Azure AD SSO + SCIM 2.0 integration, building on the existing foundation while adding all the missing pieces for a production-ready enterprise onboarding system.
