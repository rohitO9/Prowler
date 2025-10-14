"""
Comprehensive API security system for multi-tenant applications.
"""

import logging
from functools import wraps
from typing import Dict, Any, Optional, List, Callable
from django.http import JsonResponse, HttpRequest
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.core.cache import cache
from django.db import connection
from django.contrib.auth import get_user_model

from api.models import Tenant, SecurityAuditLog
from api.auth.tenant_jwt import get_tenant_jwt_auth
from api.utils.tenant_utils import validate_tenant_access, get_tenant_context

logger = logging.getLogger(__name__)
User = get_user_model()


class TenantSecurityError(Exception):
    """Custom exception for tenant security violations."""
    pass


class APISecurityManager:
    """
    Comprehensive API security manager for multi-tenant applications.
    """
    
    def __init__(self):
        self.jwt_auth = get_tenant_jwt_auth()
        self.rate_limit_cache_prefix = "api_rate_limit"
        self.security_cache_prefix = "api_security"
    
    def authenticate_request(self, request: HttpRequest) -> Dict[str, Any]:
        """
        Authenticate and validate API request with tenant context.
        
        Args:
            request: Django request object
            
        Returns:
            Dictionary containing authentication context
        """
        context = {
            'authenticated': False,
            'user': None,
            'tenant': None,
            'permissions': {},
            'security_level': 'low'
        }
        
        try:
            # Extract JWT token
            token = self._extract_token(request)
            if not token:
                return context
            
            # Validate token
            claims = self.jwt_auth.validate_access_token(token)
            if not claims:
                return context
            
            # Get user and tenant
            user = self._get_user_from_claims(claims)
            tenant = self._get_tenant_from_claims(claims)
            
            if not user or not tenant:
                return context
            
            # Validate tenant access
            if not validate_tenant_access(user, tenant):
                self._log_security_violation(
                    request, user, tenant, 
                    'Invalid tenant access attempt',
                    'high'
                )
                return context
            
            # Get user permissions
            permissions = self.jwt_auth.get_user_permissions_from_token(token)
            
            # Set context
            context.update({
                'authenticated': True,
                'user': user,
                'tenant': tenant,
                'permissions': permissions,
                'security_level': self._determine_security_level(user, tenant)
            })
            
            # Log successful authentication
            self._log_api_access(request, user, tenant, 'success')
            
        except Exception as e:
            logger.error(f"Error authenticating request: {e}")
            self._log_security_violation(
                request, None, None,
                f'Authentication error: {str(e)}',
                'medium'
            )
        
        return context
    
    def check_rate_limit(self, request: HttpRequest, user: User, tenant: Tenant) -> bool:
        """
        Check if request is within rate limits.
        
        Args:
            request: Django request object
            user: User object
            tenant: Tenant object
            
        Returns:
            True if within limits, False otherwise
        """
        # Get client IP
        ip_address = self._get_client_ip(request)
        
        # Create rate limit keys
        user_key = f"{self.rate_limit_cache_prefix}:user:{user.id}:{tenant.id}"
        ip_key = f"{self.rate_limit_cache_prefix}:ip:{ip_address}:{tenant.id}"
        
        # Check user rate limit (100 requests per minute)
        user_count = cache.get(user_key, 0)
        if user_count >= 100:
            self._log_rate_limit_exceeded(request, user, tenant, 'user_limit')
            return False
        
        # Check IP rate limit (200 requests per minute)
        ip_count = cache.get(ip_key, 0)
        if ip_count >= 200:
            self._log_rate_limit_exceeded(request, user, tenant, 'ip_limit')
            return False
        
        # Increment counters
        cache.set(user_key, user_count + 1, 60)
        cache.set(ip_key, ip_count + 1, 60)
        
        return True
    
    def check_permissions(self, request: HttpRequest, required_permission: str, 
                         user: User, tenant: Tenant) -> bool:
        """
        Check if user has required permission in tenant.
        
        Args:
            request: Django request object
            required_permission: Required permission
            user: User object
            tenant: Tenant object
            
        Returns:
            True if permission granted, False otherwise
        """
        try:
            # Superusers have all permissions
            if user.is_superuser:
                return True
            
            # Check user membership in tenant
            membership = user.tenant_memberships.filter(
                tenant=tenant,
                is_active=True
            ).first()
            
            if not membership:
                self._log_permission_denied(request, user, tenant, required_permission)
                return False
            
            # Check specific permission
            has_permission = membership.has_permission(required_permission)
            
            if not has_permission:
                self._log_permission_denied(request, user, tenant, required_permission)
            
            return has_permission
            
        except Exception as e:
            logger.error(f"Error checking permissions: {e}")
            return False
    
    def validate_tenant_isolation(self, request: HttpRequest, resource_tenant_id: str,
                                 user: User, tenant: Tenant) -> bool:
        """
        Validate that user can access resources from specific tenant.
        
        Args:
            request: Django request object
            resource_tenant_id: Tenant ID of the resource
            user: User object
            tenant: Tenant object
            
        Returns:
            True if access allowed, False otherwise
        """
        # Superusers can access any tenant
        if user.is_superuser:
            return True
        
        # Check if resource belongs to user's tenant
        if str(tenant.id) != resource_tenant_id:
            self._log_data_access_violation(
                request, user, tenant, resource_tenant_id
            )
            return False
        
        return True
    
    def _extract_token(self, request: HttpRequest) -> Optional[str]:
        """Extract JWT token from request."""
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
        return None
    
    def _get_user_from_claims(self, claims: Dict[str, Any]) -> Optional[User]:
        """Get user from JWT claims."""
        user_id = claims.get('user_id')
        if not user_id:
            return None
        
        try:
            return User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return None
    
    def _get_tenant_from_claims(self, claims: Dict[str, Any]) -> Optional[Tenant]:
        """Get tenant from JWT claims."""
        tenant_id = claims.get('tenant_id')
        if not tenant_id:
            return None
        
        try:
            return Tenant.objects.get(id=tenant_id, is_active=True)
        except Tenant.DoesNotExist:
            return None
    
    def _determine_security_level(self, user: User, tenant: Tenant) -> str:
        """Determine security level for user-tenant combination."""
        if user.is_superuser:
            return 'critical'
        elif user.is_verified and tenant.is_verified:
            return 'high'
        elif user.is_verified or tenant.is_verified:
            return 'medium'
        else:
            return 'low'
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR', '')
    
    def _log_api_access(self, request: HttpRequest, user: User, tenant: Tenant, status: str):
        """Log API access."""
        SecurityAuditLog.log_event(
            event_type='api_access',
            message=f'API access: {request.method} {request.path} - {status}',
            user=user,
            tenant=tenant,
            severity='low',
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            request_path=request.path,
            request_method=request.method,
            details={'status': status},
            is_security_violation=False,
            requires_investigation=False
        )
    
    def _log_security_violation(self, request: HttpRequest, user: Optional[User], 
                               tenant: Optional[Tenant], message: str, severity: str):
        """Log security violation."""
        SecurityAuditLog.log_event(
            event_type='security_violation',
            message=message,
            user=user,
            tenant=tenant,
            severity=severity,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            request_path=request.path,
            request_method=request.method,
            is_security_violation=True,
            requires_investigation=True
        )
    
    def _log_rate_limit_exceeded(self, request: HttpRequest, user: User, 
                                tenant: Tenant, limit_type: str):
        """Log rate limit exceeded."""
        SecurityAuditLog.log_event(
            event_type='api_rate_limit',
            message=f'Rate limit exceeded: {limit_type}',
            user=user,
            tenant=tenant,
            severity='medium',
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            request_path=request.path,
            request_method=request.method,
            details={'limit_type': limit_type},
            is_security_violation=True,
            requires_investigation=False
        )
    
    def _log_permission_denied(self, request: HttpRequest, user: User, 
                             tenant: Tenant, permission: str):
        """Log permission denied."""
        SecurityAuditLog.log_event(
            event_type='permission_denied',
            message=f'Permission denied: {permission}',
            user=user,
            tenant=tenant,
            severity='high',
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            request_path=request.path,
            request_method=request.method,
            details={'required_permission': permission},
            is_security_violation=True,
            requires_investigation=True
        )
    
    def _log_data_access_violation(self, request: HttpRequest, user: User, 
                                  tenant: Tenant, resource_tenant_id: str):
        """Log data access violation."""
        SecurityAuditLog.log_data_access_violation(
            user=user,
            tenant=tenant,
            resource_type='cross_tenant_data',
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            request_path=request.path,
            details={
                'user_tenant_id': str(tenant.id),
                'resource_tenant_id': resource_tenant_id,
                'violation_type': 'cross_tenant_access'
            }
        )


