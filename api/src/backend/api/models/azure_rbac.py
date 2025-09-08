"""
Enhanced Azure AD RBAC Models for Multi-Tenant SaaS
"""

import uuid
import json
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from cryptography.fernet import Fernet
from django.conf import settings

User = get_user_model()


class Company(models.Model):
    """
    Represents a company/organization that uses the SaaS platform.
    Stores Azure AD tenant credentials and configuration.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Company name")
    domain = models.CharField(max_length=255, unique=True, help_text="Primary email domain")
    
    # Azure AD Tenant Configuration
    azure_tenant_id = models.CharField(max_length=255, unique=True, help_text="Azure AD Tenant ID")
    azure_client_id = models.CharField(max_length=255, help_text="Azure AD Application Client ID")
    _azure_client_secret = models.BinaryField(db_column="azure_client_secret", help_text="Encrypted Azure AD Client Secret")
    
    # Azure AD Configuration
    azure_redirect_uri = models.URLField(help_text="Azure AD Redirect URI")
    azure_scopes = models.JSONField(default=list, help_text="Azure AD OAuth Scopes")
    azure_allowed_domains = models.JSONField(default=list, help_text="Allowed email domains")
    
    # Company Settings
    is_active = models.BooleanField(default=True, help_text="Whether the company is active")
    trial_start = models.DateTimeField(null=True, blank=True, help_text="Trial start date")
    trial_end = models.DateTimeField(null=True, blank=True, help_text="Trial end date")
    subscription_tier = models.CharField(
        max_length=50,
        choices=[
            ('trial', 'Trial'),
            ('basic', 'Basic'),
            ('professional', 'Professional'),
            ('enterprise', 'Enterprise'),
        ],
        default='trial'
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_companies')
    
    class Meta:
        db_table = 'companies'
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def azure_client_secret(self):
        """Decrypt and return the Azure client secret"""
        if not self._azure_client_secret:
            return None
        
        try:
            # Use the same encryption key as other secrets
            fernet = Fernet(settings.SECRETS_ENCRYPTION_KEY.encode())
            decrypted_data = fernet.decrypt(self._azure_client_secret)
            return decrypted_data.decode()
        except Exception as e:
            raise ValidationError(f"Failed to decrypt client secret: {e}")
    
    @azure_client_secret.setter
    def azure_client_secret(self, value):
        """Encrypt and store the Azure client secret"""
        if not value:
            self._azure_client_secret = None
            return
        
        try:
            fernet = Fernet(settings.SECRETS_ENCRYPTION_KEY.encode())
            encrypted_data = fernet.encrypt(value.encode())
            self._azure_client_secret = encrypted_data
        except Exception as e:
            raise ValidationError(f"Failed to encrypt client secret: {e}")
    
    def is_trial_active(self):
        """Check if company is in active trial period"""
        if not self.trial_end:
            return False
        return timezone.now() < self.trial_end
    
    def get_azure_authority_url(self):
        """Get Azure AD authority URL for this company"""
        return f"https://login.microsoftonline.com/{self.azure_tenant_id}"


class AzureADGroupMapping(models.Model):
    """
    Maps Azure AD groups to application roles for a specific company
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='azure_group_mappings')
    
    # Azure AD Group Information
    azure_group_id = models.CharField(max_length=255, help_text="Azure AD Group ID")
    azure_group_name = models.CharField(max_length=255, help_text="Azure AD Group Display Name")
    azure_group_description = models.TextField(blank=True, help_text="Azure AD Group Description")
    
    # Application Role Mapping
    role = models.ForeignKey('Role', on_delete=models.CASCADE, related_name='azure_group_mappings')
    
    # Configuration
    is_active = models.BooleanField(default=True, help_text="Whether this mapping is active")
    auto_sync = models.BooleanField(default=True, help_text="Automatically sync group members")
    sync_frequency = models.IntegerField(default=3600, help_text="Sync frequency in seconds")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'azure_ad_group_mappings'
        verbose_name = 'Azure AD Group Mapping'
        verbose_name_plural = 'Azure AD Group Mappings'
        unique_together = ['company', 'azure_group_id']
        ordering = ['azure_group_name']
    
    def __str__(self):
        return f"{self.company.name}: {self.azure_group_name} -> {self.role.name}"


