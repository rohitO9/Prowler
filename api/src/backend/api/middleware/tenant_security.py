"""
Enhanced Multi-Tenant Security Middleware

This middleware provides complete tenant isolation and security validation.
It ensures that:
1. Tenants are properly detected from subdomains
2. Users can only access their authorized tenants
3. All requests are validated for tenant membership
4. Cross-tenant data access is prevented
"""

import logging
import re
from django.http import JsonResponse, Http404
from django.core.exceptions import PermissionDenied
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings

from api.models import Tenant, TenantMembership

logger = logging.getLogger(__name__)
User = get_user_model()


class TenantSecurityMiddleware(MiddlewareMixin):
    """
    Enhanced middleware for complete tenant isolation and security.
    
    This middleware:
    1. Detects tenant from subdomain
    2. Validates tenant exists and is active
    3. Ensures user belongs to the tenant (for authenticated requests)
    4. Sets tenant context for all subsequent operations
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process incoming request for tenant detection and validation"""
        try:
            # Extract tenant from subdomain
            tenant = self._extract_tenant_from_request(request)
            
            if not tenant:
                # Handle non-tenant requests (main domain)
                request.tenant = None
                request.tenant_context = None
                return None
            
            # Validate tenant is active
            if not tenant.is_active:
                logger.warning(f"Attempted access to inactive tenant: {tenant.subdomain}")
                return JsonResponse({
                    'error': 'Tenant account is inactive',
                    'code': 'TENANT_INACTIVE'
                }, status=403)
            
            # Set tenant context
            request.tenant = tenant
            request.tenant_context = {
                'tenant_id': str(tenant.id),
                'tenant_name': tenant.name,
                'tenant_subdomain': tenant.subdomain,
                'tenant_domain': tenant.domain,
            }
            
            # For authenticated requests, validate user belongs to tenant
            if request.user.is_authenticated:
                if not self._validate_user_tenant_access(request.user, tenant):
                    logger.warning(
                        f"User {request.user.email} attempted access to unauthorized tenant {tenant.subdomain}"
                    )
                    return JsonResponse({
                        'error': 'Access denied',
                        'code': 'TENANT_ACCESS_DENIED'
                    }, status=403)
                
                # Set user's role in this tenant
                membership = self._get_user_tenant_membership(request.user, tenant)
                if membership:
                    request.tenant_context.update({
                        'user_role': membership.role,
                        'user_permissions': {
                            'can_invite_users': membership.can_invite_users,
                            'can_manage_settings': membership.can_manage_settings,
                            'can_view_analytics': membership.can_view_analytics,
                        }
                    })
            
            logger.debug(f"Tenant context set: {request.tenant_context}")
            return None
            
        except Exception as e:
            logger.error(f"Error in tenant security middleware: {e}")
            return JsonResponse({
                'error': 'Internal server error',
                'code': 'TENANT_MIDDLEWARE_ERROR'
            }, status=500)
    
    def _extract_tenant_from_request(self, request):
        """Extract tenant from request subdomain or domain"""
        host = request.get_host().split(':')[0]  # Remove port
        
        # Handle localhost development
        if host.endswith('.localhost'):
            subdomain = host.replace('.localhost', '')
            if subdomain and subdomain != 'www':
                try:
                    return Tenant.objects.get(
                        subdomain=subdomain,
                        is_active=True
                    )
                except Tenant.DoesNotExist:
                    logger.warning(f"Tenant not found for subdomain: {subdomain}")
                    return None
        
        # Handle custom domains
        try:
            return Tenant.objects.get(
                domain=host,
                is_active=True
            )
        except Tenant.DoesNotExist:
            pass
        
        # Handle www subdomain redirect
        if host.startswith('www.'):
            main_domain = host[4:]
            try:
                return Tenant.objects.get(
                    domain=main_domain,
                    is_active=True
                )
            except Tenant.DoesNotExist:
                pass
        
        return None
    
    def _validate_user_tenant_access(self, user, tenant):
        """Validate that user can access the specified tenant"""
        if not user.is_active:
            return False
        
        if user.is_locked():
            return False
        
        # Check if user is a member of this tenant
        return user.can_access_tenant(tenant.id)
    
    def _get_user_tenant_membership(self, user, tenant):
        """Get user's membership in the tenant"""
        try:
            return TenantMembership.objects.get(
                user=user,
                tenant=tenant,
                is_active=True
            )
        except TenantMembership.DoesNotExist:
            return None


