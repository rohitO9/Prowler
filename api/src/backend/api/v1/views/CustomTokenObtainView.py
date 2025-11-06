import logging
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from rest_framework.exceptions import ValidationError
from api.models import Tenant

logger = logging.getLogger(__name__)

class CustomTokenObtainView(TokenObtainPairView):
    """
    Custom token obtain view with tenant isolation security.
    
    This view validates that users can only login to their assigned tenants.
    """
    
    def post(self, request, *args, **kwargs):
        """Override post method to add tenant validation"""
        logger.info(f"🔍 [CUSTOM_TOKEN_VIEW] Starting token request for tenant: {getattr(request, 'tenant', None)}")
        try:
            # Get tenant from request context (set by middleware) or from request data
            tenant = getattr(request, 'tenant', None)
            
            # If no tenant from middleware, try to get from request data
            if not tenant:
                logger.info("No tenant from middleware, checking request data")
                data = request.data.get('data', {})
                attributes = data.get('attributes', {})
                tenant_name = attributes.get('tenant_name')
                
                if tenant_name:
                    try:
                        tenant = Tenant.objects.get(
                            subdomain=tenant_name.lower(),
                            is_active=True
                        )
                        logger.info(f"Found tenant from request data: {tenant.subdomain}")
                    except Tenant.DoesNotExist:
                        logger.warning(f"Tenant not found for subdomain: {tenant_name}")
                        return JsonResponse({
                            'error': f'Organization "{tenant_name}" not found',
                            'code': 'TENANT_NOT_FOUND'
                        }, status=404)
            
            if not tenant:
                logger.warning(f"No tenant context found for login request")
                return JsonResponse({
                    'error': 'Tenant context required for login',
                    'code': 'TENANT_CONTEXT_REQUIRED'
                }, status=400)
            
            # Check if user is SSO-only (from invitation) - prevent password login
            email = request.data.get('email') or (request.data.get('data', {}).get('attributes', {}).get('email'))
            if email:
                from api.models import User
                try:
                    user = User.objects.get(email=email)
                    # Check if user is SSO-only (invited users)
                    if hasattr(user, 'is_sso_user') and user.is_sso_user:
                        logger.warning(f"SSO-only user {email} attempted password login - blocked")
                        return JsonResponse({
                            'error': 'This account can only be accessed via Azure AD SSO. Please use SSO login.',
                            'code': 'SSO_ONLY_USER'
                        }, status=403)
                except User.DoesNotExist:
                    pass  # User doesn't exist yet, let parent handle it
            
            # Call parent method to get tokens
            response = super().post(request, *args, **kwargs)
            
            if response.status_code == 200:
                # Extract user from the response or request
                user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
                
                if user:
                    # Validate user belongs to the tenant
                    if not user.can_access_tenant(tenant.id):
                        logger.error(
                            f"SECURITY VIOLATION: User {user.email} attempted login to unauthorized tenant {tenant.subdomain}"
                        )
                        return JsonResponse({
                            'error': 'Access denied - user does not belong to this tenant',
                            'code': 'TENANT_ACCESS_DENIED'
                        }, status=403)
                    
                    logger.info(f"User {user.email} successfully logged in to tenant {tenant.subdomain}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ [CUSTOM_TOKEN_VIEW] Error in CustomTokenObtainView: {e}")
            return JsonResponse({
                'error': 'Internal server error',
                'code': 'LOGIN_ERROR'
            }, status=500)
