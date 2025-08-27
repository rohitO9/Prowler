"""
Azure AD Admin Interface
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from api.v1.models.azure_ad import (
    AzureADGroupMapping,
    AzureADTenantMapping,
    AzureADUserSync,
    AzureADTokenCache,
    AzureADUserProfile,
    AzureADAuditLog,
)


@admin.register(AzureADGroupMapping)
class AzureADGroupMappingAdmin(admin.ModelAdmin):
    """Admin interface for Azure AD Group Mappings"""
    
    list_display = [
        'azure_group_name', 'azure_group_id', 'role', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'role', 'created_at']
    search_fields = ['azure_group_name', 'azure_group_id', 'role__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['azure_group_name']
    
    fieldsets = (
        ('Azure AD Group', {
            'fields': ('azure_group_id', 'azure_group_name')
        }),
        ('Local Role', {
            'fields': ('role', 'is_active')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('role')


@admin.register(AzureADTenantMapping)
class AzureADTenantMappingAdmin(admin.ModelAdmin):
    """Admin interface for Azure AD Tenant Mappings"""
    
    list_display = [
        'azure_group_name', 'azure_group_id', 'tenant', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'tenant', 'created_at']
    search_fields = ['azure_group_name', 'azure_group_id', 'tenant__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['azure_group_name']
    
    fieldsets = (
        ('Azure AD Group', {
            'fields': ('azure_group_id', 'azure_group_name')
        }),
        ('Local Tenant', {
            'fields': ('tenant', 'is_active')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tenant')


@admin.register(AzureADUserSync)
class AzureADUserSyncAdmin(admin.ModelAdmin):
    """Admin interface for Azure AD User Sync Records"""
    
    list_display = [
        'user_email', 'azure_user_id', 'sync_type', 'status', 'last_synced_at'
    ]
    list_filter = ['sync_type', 'status', 'last_synced_at', 'created_at']
    search_fields = ['user__email', 'azure_user_id', 'error_message']
    readonly_fields = [
        'id', 'user', 'azure_user_id', 'sync_type', 'status', 
        'error_message', 'sync_data', 'last_synced_at', 'created_at'
    ]
    ordering = ['-last_synced_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'azure_user_id')
        }),
        ('Sync Details', {
            'fields': ('sync_type', 'status', 'error_message')
        }),
        ('Sync Data', {
            'fields': ('sync_data',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('last_synced_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email if obj.user else 'Unknown'
    user_email.short_description = 'User Email'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(AzureADTokenCache)
class AzureADTokenCacheAdmin(admin.ModelAdmin):
    """Admin interface for Azure AD Token Cache"""
    
    list_display = [
        'user_email', 'token_type', 'expires_at', 'is_expired', 'created_at'
    ]
    list_filter = ['token_type', 'created_at', 'expires_at']
    search_fields = ['user__email', 'scope']
    readonly_fields = [
        'id', 'user', 'access_token', 'refresh_token', 'token_type',
        'expires_at', 'scope', 'created_at', 'updated_at'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Token Information', {
            'fields': ('token_type', 'expires_at', 'scope')
        }),
        ('Token Data', {
            'fields': ('access_token', 'refresh_token'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email if obj.user else 'Unknown'
    user_email.short_description = 'User Email'
    
    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Expired'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(AzureADUserProfile)
class AzureADUserProfileAdmin(admin.ModelAdmin):
    """Admin interface for Azure AD User Profiles"""
    
    list_display = [
        'user_email', 'azure_ad_id', 'job_title', 'department', 'last_synced_at'
    ]
    list_filter = ['department', 'last_synced_at', 'created_at']
    search_fields = [
        'user__email', 'azure_ad_id', 'job_title', 'department', 'company_name'
    ]
    readonly_fields = [
        'id', 'user', 'azure_ad_id', 'last_synced_at', 'created_at'
    ]
    ordering = ['user__email']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'azure_ad_id')
        }),
        ('Job Information', {
            'fields': ('job_title', 'department', 'office_location', 'company_name')
        }),
        ('Contact Information', {
            'fields': ('business_phones', 'mobile_phone', 'preferred_language')
        }),
        ('Profile', {
            'fields': ('photo_url',)
        }),
        ('Timestamps', {
            'fields': ('last_synced_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email if obj.user else 'Unknown'
    user_email.short_description = 'User Email'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(AzureADAuditLog)
class AzureADAuditLogAdmin(admin.ModelAdmin):
    """Admin interface for Azure AD Audit Logs"""
    
    list_display = [
        'user_email', 'action', 'success', 'ip_address', 'created_at'
    ]
    list_filter = ['action', 'success', 'created_at']
    search_fields = ['user__email', 'action', 'error_message', 'ip_address']
    readonly_fields = [
        'id', 'user', 'action', 'details', 'ip_address', 'user_agent',
        'success', 'error_message', 'created_at'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'ip_address', 'user_agent')
        }),
        ('Action Details', {
            'fields': ('action', 'success', 'error_message')
        }),
        ('Details', {
            'fields': ('details',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email if obj.user else 'Unknown'
    user_email.short_description = 'User Email'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def has_add_permission(self, request):
        return False  # Audit logs should not be manually created
    
    def has_change_permission(self, request, obj=None):
        return False  # Audit logs should not be modified 