class TenantContextMiddleware(MiddlewareMixin):
    """
    Middleware to inject tenant context into all database queries.
    This ensures all data access is automatically scoped to the current tenant.
    """
    
    def process_request(self, request):
        """Set tenant context for database operations"""
        if hasattr(request, 'tenant') and request.tenant:
            # Set tenant context for RLS (Row Level Security)
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL app.current_tenant_id = %s",
                    [str(request.tenant.id)]
                )
    
    def process_response(self, request, response):
        """Clean up tenant context after request"""
        if hasattr(request, 'tenant') and request.tenant:
            from django.db import connection
            with connection.cursor() as cursor:
                # Reset the tenant context variable
                cursor.execute("SET LOCAL app.current_tenant_id = ''")
        
        return response


class TenantValidationMixin:
    """
    Mixin for views that require tenant validation.
    Provides methods to validate tenant access and permissions.
    """
    
    def validate_tenant_access(self, request):
        """Validate that request has proper tenant context"""
        if not hasattr(request, 'tenant') or not request.tenant:
            raise PermissionDenied("No tenant context found")
        
        if not request.tenant.is_active:
            raise PermissionDenied("Tenant account is inactive")
        
        return True
    
    def validate_user_tenant_membership(self, request):
        """Validate that user belongs to the current tenant"""
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required")
        
        if not hasattr(request, 'tenant') or not request.tenant:
            raise PermissionDenied("No tenant context found")
        
        if not request.user.can_access_tenant(request.tenant.id):
            raise PermissionDenied("User does not belong to this tenant")
        
        return True
    
    def validate_tenant_permission(self, request, permission):
        """Validate that user has specific permission in tenant"""
        self.validate_user_tenant_membership(request)
        
        if not hasattr(request, 'tenant_context') or not request.tenant_context:
            raise PermissionDenied("No tenant context found")
        
        user_permissions = request.tenant_context.get('user_permissions', {})
        if not user_permissions.get(permission, False):
            raise PermissionDenied(f"Permission '{permission}' required")
        
        return True
    
    def get_tenant_queryset(self, queryset):
        """Filter queryset to current tenant's data only"""
        if not hasattr(self.request, 'tenant') or not self.request.tenant:
            return queryset.none()
        
        # Apply tenant filter based on model
        if hasattr(queryset.model, 'tenant'):
            return queryset.filter(tenant=self.request.tenant)
        elif hasattr(queryset.model, 'tenant_id'):
            return queryset.filter(tenant_id=self.request.tenant.id)
        
        return queryset


def require_tenant_access(view_func):
    """
    Decorator to ensure view has tenant context and user access.
    """
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'tenant') or not request.tenant:
            return JsonResponse({
                'error': 'Tenant context required',
                'code': 'TENANT_REQUIRED'
            }, status=400)
        
        if not request.tenant.is_active:
            return JsonResponse({
                'error': 'Tenant account is inactive',
                'code': 'TENANT_INACTIVE'
            }, status=403)
        
        if request.user.is_authenticated and not request.user.can_access_tenant(request.tenant.id):
            return JsonResponse({
                'error': 'Access denied',
                'code': 'TENANT_ACCESS_DENIED'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def require_tenant_permission(permission):
    """
    Decorator to require specific tenant permission.
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'tenant_context') or not request.tenant_context:
                return JsonResponse({
                    'error': 'Tenant context required',
                    'code': 'TENANT_REQUIRED'
                }, status=400)
            
            user_permissions = request.tenant_context.get('user_permissions', {})
            if not user_permissions.get(permission, False):
                return JsonResponse({
                    'error': f'Permission {permission} required',
                    'code': 'PERMISSION_DENIED'
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator
