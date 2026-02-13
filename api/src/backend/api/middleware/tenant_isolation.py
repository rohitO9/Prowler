"""
Enhanced Tenant Isolation Middleware
Ensures every request is properly scoped to tenant context
"""

import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils import timezone
import threading

from api.models import Tenant, TenantMembership
from api.v1.models.azure_sso import AzureADAuditLog

logger = logging.getLogger(__name__)

# Thread-local storage for tenant context
_thread_locals = threading.local()


class TenantIsolationMiddleware(MiddlewareMixin):
    """
    Middleware to enforce tenant isolation on every request
    """
    
    def process_request(self, request):
        """Extract tenant from subdomain and validate access"""
        try:
            # Extract tenant from subdomain
            host = request.META.get('HTTP_HOST', '')
            tenant = self._extract_tenant_from_host(request, host)
            
            if not tenant:
                # Allow public endpoints (e.g. tenant registration, public info)
                if self._is_public_endpoint(request.path):
                    return None
                logger.warning(
                    "Tenant required but none found. path=%r host=%r",
                    request.path,
                    request.META.get('HTTP_HOST', ''),
                )
                return JsonResponse({
                    'error': 'Invalid tenant subdomain',
                    'message': (
                        'Please access via tenant subdomain. '
                        'E.g. tenant.yourdomain.com or (for local dev) company1.localhost:3000'
                    )
                }, status=400)
            
            # Set tenant in thread-local storage
            _thread_locals.tenant = tenant
            request.tenant = tenant
            
            # Validate user belongs to tenant (if authenticated)
            if hasattr(request, 'user') and request.user.is_authenticated:
                if not self._validate_user_tenant_access(request.user, tenant):
                    # Log security violation
                    AzureADAuditLog.log_event(
                        tenant=tenant,
                        user=request.user,
                        event_type='CROSS_TENANT_ACCESS_ATTEMPT',
                        description=f'User {request.user.email} attempted cross-tenant access',
                        details={
                            'user_tenant': request.user.primary_tenant.name if request.user.primary_tenant else None,
                            'requested_tenant': tenant.name,
                            'path': request.path
                        },
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT')
                    )
                    
                    return JsonResponse({
                        'error': 'Access denied',
                        'message': 'You do not have access to this tenant'
                    }, status=403)
            
            # Set tenant context in database session
            self._set_tenant_context(tenant)
            
        except Exception as e:
            logger.error(f"Tenant isolation error: {e}")
            return JsonResponse({
                'error': 'Internal server error'
            }, status=500)
        
        return None
    
    def process_response(self, request, response):
        """Clean up tenant context after request"""
        # Clear thread-local storage
        if hasattr(_thread_locals, 'tenant'):
            delattr(_thread_locals, 'tenant')
        
        # Clear database tenant context
        self._clear_tenant_context()
        
        return response
    
    def _extract_tenant_from_host(self, request, host):
        """Extract tenant from X-Tenant-Subdomain header or hostname (two-level subdomain rule)."""
        try:
            # Priority 1: X-Tenant-Subdomain header (set by Next.js when proxying to backend)
            tenant_header = request.META.get('HTTP_X_TENANT_SUBDOMAIN')
            if tenant_header:
                try:
                    tenant = Tenant.objects.get(
                        subdomain=tenant_header.lower().strip(),
                        is_active=True
                    )
                    logger.debug(f"Found tenant by header: {tenant_header}")
                    return tenant
                except Tenant.DoesNotExist:
                    logger.warning(f"Tenant not found for header: {tenant_header}")

            # Priority 2: Extract from hostname (same two-level rule as frontend)
            hostname = host.split(':')[0].strip().lower()
            parts = hostname.split('.')

            if '.localhost' in hostname:
                # Dev: tenant from first segment (e.g. company1.localhost -> company1)
                if len(parts) > 1 and parts[0] not in ('www', 'api', 'admin', 'app', 'dashboard'):
                    subdomain = parts[0]
                else:
                    subdomain = None
            else:
                # Production: only two-level subdomain is tenant (e.g. tenant1.valnarq.domain.com -> tenant1)
                # Single-level (valnarq.vaniva.shop) is app domain, not tenant
                if len(parts) >= 4 and parts[0] not in ('www', 'api', 'admin', 'app', 'dashboard'):
                    subdomain = parts[0]
                else:
                    subdomain = None

            if not subdomain:
                return None

            try:
                return Tenant.objects.get(subdomain=subdomain, is_active=True)
            except Tenant.DoesNotExist:
                return None

        except Exception as e:
            logger.error(f"Error extracting tenant from host {host}: {e}")
            return None
    
    def _is_public_endpoint(self, path):
        """Check if endpoint is public (no tenant required). Handles path prefix and case from proxies."""
        if not path:
            return False
        path_clean = path.split('?')[0].strip()
        path_lower = path_clean.lower()
        # Explicit public path segments (any occurrence = public)
        public_contains = [
            'tenant/register',
            'tenant/public-info',
            'tenant/validate-invite',
            'tenant/accept-invite',
            'scim/v2/serviceproviderconfig',
            '/api/auth/',
            '/health',
            '/status',
        ]
        if any(segment in path_lower for segment in public_contains):
            return True
        # Exact/prefix style (case-insensitive)
        public_prefixes = [
            '/api/v1/tenant/register',
            '/api/v1/tenant/public-info',
            '/api/v1/tenant/validate-invite',
            '/api/v1/tenant/accept-invite',
            '/health/',
            '/status/',
        ]
        return any(path_lower.startswith(p.lower()) for p in public_prefixes)
    
    def _validate_user_tenant_access(self, user, tenant):
        """Validate user has access to tenant"""
        try:
            # Superusers can access any tenant
            if user.is_superuser:
                return True
            
            # Check if user is member of tenant
            return user.is_member_of_tenant(tenant.id)
            
        except Exception as e:
            logger.error(f"Error validating user tenant access: {e}")
            return False
    
    def _set_tenant_context(self, tenant):
        """Set tenant context in database session"""
        try:
            with connection.cursor() as cursor:
                # Set tenant context for row-level security
                cursor.execute("SET app.current_tenant_id = %s", [str(tenant.id)])
        except Exception as e:
            logger.error(f"Error setting tenant context: {e}")
    
    def _clear_tenant_context(self):
        """Clear tenant context from database session"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("RESET app.current_tenant_id")
        except Exception as e:
            logger.error(f"Error clearing tenant context: {e}")


def get_current_tenant():
    """Get current tenant from thread-local storage"""
    return getattr(_thread_locals, 'tenant', None)


def set_current_tenant(tenant):
    """Set current tenant in thread-local storage"""
    _thread_locals.tenant = tenant


def clear_current_tenant():
    """Clear current tenant from thread-local storage"""
    if hasattr(_thread_locals, 'tenant'):
        delattr(_thread_locals, 'tenant')