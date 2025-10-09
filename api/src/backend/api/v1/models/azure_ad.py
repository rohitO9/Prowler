"""
Azure AD Models
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class AzureADGroupMapping(models.Model):
    """Model for mapping Azure AD groups to local roles"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    azure_group_id = models.CharField(max_length=255, unique=True, help_text="Azure AD group ID")
    azure_group_name = models.CharField(max_length=255, help_text="Azure AD group display name")
    role = models.ForeignKey('Role', on_delete=models.CASCADE, related_name='azure_group_mappings')
    is_active = models.BooleanField(default=True, help_text="Whether this mapping is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'azure_ad_group_mapping'
        verbose_name = 'Azure AD Group Mapping'
        verbose_name_plural = 'Azure AD Group Mappings'
        ordering = ['azure_group_name']
    
    def __str__(self):
        return f"{self.azure_group_name} -> {self.role.name}"


class AzureADTenantMapping(models.Model):
    """Model for mapping Azure AD groups to tenants"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('api.Tenant', on_delete=models.CASCADE, related_name='azure_tenant_mappings')
    azure_group_id = models.CharField(max_length=255, unique=True, help_text="Azure AD group ID for tenant")
    azure_group_name = models.CharField(max_length=255, help_text="Azure AD group display name")
    is_active = models.BooleanField(default=True, help_text="Whether this mapping is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'azure_ad_tenant_mapping'
        verbose_name = 'Azure AD Tenant Mapping'
        verbose_name_plural = 'Azure AD Tenant Mappings'
        ordering = ['azure_group_name']
    
    def __str__(self):
        return f"{self.azure_group_name} -> {self.tenant.name}"


class AzureADUserSync(models.Model):
    """Model for tracking Azure AD user synchronization"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='azure_sync_records')
    azure_user_id = models.CharField(max_length=255, help_text="Azure AD user ID")
    sync_type = models.CharField(
        max_length=50,
        choices=[
            ('profile', 'Profile Update'),
            ('groups', 'Group Sync'),
            ('photo', 'Photo Sync'),
            ('full', 'Full Sync'),
        ],
        default='profile'
    )
    status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pending'),
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('partial', 'Partial Success'),
        ],
        default='pending'
    )
    error_message = models.TextField(blank=True, null=True, help_text="Error message if sync failed")
    sync_data = models.JSONField(default=dict, help_text="Data that was synced")
    last_synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'azure_ad_user_sync'
        verbose_name = 'Azure AD User Sync'
        verbose_name_plural = 'Azure AD User Syncs'
        ordering = ['-last_synced_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.sync_type} - {self.status}"


class AzureADTokenCache(models.Model):
    """Model for caching Azure AD tokens"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='azure_token_cache')
    access_token = models.TextField(help_text="Azure AD access token")
    refresh_token = models.TextField(help_text="Azure AD refresh token")
    token_type = models.CharField(max_length=50, default='Bearer')
    expires_at = models.DateTimeField(help_text="Token expiration time")
    scope = models.TextField(blank=True, help_text="Token scope")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'azure_ad_token_cache'
        verbose_name = 'Azure AD Token Cache'
        verbose_name_plural = 'Azure AD Token Caches'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.token_type}"
    
    @property
    def is_expired(self):
        """Check if token is expired"""
        return timezone.now() > self.expires_at
    
    @property
    def is_expiring_soon(self):
        """Check if token expires within 5 minutes"""
        return timezone.now() > (self.expires_at - timezone.timedelta(minutes=5))


class AzureADUserProfile(models.Model):
    """Extended user profile for Azure AD users"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='azure_profile')
    azure_ad_id = models.CharField(max_length=255, unique=True, help_text="Azure AD user ID")
    job_title = models.CharField(max_length=255, blank=True, help_text="Job title from Azure AD")
    department = models.CharField(max_length=255, blank=True, help_text="Department from Azure AD")
    office_location = models.CharField(max_length=255, blank=True, help_text="Office location from Azure AD")
    company_name = models.CharField(max_length=255, blank=True, help_text="Company name from Azure AD")
    business_phones = models.JSONField(default=list, help_text="Business phone numbers")
    mobile_phone = models.CharField(max_length=50, blank=True, help_text="Mobile phone number")
    preferred_language = models.CharField(max_length=10, blank=True, help_text="Preferred language")
    photo_url = models.URLField(blank=True, help_text="Profile photo URL")
    last_synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'azure_ad_user_profile'
        verbose_name = 'Azure AD User Profile'
        verbose_name_plural = 'Azure AD User Profiles'
    
    def __str__(self):
        return f"{self.user.email} - Azure Profile"


class AzureADAuditLog(models.Model):
    """Audit log for Azure AD operations"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='azure_audit_logs')
    action = models.CharField(
        max_length=100,
        choices=[
            ('login', 'User Login'),
            ('logout', 'User Logout'),
            ('sync', 'User Sync'),
            ('group_sync', 'Group Sync'),
            ('token_refresh', 'Token Refresh'),
            ('profile_update', 'Profile Update'),
            ('error', 'Error'),
        ]
    )
    details = models.JSONField(default=dict, help_text="Action details")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'azure_ad_audit_log'
        verbose_name = 'Azure AD Audit Log'
        verbose_name_plural = 'Azure AD Audit Logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email if self.user else 'Unknown'} - {self.action} - {self.created_at}" 