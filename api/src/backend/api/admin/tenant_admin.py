"""
Tenant-aware Django admin configuration for multi-tenant security.
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.contrib.admin import SimpleListFilter
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.db import models

from api.models import (
    Tenant, User, TenantMembership, SecurityAuditLog, 
    TenantOAuthConfig, TenantOAuthUser
)
from api.utils.tenant_utils import get_tenant_context

User = get_user_model()


class TenantFilter(SimpleListFilter):
    """Filter for tenant-specific data in admin."""
    title = 'Tenant'
    parameter_name = 'tenant'
    
    def lookups(self, request, model_admin):
        """Get list of tenants for the filter."""
        if request.user.is_superuser:
            # Superusers can see all tenants
            tenants = Tenant.objects.all().order_by('name')
        else:
            # Regular users can only see their tenants
            user_tenants = Tenant.objects.filter(
                members__user=request.user,
                members__is_active=True
            ).distinct().order_by('name')
            tenants = user_tenants
        
        return [(tenant.id, tenant.name) for tenant in tenants]
    
    def queryset(self, request, queryset):
        """Filter queryset by selected tenant."""
        if self.value():
            return queryset.filter(tenant_id=self.value())
        return queryset


class SecurityViolationFilter(SimpleListFilter):
    """Filter for security violations in audit logs."""
    title = 'Security Violation'
    parameter_name = 'security_violation'
    
    def lookups(self, request, model_admin):
        return [
            ('yes', 'Yes'),
            ('no', 'No'),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(is_security_violation=True)
        elif self.value() == 'no':
            return queryset.filter(is_security_violation=False)
        return queryset


class UnresolvedIssuesFilter(SimpleListFilter):
    """Filter for unresolved security issues."""
    title = 'Requires Investigation'
    parameter_name = 'requires_investigation'
    
    def lookups(self, request, model_admin):
        return [
            ('yes', 'Yes'),
            ('no', 'No'),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(requires_investigation=True, resolved=False)
        elif self.value() == 'no':
            return queryset.filter(Q(requires_investigation=False) | Q(resolved=True))
        return queryset


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """Admin interface for Tenant model with security features."""
    
    list_display = [
        'name', 'subdomain', 'domain', 'is_active', 'is_verified',
        'subscription_status', 'user_count', 'max_users', 'last_activity',
        'security_status'
    ]
    list_filter = [
        'is_active', 'is_verified', 'subscription_status', 'created_at'
    ]
    search_fields = ['name', 'subdomain', 'domain', 'contact_email']
    readonly_fields = [
        'id', 'inserted_at', 'updated_at', 'last_activity', 
        'user_count', 'security_summary'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'subdomain', 'domain', 'contact_email', 'contact_phone', 'address')
        }),
        ('Status & Configuration', {
            'fields': ('is_active', 'is_verified', 'subscription_status', 'trial_ends_at')
        }),
        ('Limits & Quotas', {
            'fields': ('max_users', 'max_providers', 'session_timeout_minutes')
        }),
        ('Security Settings', {
            'fields': (
                'allow_registration', 'require_email_verification',
                'max_failed_login_attempts', 'lockout_duration_minutes'
            )
        }),
        ('Branding', {
            'fields': ('logo_url', 'theme_color', 'secondary_color'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('id', 'inserted_at', 'updated_at', 'last_activity', 'created_by'),
            'classes': ('collapse',)
        }),
        ('Security Summary', {
            'fields': ('security_summary',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter tenants based on user permissions."""
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        else:
            # Regular users can only see their tenants
            return qs.filter(members__user=request.user, members__is_active=True).distinct()
    
    def user_count(self, obj):
        """Display user count with link to user list."""
        count = obj.user_count
        if count > 0:
            url = reverse('admin:api_user_changelist') + f'?tenant_id={obj.id}'
            return format_html('<a href="{}">{} users</a>', url, count)
        return f"{count} users"
    user_count.short_description = 'Users'
    
    def security_status(self, obj):
        """Display security status with color coding."""
        if not obj.is_active:
            return format_html('<span style="color: red;">Inactive</span>')
        elif not obj.is_verified:
            return format_html('<span style="color: orange;">Unverified</span>')
        else:
            return format_html('<span style="color: green;">Active</span>')
    security_status.short_description = 'Security Status'
    
    def security_summary(self, obj):
        """Display security summary."""
        summary = obj.get_security_summary()
        return format_html(
            '<div style="font-family: monospace;">'
            'Total Users: {}<br>'
            'Max Users: {}<br>'
            'Active: {}<br>'
            'Verified: {}<br>'
            'Last Activity: {}<br>'
            'Session Timeout: {} min<br>'
            'Max Failed Attempts: {}'
            '</div>',
            summary['total_users'],
            summary['max_users'],
            summary['is_active'],
            summary['is_verified'],
            summary['last_activity'],
            summary['session_timeout'],
            summary['max_failed_attempts']
        )
    security_summary.short_description = 'Security Summary'
    
    def has_add_permission(self, request):
        """Only superusers can add tenants."""
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete tenants."""
        return request.user.is_superuser


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Admin interface for User model with tenant awareness."""
    
    list_display = [
        'email', 'name', 'is_active', 'is_verified', 'primary_tenant',
        'last_login', 'failed_login_attempts', 'is_locked_status',
        'tenant_count'
    ]
    list_filter = [
        TenantFilter, 'is_active', 'is_verified', 'is_superuser',
        'two_factor_enabled', 'date_joined'
    ]
    search_fields = ['email', 'name', 'company_name']
    readonly_fields = [
        'id', 'date_joined', 'last_login', 'last_login_ip',
        'failed_login_attempts', 'locked_until', 'password_changed_at',
        'security_summary'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('email', 'name', 'company_name', 'is_active', 'is_verified')
        }),
        ('Tenant Information', {
            'fields': ('primary_tenant', 'tenant_memberships')
        }),
        ('Security', {
            'fields': (
                'is_superuser', 'two_factor_enabled', 'two_factor_secret',
                'failed_login_attempts', 'locked_until', 'last_login_ip'
            )
        }),
        ('Audit Information', {
            'fields': ('id', 'date_joined', 'last_login', 'password_changed_at'),
            'classes': ('collapse',)
        }),
        ('Security Summary', {
            'fields': ('security_summary',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter users based on tenant permissions."""
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        # Filter by tenant if specified
        tenant_id = request.GET.get('tenant_id')
        if tenant_id:
            return qs.filter(tenant_memberships__tenant_id=tenant_id, tenant_memberships__is_active=True)
        
        # Show users from user's tenants
        user_tenants = Tenant.objects.filter(
            members__user=request.user,
            members__is_active=True
        )
        return qs.filter(tenant_memberships__tenant__in=user_tenants, tenant_memberships__is_active=True).distinct()
    
    def is_locked_status(self, obj):
        """Display lock status."""
        if obj.is_locked():
            return format_html('<span style="color: red;">Locked</span>')
        return format_html('<span style="color: green;">Active</span>')
    is_locked_status.short_description = 'Status'
    
    def tenant_count(self, obj):
        """Display number of tenants user belongs to."""
        count = obj.get_tenant_memberships().count()
        if count > 0:
            url = reverse('admin:api_tenantmembership_changelist') + f'?user_id={obj.id}'
            return format_html('<a href="{}">{} tenants</a>', url, count)
        return f"{count} tenants"
    tenant_count.short_description = 'Tenants'
    
    def security_summary(self, obj):
        """Display security summary."""
        summary = obj.get_security_summary()
        return format_html(
            '<div style="font-family: monospace;">'
            'Active: {}<br>'
            'Verified: {}<br>'
            'Locked: {}<br>'
            'Failed Attempts: {}<br>'
            'Last Login: {}<br>'
            '2FA Enabled: {}<br>'
            'Tenant Count: {}<br>'
            'Primary Tenant: {}'
            '</div>',
            summary['is_active'],
            summary['is_verified'],
            summary['is_locked'],
            summary['failed_attempts'],
            summary['last_login'],
            summary['two_factor_enabled'],
            summary['tenant_count'],
            summary['primary_tenant']
        )
    security_summary.short_description = 'Security Summary'


@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    """Admin interface for TenantMembership model."""
    
    list_display = [
        'user', 'tenant', 'role', 'is_active', 'joined_at',
        'permissions_summary'
    ]
    list_filter = [
        TenantFilter, 'role', 'is_active', 'joined_at'
    ]
    search_fields = ['user__email', 'user__name', 'tenant__name']
    readonly_fields = ['joined_at', 'permissions_summary']
    
    fieldsets = (
        ('Membership Information', {
            'fields': ('user', 'tenant', 'role', 'is_active', 'joined_at')
        }),
        ('Permissions', {
            'fields': ('can_invite_users', 'can_manage_settings', 'can_view_analytics')
        }),
        ('Audit Information', {
            'fields': ('invited_by',),
            'classes': ('collapse',)
        }),
        ('Permissions Summary', {
            'fields': ('permissions_summary',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter memberships based on tenant permissions."""
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        # Show memberships from user's tenants
        user_tenants = Tenant.objects.filter(
            members__user=request.user,
            members__is_active=True
        )
        return qs.filter(tenant__in=user_tenants)
    
    def permissions_summary(self, obj):
        """Display permissions summary."""
        permissions = []
        if obj.can_invite_users:
            permissions.append('Invite Users')
        if obj.can_manage_settings:
            permissions.append('Manage Settings')
        if obj.can_view_analytics:
            permissions.append('View Analytics')
        
        if permissions:
            return format_html('<br>'.join(permissions))
        return 'No special permissions'
    permissions_summary.short_description = 'Permissions'


@admin.register(SecurityAuditLog)
class SecurityAuditLogAdmin(admin.ModelAdmin):
    """Admin interface for SecurityAuditLog model."""
    
    list_display = [
        'timestamp', 'event_type', 'severity', 'user', 'tenant',
        'is_security_violation', 'requires_investigation', 'resolved',
        'message_preview'
    ]
    list_filter = [
        TenantFilter, 'event_type', 'severity', SecurityViolationFilter,
        UnresolvedIssuesFilter, 'resolved', 'timestamp'
    ]
    search_fields = ['message', 'user__email', 'tenant__name', 'ip_address']
    readonly_fields = [
        'id', 'timestamp', 'event_type', 'severity', 'user', 'tenant',
        'ip_address', 'user_agent', 'request_path', 'request_method',
        'message', 'details', 'is_security_violation', 'requires_investigation',
        'resolved', 'resolved_by', 'resolved_at', 'resolution_notes'
    ]
    
    fieldsets = (
        ('Event Information', {
            'fields': ('event_type', 'severity', 'message', 'timestamp')
        }),
        ('Context', {
            'fields': ('user', 'tenant', 'ip_address', 'user_agent')
        }),
        ('Request Details', {
            'fields': ('request_path', 'request_method'),
            'classes': ('collapse',)
        }),
        ('Security Context', {
            'fields': ('is_security_violation', 'requires_investigation')
        }),
        ('Resolution', {
            'fields': ('resolved', 'resolved_by', 'resolved_at', 'resolution_notes')
        }),
        ('Additional Details', {
            'fields': ('details',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter audit logs based on tenant permissions."""
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        # Show logs from user's tenants
        user_tenants = Tenant.objects.filter(
            members__user=request.user,
            members__is_active=True
        )
        return qs.filter(tenant__in=user_tenants)
    
    def message_preview(self, obj):
        """Display message preview."""
        if len(obj.message) > 50:
            return obj.message[:50] + '...'
        return obj.message
    message_preview.short_description = 'Message'
    
    def has_add_permission(self, request):
        """Prevent manual addition of audit logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Only allow changing resolution status."""
        if obj and not obj.resolved:
            return True
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of audit logs."""
        return False


@admin.register(TenantOAuthConfig)
class TenantOAuthConfigAdmin(admin.ModelAdmin):
    """Admin interface for TenantOAuthConfig model."""
    
    list_display = [
        'tenant', 'provider', 'is_active', 'auto_create_users',
        'last_used', 'created_at'
    ]
    list_filter = [
        TenantFilter, 'provider', 'is_active', 'auto_create_users', 'created_at'
    ]
    search_fields = ['tenant__name', 'client_id', 'redirect_uri']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_used']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'provider', 'is_active')
        }),
        ('OAuth Configuration', {
            'fields': ('client_id', 'client_secret', 'redirect_uri', 'provider_tenant_id')
        }),
        ('Settings', {
            'fields': ('scopes', 'allowed_domains', 'auto_create_users', 'require_email_verification')
        }),
        ('Advanced Settings', {
            'fields': ('additional_params',),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('id', 'created_at', 'updated_at', 'last_used', 'created_by'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter OAuth configs based on tenant permissions."""
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        # Show configs from user's tenants
        user_tenants = Tenant.objects.filter(
            members__user=request.user,
            members__is_active=True
        )
        return qs.filter(tenant__in=user_tenants)


@admin.register(TenantOAuthUser)
class TenantOAuthUserAdmin(admin.ModelAdmin):
    """Admin interface for TenantOAuthUser model."""
    
    list_display = [
        'user', 'tenant', 'oauth_config', 'provider_user_id',
        'is_active', 'last_login'
    ]
    list_filter = [
        TenantFilter, 'oauth_config__provider', 'is_active', 'last_login'
    ]
    search_fields = [
        'user__email', 'tenant__name', 'provider_user_id', 'provider_email'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'tenant', 'oauth_config', 'is_active')
        }),
        ('Provider Information', {
            'fields': ('provider_user_id', 'provider_email')
        }),
        ('Token Information', {
            'fields': ('token_expires_at',),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('id', 'created_at', 'updated_at', 'last_login'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter OAuth users based on tenant permissions."""
        qs = super().get_queryset(request)
        
        if request.user.is_superuser:
            return qs
        
        # Show OAuth users from user's tenants
        user_tenants = Tenant.objects.filter(
            members__user=request.user,
            members__is_active=True
        )
        return qs.filter(tenant__in=user_tenants)


# Custom admin site configuration
class TenantAwareAdminSite(admin.AdminSite):
    """Custom admin site with tenant awareness."""
    
    site_header = "Multi-Tenant Security Admin"
    site_title = "Security Admin"
    index_title = "Tenant Security Dashboard"
    
    def has_permission(self, request):
        """Check if user has permission to access admin."""
        return request.user.is_active and (
            request.user.is_staff or request.user.is_superuser
        )
    
    def index(self, request, extra_context=None):
        """Custom index page with tenant security overview."""
        extra_context = extra_context or {}
        
        # Get tenant context
        context = get_tenant_context(request)
        extra_context['tenant_context'] = context
        
        # Get security statistics
        if context['tenant']:
            tenant = context['tenant']
            extra_context['security_stats'] = {
                'total_users': tenant.user_count,
                'max_users': tenant.max_users,
                'recent_violations': SecurityAuditLog.objects.filter(
                    tenant=tenant,
                    is_security_violation=True,
                    timestamp__gte=timezone.now() - timezone.timedelta(days=7)
                ).count(),
                'unresolved_issues': SecurityAuditLog.objects.filter(
                    tenant=tenant,
                    requires_investigation=True,
                    resolved=False
                ).count()
            }
        
        return super().index(request, extra_context)


# Create custom admin site instance
tenant_admin_site = TenantAwareAdminSite(name='tenant_admin')