class AzureADUserProfile(models.Model):
    """
    Extended user profile for Azure AD users with company context
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='azure_profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='azure_users')
    
    # Azure AD User Information
    azure_ad_id = models.CharField(max_length=255, help_text="Azure AD User ID")
    azure_ad_object_id = models.CharField(max_length=255, help_text="Azure AD Object ID")
    
    # Extended Profile Information
    job_title = models.CharField(max_length=255, blank=True, help_text="Job title from Azure AD")
    department = models.CharField(max_length=255, blank=True, help_text="Department from Azure AD")
    office_location = models.CharField(max_length=255, blank=True, help_text="Office location from Azure AD")
    business_phones = models.JSONField(default=list, help_text="Business phone numbers")
    mobile_phone = models.CharField(max_length=50, blank=True, help_text="Mobile phone number")
    preferred_language = models.CharField(max_length=10, blank=True, help_text="Preferred language")
    photo_url = models.URLField(blank=True, help_text="Profile photo URL")
    
    # Azure AD Groups (cached)
    azure_groups = models.JSONField(default=list, help_text="Azure AD groups user belongs to")
    
    # Sync Information
    last_synced_at = models.DateTimeField(auto_now=True)
    sync_status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending'),
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('partial', 'Partial Success'),
        ],
        default='pending'
    )
    sync_error = models.TextField(blank=True, help_text="Last sync error message")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'azure_ad_user_profiles'
        verbose_name = 'Azure AD User Profile'
        verbose_name_plural = 'Azure AD User Profiles'
        unique_together = ['company', 'azure_ad_id']
    
    def __str__(self):
        return f"{self.user.email} - {self.company.name}"


class AzureADTokenCache(models.Model):
    """
    Cache Azure AD tokens for users to avoid repeated token exchanges
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='azure_token_cache')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='azure_tokens')
    
    # Token Information
    access_token = models.TextField(help_text="Azure AD access token")
    refresh_token = models.TextField(help_text="Azure AD refresh token")
    id_token = models.TextField(help_text="Azure AD ID token")
    token_type = models.CharField(max_length=50, default='Bearer')
    scope = models.TextField(help_text="Token scope")
    
    # Expiration
    expires_at = models.DateTimeField(help_text="Token expiration time")
    issued_at = models.DateTimeField(auto_now_add=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'azure_ad_token_cache'
        verbose_name = 'Azure AD Token Cache'
        verbose_name_plural = 'Azure AD Token Caches'
        unique_together = ['user', 'company']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.company.name}"
    
    @property
    def is_expired(self):
        """Check if token is expired"""
        return timezone.now() > self.expires_at
    
    @property
    def is_expiring_soon(self):
        """Check if token expires within 5 minutes"""
        return timezone.now() > (self.expires_at - timezone.timedelta(minutes=5))


