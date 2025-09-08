"""
Enhanced Role Model for Azure AD RBAC Integration
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from api.models import RowLevelSecurityProtectedModel, PermissionChoices
from django.db.models import Q

User = get_user_model()


class EnhancedRole(RowLevelSecurityProtectedModel):
    """
    Enhanced Role model that integrates with Azure AD RBAC system
    Maintains backward compatibility with existing Role model
    """
    
    ROLE_TYPES = [
        ('system', 'System Role'),
        ('company', 'Company Role'),
        ('azure_sync', 'Azure AD Synced Role'),
        ('custom', 'Custom Role'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Role Information
    name = models.CharField(max_length=255, help_text="Role name")
    display_name = models.CharField(max_length=255, help_text="Human-readable role name")
    description = models.TextField(blank=True, help_text="Role description")
    role_type = models.CharField(max_length=50, choices=ROLE_TYPES, default='company')
    
    # Legacy Permission Fields (for backward compatibility)
    manage_users = models.BooleanField(default=False, help_text="Can manage users")
    manage_account = models.BooleanField(default=False, help_text="Can manage account settings")
    manage_billing = models.BooleanField(default=False, help_text="Can manage billing")
    manage_providers = models.BooleanField(default=False, help_text="Can manage providers")
    manage_integrations = models.BooleanField(default=False, help_text="Can manage integrations")
    manage_scans = models.BooleanField(default=False, help_text="Can manage scans")
    unlimited_visibility = models.BooleanField(default=False, help_text="Has unlimited visibility")
    
    # Azure AD Integration
    azure_group_id = models.CharField(max_length=255, blank=True, help_text="Azure AD Group ID")
    azure_group_name = models.CharField(max_length=255, blank=True, help_text="Azure AD Group Name")
    auto_sync_from_azure = models.BooleanField(default=False, help_text="Auto-sync from Azure AD")
    
    # Role Configuration
    is_system_role = models.BooleanField(default=False, help_text="System-level role")
    is_active = models.BooleanField(default=True, help_text="Whether this role is active")
    is_default = models.BooleanField(default=False, help_text="Default role for new users")
    priority = models.IntegerField(default=0, help_text="Role priority (higher = more important)")
    
    # Relationships
    provider_groups = models.ManyToManyField(
        'ProviderGroup', 
        through="RoleProviderGroupRelationship", 
        related_name="enhanced_roles",
        blank=True
    )
    users = models.ManyToManyField(
        User, 
        through="UserRoleAssignment", 
        related_name="enhanced_roles",
        blank=True
    )
    permissions = models.ManyToManyField(
        'Permission',
        through="RolePermission",
        related_name="roles",
        blank=True
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_roles'
    )
    
    # Legacy compatibility fields
    PERMISSION_FIELDS = [
        "manage_users",
        "manage_account", 
        "manage_billing",
        "manage_providers",
        "manage_integrations",
        "manage_scans",
    ]
    
    class Meta:
        db_table = "enhanced_roles"
        verbose_name = "Enhanced Role"
        verbose_name_plural = "Enhanced Roles"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="unique_enhanced_role_per_tenant",
            ),
            models.UniqueConstraint(
                fields=["tenant_id", "azure_group_id"],
                condition=Q(azure_group_id__isnull=False),
                name="unique_azure_group_per_tenant",
            ),
        ]
        ordering = ['-priority', 'name']
    
    class JSONAPIMeta:
        resource_name = "enhanced-roles"
    
    def __str__(self):
        return f"{self.display_name} ({self.name})"
    
    @property
    def permission_state(self):
        """Calculate permission state based on legacy fields"""
        values = [getattr(self, field) for field in self.PERMISSION_FIELDS]
        if all(values):
            return PermissionChoices.UNLIMITED
        elif not any(values):
            return PermissionChoices.NONE
        else:
            return PermissionChoices.LIMITED
    
    @classmethod
    def filter_by_permission_state(cls, queryset, value):
        """Filter roles by permission state"""
        q_all_true = Q(**{field: True for field in cls.PERMISSION_FIELDS})
        q_all_false = Q(**{field: False for field in cls.PERMISSION_FIELDS})
        
        if value == PermissionChoices.UNLIMITED:
            return queryset.filter(q_all_true)
        elif value == PermissionChoices.NONE:
            return queryset.filter(q_all_false)
        else:
            return queryset.exclude(q_all_true | q_all_false)
    
    def has_permission(self, permission_name):
        """Check if role has a specific permission"""
        try:
            from api.models.azure_rbac import Permission
            permission = Permission.objects.get(name=permission_name)
            return self.permissions.filter(
                id=permission.id,
                rolepermission__granted=True
            ).exists()
        except Permission.DoesNotExist:
            return False
    
    def get_permissions(self):
        """Get all permissions for this role"""
        return self.permissions.filter(rolepermission__granted=True)
    
    def add_permission(self, permission_name, granted=True, conditions=None):
        """Add a permission to this role"""
        try:
            from api.models.azure_rbac import Permission, RolePermission
            permission = Permission.objects.get(name=permission_name)
            role_permission, created = RolePermission.objects.get_or_create(
                role=self,
                permission=permission,
                defaults={
                    'granted': granted,
                    'conditions': conditions or {}
                }
            )
            if not created:
                role_permission.granted = granted
                role_permission.conditions = conditions or {}
                role_permission.save()
            return role_permission
        except Permission.DoesNotExist:
            return None
    
    def remove_permission(self, permission_name):
        """Remove a permission from this role"""
        try:
            from api.models.azure_rbac import Permission, RolePermission
            permission = Permission.objects.get(name=permission_name)
            RolePermission.objects.filter(role=self, permission=permission).delete()
            return True
        except Permission.DoesNotExist:
            return False
    
    def sync_from_azure_group(self, azure_group_data):
        """Sync role data from Azure AD group"""
        if not self.auto_sync_from_azure:
            return False
        
        self.azure_group_name = azure_group_data.get('displayName', '')
        self.description = azure_group_data.get('description', '')
        self.save()
        return True
    
    def get_users_count(self):
        """Get count of users assigned to this role"""
        return self.users.filter(userroleassignment__is_active=True).count()
    
    def get_azure_group_members(self, access_token):
        """Get members of the Azure AD group for this role"""
        if not self.azure_group_id:
            return []
        
        try:
            import requests
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                f'https://graph.microsoft.com/v1.0/groups/{self.azure_group_id}/members',
                headers=headers
            )
            response.raise_for_status()
            return response.json().get('value', [])
        except Exception:
            return []
    
    @classmethod
    def create_default_roles(cls, tenant_id):
        """Create default roles for a new tenant"""
        default_roles = [
            {
                'name': 'admin',
                'display_name': 'Administrator',
                'description': 'Full administrative access',
                'role_type': 'system',
                'manage_users': True,
                'manage_account': True,
                'manage_billing': True,
                'manage_providers': True,
                'manage_integrations': True,
                'manage_scans': True,
                'unlimited_visibility': True,
                'priority': 100,
                'is_default': False,
            },
            {
                'name': 'user',
                'display_name': 'User',
                'description': 'Standard user access',
                'role_type': 'company',
                'manage_users': False,
                'manage_account': False,
                'manage_billing': False,
                'manage_providers': False,
                'manage_integrations': False,
                'manage_scans': True,
                'unlimited_visibility': False,
                'priority': 10,
                'is_default': True,
            },
            {
                'name': 'viewer',
                'display_name': 'Viewer',
                'description': 'Read-only access',
                'role_type': 'company',
                'manage_users': False,
                'manage_account': False,
                'manage_billing': False,
                'manage_providers': False,
                'manage_integrations': False,
                'manage_scans': False,
                'unlimited_visibility': False,
                'priority': 1,
                'is_default': False,
            },
        ]
        
        created_roles = []
        for role_data in default_roles:
            role_data['tenant_id'] = tenant_id
            role, created = cls.objects.get_or_create(
                tenant_id=tenant_id,
                name=role_data['name'],
                defaults=role_data
            )
            if created:
                created_roles.append(role)
        
        return created_roles
