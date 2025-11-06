"""
Azure AD SSO Models for Multi-Tenant SaaS
Consolidated models for Azure AD integration and SCIM provisioning
"""

import uuid
import secrets
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from cryptography.fernet import Fernet
from django.conf import settings

from api.utils.encryption import encrypt_field, decrypt_field

User = get_user_model()


class AzureSSOConfig(models.Model):
    """
    OneToOne relationship with Tenant for Azure AD SSO configuration
    Stores Azure AD credentials and SCIM configuration
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField('api.Tenant', on_delete=models.CASCADE, related_name='azure_sso_config')
    
    # Azure Credentials
    azure_tenant_id = models.CharField(max_length=255, db_index=True, help_text="Azure AD Tenant ID")
    client_id = models.CharField(max_length=255, help_text="Azure AD Application Client ID")
    client_secret = models.CharField(max_length=500, help_text="Encrypted Azure AD Client Secret")
    authority = models.URLField(help_text="Azure AD Authority URL")
    authorization_endpoint = models.URLField(help_text="OAuth2 Authorization Endpoint")
    token_endpoint = models.URLField(help_text="OAuth2 Token Endpoint")
    
    # SCIM Configuration
    scim_enabled = models.BooleanField(default=True, help_text="Enable SCIM provisioning")
    scim_token = models.CharField(max_length=255, unique=True, help_text="SCIM Bearer Token")
    scim_base_url = models.URLField(help_text="SCIM Base URL")
    
    # Sync Settings
    auto_provision_users = models.BooleanField(default=True, help_text="Auto-create users from Azure AD")
    auto_deprovision_users = models.BooleanField(default=True, help_text="Auto-deactivate removed users")
    sync_user_attributes = models.BooleanField(default=True, help_text="Sync user profile attributes")
    
    # Mappings (JSON fields)
    attribute_mapping = models.JSONField(
        default=dict,
        help_text="Azure AD attribute to local field mapping"
    )
    group_role_mapping = models.JSONField(
        default=dict,
        help_text="Azure AD group ID to role mapping"
    )
    
    # Sync Status
    last_sync_at = models.DateTimeField(null=True, blank=True, help_text="Last successful sync")
    last_sync_status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('partial', 'Partial Success')
        ],
        default='success',
        help_text="Last sync status"
    )
    last_sync_error = models.TextField(blank=True, help_text="Last sync error message")
    
    # Status
    is_active = models.BooleanField(default=True, help_text="Whether SSO is active")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'azure_sso_config'
        verbose_name = 'Azure SSO Configuration'
        verbose_name_plural = 'Azure SSO Configurations'
        indexes = [
            models.Index(fields=['azure_tenant_id']),
            models.Index(fields=['scim_token']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - Azure SSO Config"
    
    def save(self, *args, **kwargs):
        # Generate SCIM token if not provided
        if not self.scim_token:
            self.scim_token = secrets.token_urlsafe(32)
        
        # Set default attribute mapping if not provided
        if not self.attribute_mapping:
            self.attribute_mapping = {
                "email": "mail",
                "first_name": "givenName",
                "last_name": "surname",
                "department": "department",
                "job_title": "jobTitle",
                "phone_number": "mobilePhone"
            }
        
        super().save(*args, **kwargs)
    
    def get_scim_url(self):
        """Get the SCIM endpoint URL for this tenant"""
        return f"{self.scim_base_url}/scim/v2"
    
    def get_client_secret(self):
        """Get decrypted client secret"""
        return decrypt_field(self.client_secret)
    
    def set_client_secret(self, value):
        """Set encrypted client secret"""
        self.client_secret = encrypt_field(value)
    
    def test_connection(self):
        """Test Azure AD connection"""
        try:
            import requests
            
            # Test token endpoint
            token_data = {
                'client_id': self.client_id,
                'client_secret': self.get_client_secret(),
                'scope': 'https://graph.microsoft.com/.default',
                'grant_type': 'client_credentials'
            }
            
            response = requests.post(
                self.token_endpoint,
                data=token_data,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception:
            return False


class AzureUserSync(models.Model):
    """
    Audit trail for Azure AD sync events
    Tracks all user synchronization operations
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('api.Tenant', on_delete=models.CASCADE, related_name='azure_user_syncs')
    user = models.ForeignKey('api.User', on_delete=models.CASCADE, null=True, blank=True, related_name='azure_syncs')
    azure_user_id = models.CharField(max_length=255, db_index=True, help_text="Azure AD User ID")
    azure_user_data = models.JSONField(help_text="Full Azure AD user object")
    
    action = models.CharField(
        max_length=20,
        choices=[
            ('created', 'Created'),
            ('updated', 'Updated'),
            ('deleted', 'Deleted'),
            ('disabled', 'Disabled'),
            ('enabled', 'Enabled')
        ],
        help_text="Sync action performed"
    )
    
    changes = models.JSONField(
        default=dict,
        help_text="What changed in this sync"
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('skipped', 'Skipped')
        ],
        help_text="Sync operation status"
    )
    
    error_message = models.TextField(blank=True, help_text="Error message if sync failed")
    synced_at = models.DateTimeField(auto_now_add=True, help_text="When sync occurred")
    
    class Meta:
        db_table = 'azure_user_sync'
        verbose_name = 'Azure User Sync'
        verbose_name_plural = 'Azure User Syncs'
        indexes = [
            models.Index(fields=['tenant', 'synced_at']),
            models.Index(fields=['azure_user_id']),
            models.Index(fields=['action']),
            models.Index(fields=['status']),
        ]
        ordering = ['-synced_at']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.azure_user_id} - {self.action} - {self.status}"


