"""
Tenant-aware middleware for automatic request scoping and security enforcement.
This middleware ensures all requests are properly scoped to the correct tenant.
"""

import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.db import connection
from django.contrib.auth import get_user_model
from django.core.cache import cache
import re
import json

from api.models import Tenant, SecurityAuditLog
from api.utils.tenant_utils import get_tenant_from_request, get_user_from_token

logger = logging.getLogger(__name__)
User = get_user_model()


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware that automatically scopes all requests to the correct tenant.
    
    This middleware:
    1. Extracts tenant information from subdomain or headers
    2. Validates tenant access for authenticated users
    3. Sets tenant context for the request
    4. Enforces tenant isolation at the database level
    5. Logs security violations
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """
        Process the request to determine and validate tenant context.
        """
        try:
            # Skip tenant processing for certain paths
            if self._should_skip_tenant_processing(request):
                return None
            
            # Extract tenant information
            tenant = self._get_tenant_from_request(request)
            if not tenant:
                return self._handle_no_tenant(request)
            
            # Validate tenant is active
            if not tenant.is_active:
                return self._handle_inactive_tenant(request, tenant)
            
            # Set tenant context
            request.tenant = tenant
            request.tenant_id = str(tenant.id)
            
            # For authenticated requests, validate user access
            if hasattr(request, 'user') and request.user.is_authenticated:
                if not self._validate_user_tenant_access(request, tenant):
                    return self._handle_unauthorized_tenant_access(request, tenant)
            
            # Set database tenant context for RLS
            self._set_database_tenant_context(tenant)
            
            # Log tenant access
            self._log_tenant_access(request, tenant)
            
        except Exception as e:
            logger.error(f"Tenant middleware error: {e}", exc_info=True)
            return self._handle_tenant_error(request, str(e))
        
        return None
    
    def process_response(self, request, response):
        """
        Process the response to clean up tenant context.
        """
        # Clear database tenant context
        if hasattr(request, 'tenant_id'):
            self._clear_database_tenant_context()
        
        return response
    
    def _should_skip_tenant_processing(self, request):
        """Determine if tenant processing should be skipped for this request."""
        skip_paths = [
            '/admin/',
            '/api/auth/',
            '/api/health/',
            '/api/status/',
            '/static/',
            '/media/',
            '/favicon.ico',
        ]
        
        path = request.path
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    def _get_tenant_from_request(self, request):
        """Extract tenant information from the request."""
        # Method 1: Extract from subdomain
        tenant = self._get_tenant_from_subdomain(request)
        if tenant:
            return tenant
        
        # Method 2: Extract from headers
        tenant = self._get_tenant_from_headers(request)
        if tenant:
            return tenant
        
        # Method 3: Extract from JWT token
        tenant = self._get_tenant_from_token(request)
        if tenant:
            return tenant
        
        return None
    
    def _get_tenant_from_subdomain(self, request):
        """Extract tenant from subdomain."""
        host = request.get_host()
        
        # Handle localhost development
        if 'localhost' in host or '127.0.0.1' in host:
            subdomain = host.split('.')[0]
            if subdomain in ['localhost', '127', '0', '0', '1']:
                return None
        else:
            # Handle production domains
            parts = host.split('.')
            if len(parts) >= 3:
                subdomain = parts[0]
            else:
                return None
        
        try:
            return Tenant.objects.get(subdomain=subdomain, is_active=True)
        except Tenant.DoesNotExist:
            return None
    
    def _get_tenant_from_headers(self, request):
        """Extract tenant from custom headers."""
        tenant_id = request.headers.get('X-Tenant-ID')
        tenant_subdomain = request.headers.get('X-Tenant-Subdomain')
        
        if tenant_id:
            try:
                return Tenant.objects.get(id=tenant_id, is_active=True)
            except Tenant.DoesNotExist:
                return None
        
        if tenant_subdomain:
            try:
                return Tenant.objects.get(subdomain=tenant_subdomain, is_active=True)
            except Tenant.DoesNotExist:
                return None
        
        return None
    
    def _get_tenant_from_token(self, request):
        """Extract tenant from JWT token."""
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        try:
            token = auth_header.split(' ')[1]
            user = get_user_from_token(token)
            if user and user.primary_tenant:
                return user.primary_tenant
        except Exception as e:
            logger.warning(f"Error extracting tenant from token: {e}")
        
        return None
    
    def _validate_user_tenant_access(self, request, tenant):
        """Validate that the user can access the specified tenant."""
        user = request.user
        
        # Superusers can access any tenant
        if user.is_superuser:
            return True
        
        # Check if user is locked
        if user.is_locked():
            return False
        
        # Check if user is a member of this tenant
        return user.can_access_tenant(tenant.id)
    
    def _set_database_tenant_context(self, tenant):
        """Set the database tenant context for Row Level Security."""
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL app.current_tenant_id = %s", [str(tenant.id)])
    
    def _clear_database_tenant_context(self):
        """Clear the database tenant context."""
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL app.current_tenant_id = NULL")
    
    def _log_tenant_access(self, request, tenant):
        """Log tenant access for audit purposes."""
        if hasattr(request, 'user') and request.user.is_authenticated:
            SecurityAuditLog.log_event(
                event_type='tenant_switched',
                message=f"User {request.user.email} accessed tenant {tenant.name}",
                user=request.user,
                tenant=tenant,
                severity='low',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                request_path=request.path,
                request_method=request.method,
                is_security_violation=False,
                requires_investigation=False
            )
    
    def _get_client_ip(self, request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _handle_no_tenant(self, request):
        """Handle requests where no tenant can be determined."""
        # For API requests, return 400 Bad Request
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Tenant not specified',
                'message': 'Please specify tenant via subdomain or X-Tenant-ID header'
            }, status=400)
        
        # For other requests, allow through (might be public pages)
        return None
    
    def _handle_inactive_tenant(self, request, tenant):
        """Handle requests to inactive tenants."""
        SecurityAuditLog.log_event(
            event_type='tenant_access_denied',
            message=f"Attempted access to inactive tenant {tenant.name}",
            tenant=tenant,
            severity='high',
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            request_path=request.path,
            is_security_violation=True,
            requires_investigation=True
        )
        
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Tenant inactive',
                'message': 'This tenant account is currently inactive'
            }, status=403)
        
        return None
    
    def _handle_unauthorized_tenant_access(self, request, tenant):
        """Handle unauthorized tenant access attempts."""
        SecurityAuditLog.log_tenant_access_denied(
            user=request.user,
            tenant=tenant,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            request_path=request.path,
            details={
                'user_id': str(request.user.id),
                'tenant_id': str(tenant.id),
                'timestamp': timezone.now().isoformat()
            }
        )
        
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Access denied',
                'message': 'You do not have access to this tenant'
            }, status=403)
        
        return None
    
    def _handle_tenant_error(self, request, error_message):
        """Handle tenant processing errors."""
        logger.error(f"Tenant middleware error: {error_message}")
        
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Tenant processing error',
                'message': 'Unable to process tenant context'
            }, status=500)
        
        return None


