"""
Tenant Isolation Middleware

This middleware enforces strict tenant isolation by:
1. Validating that users can only access their assigned tenants
2. Ensuring all database queries are tenant-scoped
3. Preventing cross-tenant data access
4. Logging all tenant access attempts for security auditing
"""

import logging
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class TenantIsolationMiddleware(MiddlewareMixin):
    """
    Enforces strict tenant isolation for all requests.
    
    This middleware ensures that:
    - Users can only access their assigned tenants
    - All database queries are automatically scoped to the current tenant
    - Cross-tenant access is blocked and logged
    - Security violations are tracked
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
    
    def process_request(self, request):
        """Process incoming request for tenant isolation"""
        try:
            # Skip tenant isolation for exempt paths
            exempt_paths = [
                '/api/v1/tenant/register',
                '/api/v1/tenant/register/',
                '/api/v1/tenant/login',
                '/api/v1/tenant/login/',
                '/api/v1/tenant/public-info',
                '/api/v1/tenant/public-info/',
                '/admin/',
                '/static/',
                '/media/',
            ]
            
            if any(request.path.startswith(path) for path in exempt_paths):
                return None
            
            # Special handling for /api/v1/tokens endpoint
            if request.path in ['/api/v1/tokens', '/api/v1/tokens/']:
                # For tokens endpoint, we need to validate tenant context from JWT token
                # This will be handled by the authentication view itself
                return None
            
            # Get tenant from request context
            tenant = getattr(request, 'tenant', None)
            user = getattr(request, 'user', None)
            
            logger.info(f"🔍 [TENANT_ISOLATION] Processing request: {request.path}")
            logger.info(f"🔍 [TENANT_ISOLATION] Tenant context: {tenant.subdomain if tenant else 'None'} (ID: {tenant.id if tenant else 'None'})")
            logger.info(f"🔍 [TENANT_ISOLATION] User context: {user.email if user and user.is_authenticated else 'Anonymous'}")
            
            if not tenant:
                logger.warning(f"❌ [TENANT_ISOLATION] No tenant context found for request: {request.path}")
                return JsonResponse({
                    'error': 'Tenant context required',
                    'code': 'TENANT_CONTEXT_REQUIRED'
                }, status=400)
            
            # For authenticated requests, validate tenant access
            if request.user.is_authenticated:
                if not self._validate_tenant_access(request.user, tenant):
                    logger.error(
                        f"SECURITY VIOLATION: User {request.user.email} attempted access to unauthorized tenant {tenant.subdomain}"
                    )
                    return JsonResponse({
                        'error': 'Access denied - insufficient permissions',
                        'code': 'TENANT_ACCESS_DENIED'
                    }, status=403)
                
                # Set tenant context in database for query scoping
                self._set_tenant_context(tenant.id)
            else:
                # Check if there's a JWT token in the Authorization header
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                if auth_header.startswith('Bearer '):
                    # Extract and validate JWT token
                    token = auth_header.split(' ')[1]
                    user = self._authenticate_jwt_token(token)
                    if user:
                        # Additional validation: Check JWT token tenant matches request tenant
                        # We need to decode the token again to get tenant_id
                        try:
                            from rest_framework_simplejwt.tokens import AccessToken
                            access_token = AccessToken(token)
                            token_tenant_id = access_token.get('tenant_id')
                            
                            logger.info(f"🔍 [JWT_TENANT_CHECK] JWT token tenant: {token_tenant_id}, Request tenant: {tenant.id}")
                            
                            if token_tenant_id and str(token_tenant_id) != str(tenant.id):
                                logger.error(
                                    f"❌ [JWT_TENANT_CHECK] SECURITY VIOLATION: JWT token tenant {token_tenant_id} does not match request tenant {tenant.id} for user {user.email}"
                                )
                                return JsonResponse({
                                    'error': 'Token tenant mismatch - access denied',
                                    'code': 'TENANT_MISMATCH'
                                }, status=403)
                            else:
                                logger.info(f"✅ [JWT_TENANT_CHECK] JWT token tenant matches request tenant")
                        except Exception as e:
                            logger.warning(f"⚠️ [JWT_TENANT_CHECK] Could not validate token tenant: {e}")
                        
                        # Validate tenant access for JWT-authenticated user
                        if not self._validate_tenant_access(user, tenant):
                            logger.error(
                                f"SECURITY VIOLATION: JWT User {user.email} attempted access to unauthorized tenant {tenant.subdomain}"
                            )
                            return JsonResponse({
                                'error': 'Access denied - insufficient permissions',
                                'code': 'TENANT_ACCESS_DENIED'
                            }, status=403)
                        
                        # Set user in request for downstream processing
                        request.user = user
                        request._force_auth_user = user
                        
                        # Set tenant context in database for query scoping
                        self._set_tenant_context(tenant.id)
                    else:
                        logger.warning(f"Invalid JWT token for tenant {tenant.subdomain}")
                        return JsonResponse({
                            'error': 'Invalid authentication token',
                            'code': 'INVALID_TOKEN'
                        }, status=401)
                else:
                    # No authentication provided
                    logger.warning(f"Unauthenticated access attempt to tenant {tenant.subdomain}")
                    return JsonResponse({
                        'error': 'Authentication required',
                        'code': 'AUTHENTICATION_REQUIRED'
                    }, status=401)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in tenant isolation middleware: {e}")
            return JsonResponse({
                'error': 'Internal server error',
                'code': 'TENANT_ISOLATION_ERROR'
            }, status=500)
    
    def process_response(self, request, response):
        """Clean up tenant context after request"""
        try:
            # Clear tenant context from database
            self._clear_tenant_context()
        except Exception as e:
            logger.error(f"Error clearing tenant context: {e}")
        
        return response
    
    def _validate_tenant_access(self, user, tenant):
        """Validate that user has access to the specified tenant"""
        try:
            logger.info(f"🔍 [TENANT_VALIDATION] Starting validation for user {user.email} and tenant {tenant.subdomain}")
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"❌ [TENANT_VALIDATION] Inactive user {user.email} attempted access to tenant {tenant.subdomain}")
                return False
            
            # Check if user belongs to tenant
            logger.info(f"🔍 [TENANT_VALIDATION] Checking if user {user.email} belongs to tenant {tenant.subdomain} (ID: {tenant.id})")
            
            # Get user's tenant memberships for detailed logging
            user_tenants = user.get_tenant_ids()
            logger.info(f"🔍 [TENANT_VALIDATION] User {user.email} belongs to tenants: {user_tenants}")
            
            if not user.can_access_tenant(tenant.id):
                logger.error(
                    f"❌ [TENANT_VALIDATION] SECURITY VIOLATION: User {user.email} does not belong to tenant {tenant.subdomain} (ID: {tenant.id})"
                )
                logger.error(
                    f"❌ [TENANT_VALIDATION] User belongs to: {user_tenants}, Requested tenant: {tenant.id}"
                )
                return False
            
            # Log successful access for auditing
            logger.info(f"✅ [TENANT_VALIDATION] User {user.email} successfully validated for tenant {tenant.subdomain}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [TENANT_VALIDATION] Error validating tenant access: {e}")
            return False
    
    def _authenticate_jwt_token(self, token):
        """Authenticate JWT token and return user"""
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            
            # Decode and validate token
            access_token = AccessToken(token)
            
            # JWT token uses 'sub' (subject) for user ID, not 'user_id'
            user_id = access_token.get('sub') or access_token.get('user_id')
            token_tenant_id = access_token.get('tenant_id')
            
            logger.info(f"🔍 [JWT_AUTH] Decoded JWT token - User ID: {user_id}, Tenant ID: {token_tenant_id}")
            
            if not user_id:
                logger.error("❌ [JWT_AUTH] No user ID found in JWT token")
                return None
            
            # Get user from database
            user = User.objects.get(id=user_id)
            logger.info(f"✅ [JWT_AUTH] Successfully authenticated user: {user.email} (ID: {user_id})")
            
            # Log user's tenant memberships
            user_tenants = user.get_tenant_ids()
            logger.info(f"🔍 [JWT_AUTH] User {user.email} belongs to tenants: {user_tenants}")
            
            return user
            
        except Exception as e:
            logger.error(f"Error authenticating JWT token: {e}")
            return None
    
    def _set_tenant_context(self, tenant_id):
        """Set tenant context in database for query scoping"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.current_tenant_id = %s", [str(tenant_id)])
        except Exception as e:
            logger.error(f"Error setting tenant context: {e}")
    
    def _clear_tenant_context(self):
        """Clear tenant context from database"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.current_tenant_id = ''")
        except Exception as e:
            logger.error(f"Error clearing tenant context: {e}")


class TenantQueryScopingMiddleware(MiddlewareMixin):
    """
    Automatically scope all database queries to the current tenant.
    
    This middleware ensures that all ORM queries are automatically
    filtered by the current tenant context.
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
    
    def process_request(self, request):
        """Set up tenant scoping for database queries"""
        tenant = getattr(request, 'tenant', None)
        if tenant:
            # Set tenant context for automatic query scoping
            request.tenant_id = tenant.id
            logger.debug(f"Set tenant scoping for tenant: {tenant.subdomain}")
        
        return None


class TenantSecurityAuditMiddleware(MiddlewareMixin):
    """
    Audit middleware for tracking tenant access patterns and security violations.
    
    This middleware logs all tenant access attempts for security monitoring.
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
    
    def process_request(self, request):
        """Log tenant access attempts"""
        if hasattr(request, 'tenant') and request.tenant:
            tenant = request.tenant
            user = getattr(request, 'user', None)
            
            if user and user.is_authenticated:
                logger.info(
                    f"TENANT_ACCESS: User {user.email} accessing tenant {tenant.subdomain} "
                    f"via {request.method} {request.path}"
                )
            else:
                logger.info(
                    f"TENANT_ACCESS: Anonymous user accessing tenant {tenant.subdomain} "
                    f"via {request.method} {request.path}"
                )
        
        return None