# Global instance
api_security_manager = APISecurityManager()


def require_authentication(view_func: Callable) -> Callable:
    """
    Decorator to require authentication for API endpoints.
    """
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        # Authenticate request
        auth_context = api_security_manager.authenticate_request(request)
        
        if not auth_context['authenticated']:
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'Valid JWT token required'
            }, status=401)
        
        # Add auth context to request
        request.auth_context = auth_context
        request.user = auth_context['user']
        request.tenant = auth_context['tenant']
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def require_tenant_access(view_func: Callable) -> Callable:
    """
    Decorator to require tenant access for API endpoints.
    """
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not hasattr(request, 'auth_context'):
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'Valid JWT token required'
            }, status=401)
        
        auth_context = request.auth_context
        
        if not auth_context['authenticated']:
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'Valid JWT token required'
            }, status=401)
        
        # Check rate limits
        if not api_security_manager.check_rate_limit(
            request, auth_context['user'], auth_context['tenant']
        ):
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.'
            }, status=429)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def require_permission(permission: str):
    """
    Decorator to require specific permission for API endpoints.
    
    Args:
        permission: Required permission
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if not hasattr(request, 'auth_context'):
                return JsonResponse({
                    'error': 'Authentication required',
                    'message': 'Valid JWT token required'
                }, status=401)
            
            auth_context = request.auth_context
            
            if not auth_context['authenticated']:
                return JsonResponse({
                    'error': 'Authentication required',
                    'message': 'Valid JWT token required'
                }, status=401)
            
            # Check permission
            if not api_security_manager.check_permissions(
                request, permission, auth_context['user'], auth_context['tenant']
            ):
                return JsonResponse({
                    'error': 'Permission denied',
                    'message': f'Required permission: {permission}'
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_tenant_isolation(view_func: Callable) -> Callable:
    """
    Decorator to enforce tenant isolation for API endpoints.
    """
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not hasattr(request, 'auth_context'):
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'Valid JWT token required'
            }, status=401)
        
        auth_context = request.auth_context
        
        if not auth_context['authenticated']:
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'Valid JWT token required'
            }, status=401)
        
        # Set database tenant context for RLS
        with connection.cursor() as cursor:
            cursor.execute(
                "SET LOCAL app.current_tenant_id = %s", 
                [str(auth_context['tenant'].id)]
            )
        
        try:
            return view_func(request, *args, **kwargs)
        finally:
            # Clear database tenant context
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.current_tenant_id = NULL")
    
    return wrapper


def secure_api_endpoint(permissions: List[str] = None, require_tenant_isolation: bool = True):
    """
    Comprehensive decorator for securing API endpoints.
    
    Args:
        permissions: List of required permissions
        require_tenant_isolation: Whether to enforce tenant isolation
    """
    def decorator(view_func: Callable) -> Callable:
        # Apply authentication
        view_func = require_authentication(view_func)
        
        # Apply tenant access
        view_func = require_tenant_access(view_func)
        
        # Apply permissions
        if permissions:
            for permission in permissions:
                view_func = require_permission(permission)(view_func)
        
        # Apply tenant isolation
        if require_tenant_isolation:
            view_func = require_tenant_isolation(view_func)
        
        return view_func
    
    return decorator


class TenantAwareViewMixin:
    """
    Mixin for class-based views to provide tenant awareness.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to add tenant context."""
        # Authenticate request
        auth_context = api_security_manager.authenticate_request(request)
        
        if not auth_context['authenticated']:
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'Valid JWT token required'
            }, status=401)
        
        # Add auth context to request
        request.auth_context = auth_context
        request.user = auth_context['user']
        request.tenant = auth_context['tenant']
        
        # Check rate limits
        if not api_security_manager.check_rate_limit(
            request, auth_context['user'], auth_context['tenant']
        ):
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.'
            }, status=429)
        
        # Set database tenant context for RLS
        with connection.cursor() as cursor:
            cursor.execute(
                "SET LOCAL app.current_tenant_id = %s", 
                [str(auth_context['tenant'].id)]
            )
        
        try:
            return super().dispatch(request, *args, **kwargs)
        finally:
            # Clear database tenant context
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.current_tenant_id = NULL")
    
    def check_permissions(self, request, required_permissions: List[str]):
        """Check if user has required permissions."""
        auth_context = request.auth_context
        
        for permission in required_permissions:
            if not api_security_manager.check_permissions(
                request, permission, auth_context['user'], auth_context['tenant']
            ):
                return False
        
        return True
    
    def get_tenant_queryset(self, queryset, tenant_id: str):
        """Filter queryset by tenant."""
        return api_security_manager.validate_tenant_isolation(
            self.request, tenant_id, 
            self.request.auth_context['user'], 
            self.request.auth_context['tenant']
        )


def get_api_security_manager() -> APISecurityManager:
    """Get the global API security manager instance."""
    return api_security_manager