class TenantSecurityMiddleware(MiddlewareMixin):
    """
    Additional security middleware for tenant-specific security enforcement.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process request for additional security checks."""
        if not hasattr(request, 'tenant') or not request.tenant:
            return None
        
        # Rate limiting per tenant
        if self._is_rate_limited(request):
            return self._handle_rate_limit(request)
        
        # Check for suspicious activity
        if self._is_suspicious_activity(request):
            self._log_suspicious_activity(request)
        
        return None
    
    def _is_rate_limited(self, request):
        """Check if the request is rate limited."""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return False
        
        # Simple rate limiting based on user + tenant
        cache_key = f"rate_limit:{request.tenant.id}:{request.user.id}"
        request_count = cache.get(cache_key, 0)
        
        # Allow 100 requests per minute per user per tenant
        if request_count >= 100:
            return True
        
        cache.set(cache_key, request_count + 1, 60)  # 60 seconds
        return False
    
    def _handle_rate_limit(self, request):
        """Handle rate limited requests."""
        SecurityAuditLog.log_event(
            event_type='api_rate_limit',
            message=f"Rate limit exceeded for user {request.user.email} in tenant {request.tenant.name}",
            user=request.user,
            tenant=request.tenant,
            severity='medium',
            ip_address=self._get_client_ip(request),
            is_security_violation=True,
            requires_investigation=False
        )
        
        return JsonResponse({
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please try again later.'
        }, status=429)
    
    def _is_suspicious_activity(self, request):
        """Check for suspicious activity patterns."""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return False
        
        # Check for unusual request patterns
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ip_address = self._get_client_ip(request)
        
        # Check for bot-like user agents
        bot_patterns = ['bot', 'crawler', 'spider', 'scraper']
        if any(pattern in user_agent.lower() for pattern in bot_patterns):
            return True
        
        # Check for rapid successive requests from same IP
        cache_key = f"suspicious_activity:{ip_address}"
        request_count = cache.get(cache_key, 0)
        
        if request_count >= 50:  # 50 requests in 1 minute
            return True
        
        cache.set(cache_key, request_count + 1, 60)
        return False
    
    def _log_suspicious_activity(self, request):
        """Log suspicious activity."""
        SecurityAuditLog.log_event(
            event_type='suspicious_activity',
            message=f"Suspicious activity detected from user {request.user.email} in tenant {request.tenant.name}",
            user=request.user,
            tenant=request.tenant,
            severity='high',
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            request_path=request.path,
            is_security_violation=True,
            requires_investigation=True
        )
    
    def _get_client_ip(self, request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