class UserRoleAssignment(models.Model):
    """
    Maps users to roles with assignment source tracking
    """
    
    ASSIGNMENT_SOURCE_CHOICES = [
        ('direct', 'Direct Assignment'),
        ('azure_group', 'Azure AD Group'),
        ('custom_group', 'Custom Group'),
        ('inherited', 'Inherited'),
        ('default', 'Default Role'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_assignments')
    role = models.ForeignKey('Role', on_delete=models.CASCADE, related_name='user_assignments')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='user_role_assignments')
    
    # Assignment Details
    assignment_source = models.CharField(
        max_length=50,
        choices=ASSIGNMENT_SOURCE_CHOICES,
        default='direct',
        help_text="How this role was assigned"
    )
    source_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="Reference to source (e.g., Azure group ID)"
    )
    
    # Assignment Metadata
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_roles',
        help_text="User who assigned this role"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Role expiration date")
    is_active = models.BooleanField(default=True, help_text="Whether this assignment is active")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_role_assignments'
        verbose_name = 'User Role Assignment'
        verbose_name_plural = 'User Role Assignments'
        unique_together = ['user', 'role', 'company']
        ordering = ['-assigned_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.role.name} ({self.company.name})"
    
    @property
    def is_expired(self):
        """Check if role assignment is expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at


class AuditLog(models.Model):
    """
    Comprehensive audit log for all user actions and system events
    """
    
    ACTION_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('role_assigned', 'Role Assigned'),
        ('role_removed', 'Role Removed'),
        ('permission_granted', 'Permission Granted'),
        ('permission_denied', 'Permission Denied'),
        ('data_access', 'Data Access'),
        ('data_modified', 'Data Modified'),
        ('azure_sync', 'Azure AD Sync'),
        ('group_sync', 'Group Sync'),
        ('token_refresh', 'Token Refresh'),
        ('profile_update', 'Profile Update'),
        ('company_created', 'Company Created'),
        ('company_updated', 'Company Updated'),
        ('error', 'Error'),
        ('security_event', 'Security Event'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User and Company Context
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    
    # Action Details
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    action_description = models.TextField(help_text="Human-readable description of the action")
    resource_type = models.CharField(max_length=100, blank=True, help_text="Type of resource affected")
    resource_id = models.CharField(max_length=255, blank=True, help_text="ID of resource affected")
    
    # Request Context
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    request_method = models.CharField(max_length=10, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    
    # Additional Data
    details = models.JSONField(default=dict, help_text="Additional action details")
    metadata = models.JSONField(default=dict, help_text="System metadata")
    
    # Result
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, help_text="Error message if action failed")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['company', 'created_at']),
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['success', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email if self.user else 'System'} - {self.action_type} - {self.created_at}"
    
    @classmethod
    def log_action(cls, user=None, company=None, action_type=None, **kwargs):
        """
        Convenience method to create audit log entries
        """
        return cls.objects.create(
            user=user,
            company=company,
            action_type=action_type,
            **kwargs
        )


class Permission(models.Model):
    """
    Granular permissions for fine-grained access control
    """
    
    PERMISSION_CATEGORIES = [
        ('user_management', 'User Management'),
        ('company_management', 'Company Management'),
        ('provider_management', 'Provider Management'),
        ('scan_management', 'Scan Management'),
        ('compliance_management', 'Compliance Management'),
        ('integration_management', 'Integration Management'),
        ('audit_access', 'Audit Access'),
        ('billing_management', 'Billing Management'),
        ('system_admin', 'System Administration'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, help_text="Permission name (e.g., 'users.create')")
    display_name = models.CharField(max_length=255, help_text="Human-readable permission name")
    description = models.TextField(help_text="Permission description")
    category = models.CharField(max_length=50, choices=PERMISSION_CATEGORIES)
    
    # Permission Scope
    resource_type = models.CharField(max_length=100, blank=True, help_text="Resource type this permission applies to")
    action = models.CharField(max_length=50, help_text="Action (create, read, update, delete, execute)")
    
    # Configuration
    is_system_permission = models.BooleanField(default=False, help_text="System-level permission")
    is_active = models.BooleanField(default=True, help_text="Whether this permission is active")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'permissions'
        verbose_name = 'Permission'
        verbose_name_plural = 'Permissions'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.display_name} ({self.name})"


class RolePermission(models.Model):
    """
    Maps roles to specific permissions
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey('Role', on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='role_permissions')
    
    # Permission Configuration
    granted = models.BooleanField(default=True, help_text="Whether this permission is granted")
    conditions = models.JSONField(default=dict, help_text="Additional conditions for this permission")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'role_permissions'
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'
        unique_together = ['role', 'permission']
    
    def __str__(self):
        return f"{self.role.name} - {self.permission.display_name}"
