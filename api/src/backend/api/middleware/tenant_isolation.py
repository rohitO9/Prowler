import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
import jwt
from django.conf import settings

logger = logging.getLogger(__name__)


class TenantIsolationMiddleware(MiddlewareMixin):
    """
    Validate that authenticated users can only access their tenant
    Must run AFTER authentication middleware
    """
    
    # Paths that don't require tenant validation
    EXEMPT_PATHS = [
        '/admin/',
        '/api/v1/tenant/register',
        '/api/v1/tenant/login',
        '/api/v1/tenant/list',
        '/health',
    ]
    
    def process_request(self, request):
        """Validate tenant access"""
        # Skip exempt paths
        if self._is_exempt_path(request.path):
            return None
        
        # Skip unauthenticated requests (let auth middleware handle)
        if not request.user or not request.user.is_authenticated:
            # Try to authenticate from JWT if present
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                user = self._authenticate_jwt(token, request)
                if user:
                    request.user = user
                else:
                    return None  # Invalid token, let auth middleware handle
            else:
                return None
        
        # Get tenant from request (set by SubdomainMiddleware)
        request_tenant = getattr(request, 'tenant', None)
        
        if not request_tenant:
            # No tenant in request - only allow for exempt paths
            logger.warning(f"No tenant context for: {request.path}")
            return None
        
        # Validate user belongs to this tenant
        if request.user.is_authenticated:
            # Check if user's primary tenant matches request tenant
            if request.user.primary_tenant_id != request_tenant.id:
                # Check if user has membership in this tenant (future feature)
                # has_membership = TenantMembership.objects.filter(
                #     user=request.user,
                #     tenant=request_tenant
                # ).exists()
                
                # For now, strict: user can only access their primary tenant
                logger.error(
                    f"🚨 SECURITY VIOLATION: User {request.user.email} "
                    f"(tenant: {request.user.primary_tenant.name}) "
                    f"attempted to access {request_tenant.name}"
                )
                
                return JsonResponse({
                    'errors': [{
                        'status': '403',
                        'code': 'tenant_access_denied',
                        'title': 'Access Denied',
                        'detail': 'You do not have access to this organization',
                        'meta': {
                            'your_tenant': request.user.primary_tenant.subdomain,
                            'requested_tenant': request_tenant.subdomain,
                        }
                    }]
                }, status=403)
            
            # Also validate JWT token tenant if present
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                if not self._validate_jwt_tenant(token, request_tenant):
                    logger.error(
                        f"🚨 JWT VIOLATION: Token tenant doesn't match request tenant "
                        f"for user {request.user.email}"
                    )
                    return JsonResponse({
                        'errors': [{
                            'status': '403',
                            'code': 'invalid_tenant_token',
                            'title': 'Invalid Token',
                            'detail': 'Your authentication token is not valid for this organization',
                        }]
                    }, status=403)
        
        return None
    
    def _is_exempt_path(self, path):
        """Check if path is exempt from tenant validation"""
        return any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS)
    
    def _authenticate_jwt(self, token, request):
        """Authenticate user from JWT token"""
        try:
            from rest_framework_simplejwt.authentication import JWTAuthentication
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
            return user
        except Exception as e:
            logger.debug(f"JWT authentication failed: {e}")
            return None
    
    def _validate_jwt_tenant(self, token, request_tenant):
        """Validate JWT token contains correct tenant"""
        try:
            # Decode without verification (already validated by auth)
            decoded = jwt.decode(token, options={"verify_signature": False})
            token_tenant_id = decoded.get('tenant_id')
            
            if not token_tenant_id:
                logger.warning("JWT token missing tenant_id claim")
                return False
            
            # Compare tenant IDs
            return str(token_tenant_id) == str(request_tenant.id)
            
        except Exception as e:
            logger.error(f"Error validating JWT tenant: {e}")
            return False