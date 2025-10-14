from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from api.models import Tenant, User


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """Admin interface for Tenants"""
    
    list_display = [
        'name',
        'subdomain',
        'user_count',
        'subscription_status',
        'is_active',
        'created_at',
        'subdomain_link',
    ]
    
    list_filter = ['is_active', 'subscription_status', 'created_at']
    
    search_fields = ['name', 'subdomain', 'domain']
    
    readonly_fields = ['id', 'created_at', 'updated_at', 'user_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'subdomain', 'domain')
        }),
        ('Subscription', {
            'fields': ('subscription_tier', 'max_users', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_count(self, obj):
        """Show number of users"""
        count = obj.users.count()
        return format_html(
            '<a href="/admin/api/user/?primary_tenant__id__exact={}">{} users</a>',
            obj.id,
            count
        )
    user_count.short_description = 'Users'
    
    def subdomain_link(self, obj):
        """Show clickable subdomain link"""
        url = f'http://{obj.subdomain}.localhost:3000'
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.subdomain)
    subdomain_link.short_description = 'Subdomain Link'
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related().prefetch_related('users')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for Users"""
    
    list_display = [
        'email',
        'username',
        'tenant_name',
        'full_name',
        'is_active',
        'is_staff',
        'date_joined',
    ]
    
    list_filter = [
        'primary_tenant',
        'is_active',
        'is_staff',
        'is_superuser',
        'date_joined',
    ]
    
    search_fields = ['email', 'username', 'first_name', 'last_name', 'primary_tenant__name']
    
    readonly_fields = ['id', 'date_joined', 'last_login']
    
    fieldsets = (
        ('User Information', {
            'fields': ('id', 'username', 'email', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name')
        }),
        ('Tenant Association', {
            'fields': ('primary_tenant',),
            'description': 'Primary tenant this user belongs to'
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important Dates', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
    )
    
    def tenant_name(self, obj):
        """Show tenant name with link"""
        if obj.primary_tenant:
            return format_html(
                '<a href="/admin/api/tenant/{}/change/">{}</a>',
                obj.primary_tenant.id,
                obj.primary_tenant.name
            )
        return '-'
    tenant_name.short_description = 'Tenant'
    tenant_name.admin_order_field = 'primary_tenant__name'
    
    def full_name(self, obj):
        """Show full name"""
        return f"{obj.first_name} {obj.last_name}".strip() or '-'
    full_name.short_description = 'Name'
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related('primary_tenant')