class AzureADGroupMapping(models.Model):
    """
    Maps Azure AD groups to local roles for automatic role assignment
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('api.Tenant', on_delete=models.CASCADE, related_name='azure_group_mappings')
    azure_group_id = models.CharField(max_length=255, help_text="Azure AD Group ID")
    azure_group_name = models.CharField(max_length=255, help_text="Azure AD Group Display Name")
    role = models.CharField(
        max_length=20,
        choices=[
            ('owner', 'Owner'),
            ('admin', 'Administrator'),
            ('auditor', 'Auditor'),
            ('viewer', 'Viewer')
        ],
        help_text="Local role to assign"
    )
    is_active = models.BooleanField(default=True, help_text="Whether this mapping is active")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'azure_ad_group_mapping'
        verbose_name = 'Azure AD Group Mapping'
        verbose_name_plural = 'Azure AD Group Mappings'
        unique_together = [['tenant', 'azure_group_id']]
        indexes = [
            models.Index(fields=['tenant', 'azure_group_id']),
            models.Index(fields=['role']),
        ]
        ordering = ['azure_group_name']
    
    def __str__(self):
        return f"{self.tenant.name}: {self.azure_group_name} -> {self.role}"


class AzureADTokenCache(models.Model):
    """
    Caches Azure AD tokens for improved performance
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('api.Tenant', on_delete=models.CASCADE, related_name='azure_token_caches')
    token_type = models.CharField(
        max_length=20,
        choices=[
            ('access', 'Access Token'),
            ('refresh', 'Refresh Token'),
            ('id', 'ID Token')
        ],
        help_text="Type of token"
    )
    token_value = models.TextField(help_text="Encrypted token value")
    expires_at = models.DateTimeField(help_text="Token expiration time")
    scope = models.CharField(max_length=500, blank=True, help_text="Token scope")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'azure_ad_token_cache'
        verbose_name = 'Azure AD Token Cache'
        verbose_name_plural = 'Azure AD Token Caches'
        unique_together = [['tenant', 'token_type', 'scope']]
        indexes = [
            models.Index(fields=['tenant', 'token_type']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.token_type} - {self.expires_at}"
    
    @property
    def is_expired(self):
        """Check if token is expired"""
        return timezone.now() >= self.expires_at
    
    @property
    def is_expiring_soon(self):
        """Check if token expires within 5 minutes"""
        return timezone.now() >= (self.expires_at - timezone.timedelta(minutes=5))


class AzureADUserProfile(models.Model):
    """
    Extended user profile for Azure AD users
    Stores additional profile information from Azure AD
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField('api.User', on_delete=models.CASCADE, related_name='azure_profile_v2')
    tenant = models.ForeignKey('api.Tenant', on_delete=models.CASCADE, related_name='azure_user_profiles')
    
    # Azure AD User Information
    azure_ad_id = models.CharField(max_length=255, unique=True, help_text="Azure AD User ID")
    azure_ad_object_id = models.CharField(max_length=255, help_text="Azure AD Object ID")
    azure_upn = models.CharField(max_length=255, help_text="User Principal Name")
    
    # Extended Profile Information
    job_title = models.CharField(max_length=255, blank=True, help_text="Job title from Azure AD")
    department = models.CharField(max_length=255, blank=True, help_text="Department from Azure AD")
    office_location = models.CharField(max_length=255, blank=True, help_text="Office location")
    business_phones = models.JSONField(default=list, help_text="Business phone numbers")
    mobile_phone = models.CharField(max_length=50, blank=True, help_text="Mobile phone number")
    preferred_language = models.CharField(max_length=10, blank=True, help_text="Preferred language")
    photo_url = models.URLField(blank=True, help_text="Profile photo URL")
    
    # Azure AD Groups (cached)
    azure_groups = models.JSONField(default=list, help_text="Azure AD groups user belongs to")
    
    # Sync Information
    last_synced_at = models.DateTimeField(auto_now=True, help_text="Last sync time")
    sync_status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending'),
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('partial', 'Partial Success'),
        ],
        default='pending',
        help_text="Sync status"
    )
    sync_error = models.TextField(blank=True, help_text="Last sync error message")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'azure_ad_user_profile_v2'
        verbose_name = 'Azure AD User Profile'
        verbose_name_plural = 'Azure AD User Profiles'
        indexes = [
            models.Index(fields=['azure_ad_id']),
            models.Index(fields=['tenant', 'last_synced_at']),
            models.Index(fields=['sync_status']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - Azure Profile"
    
    def get_display_name(self):
        """Get user's display name"""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.user.email
    
    def get_primary_phone(self):
        """Get primary phone number"""
        if self.mobile_phone:
            return self.mobile_phone
        if self.business_phones:
            return self.business_phones[0]
        return None


class AzureADAuditLog(models.Model):
    """
    Comprehensive audit log for Azure AD operations
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('api.Tenant', on_delete=models.CASCADE, related_name='azure_audit_logs')
    user = models.ForeignKey('api.User', on_delete=models.CASCADE, null=True, blank=True, related_name='azure_audit_logs_v2')
    
    event_type = models.CharField(
        max_length=50,
        choices=[
            ('TENANT_CREATED', 'Tenant Created'),
            ('SSO_CONFIGURED', 'SSO Configured'),
            ('SSO_DISABLED', 'SSO Disabled'),
            ('USER_INVITED', 'User Invited'),
            ('USER_ACCEPTED_INVITE', 'User Accepted Invite'),
            ('USER_DEACTIVATED', 'User Deactivated'),
            ('AZURE_USER_SYNCED', 'Azure User Synced'),
            ('AZURE_USER_REMOVED', 'Azure User Removed'),
            ('ROLE_ASSIGNED', 'Role Assigned'),
            ('ROLE_CHANGED', 'Role Changed'),
            ('LOGIN_SUCCESS', 'Login Success'),
            ('SSO_LOGIN', 'SSO Login'),
            ('SCIM_SYNC_STARTED', 'SCIM Sync Started'),
            ('SCIM_SYNC_COMPLETED', 'SCIM Sync Completed'),
            ('SCIM_SYNC_FAILED', 'SCIM Sync Failed'),
            ('GROUP_MAPPING_CREATED', 'Group Mapping Created'),
            ('GROUP_MAPPING_UPDATED', 'Group Mapping Updated'),
            ('TOKEN_REFRESHED', 'Token Refreshed'),
            ('TOKEN_EXPIRED', 'Token Expired'),
        ],
        db_index=True,
        help_text="Type of audit event"
    )
    
    description = models.TextField(help_text="Human-readable description")
    details = models.JSONField(default=dict, help_text="Additional event details")
    
    # Request Information
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text="Client IP address")
    user_agent = models.TextField(blank=True, help_text="User agent string")
    request_id = models.CharField(max_length=100, blank=True, help_text="Request ID for tracing")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'azure_ad_audit_log_v2'
        verbose_name = 'Azure AD Audit Log'
        verbose_name_plural = 'Azure AD Audit Logs'
        indexes = [
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.event_type} - {self.created_at}"
    
    @classmethod
    def log_event(cls, tenant, user=None, event_type=None, description=None, details=None, 
                  ip_address=None, user_agent=None, request_id=None):
        """Convenience method to log an audit event"""
        return cls.objects.create(
            tenant=tenant,
            user=user,
            event_type=event_type,
            description=description,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id
        )
