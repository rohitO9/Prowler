"""
Tenant-Aware Azure AD Authentication Views

This module provides secure, tenant-isolated Azure AD authentication endpoints.
All authentication is scoped to specific tenants to prevent cross-tenant access.
"""

import logging
import secrets
from datetime import timedelta
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Tenant, User, TenantMembership
from api.models import TenantOAuthConfig
from api.middleware.tenant_security import (
    require_tenant_access,
    require_tenant_permission,
    TenantValidationMixin
)
from api.services.tenant_azure_auth import TenantAzureAuthService
from api.utils.security import rate_limit_login_attempts, audit_tenant_access

logger = logging.getLogger(__name__)


class TenantAzureInitView(APIView, TenantValidationMixin):
    """
    Initialize Azure AD login for a specific tenant.
    
    This endpoint:
    1. Validates tenant exists and is active
    2. Checks if Azure AD is configured for the tenant
    3. Generates authorization URL with tenant-specific configuration
    4. Returns redirect URL for Azure AD login
    """
    
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Initialize Azure AD login for current tenant"""
        try:
            # Get tenant from request context (set by middleware)
            if not hasattr(request, 'tenant') or not request.tenant:
                return Response({
                    'error': 'No tenant context found',
                    'code': 'NO_TENANT_CONTEXT'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            tenant = request.tenant
            
            # Check if tenant is active
            if not tenant.is_active:
                return Response({
                    'error': 'Tenant account is inactive',
                    'code': 'TENANT_INACTIVE'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Initialize Azure auth service
            azure_service = TenantAzureAuthService(tenant)
            
            # Check if Azure AD is configured
            if not azure_service.is_configured():
                return Response({
                    'error': 'Azure AD not configured for this organization',
                    'code': 'AZURE_NOT_CONFIGURED'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate state parameter for CSRF protection
            state = secrets.token_urlsafe(32)
            
            # Store state in session for validation
            request.session[f'azure_state_{tenant.id}'] = state
            request.session[f'azure_state_time_{tenant.id}'] = timezone.now().isoformat()
            
            # Get optional parameters
            domain_hint = request.GET.get('domain_hint')
            login_hint = request.GET.get('login_hint')
            
            # Generate authorization URL
            auth_url = azure_service.get_authorization_url(
                state=state,
                domain_hint=domain_hint,
                login_hint=login_hint
            )
            
            # Log the initiation
            audit_tenant_access(
                user=None,
                tenant=tenant,
                action='azure_login_initiated',
                details={
                    'ip_address': request.META.get('REMOTE_ADDR'),
                    'user_agent': request.META.get('HTTP_USER_AGENT'),
                    'domain_hint': domain_hint,
                    'login_hint': login_hint
                }
            )
            
            return Response({
                'authorization_url': auth_url,
                'state': state,
                'tenant': {
                    'id': str(tenant.id),
                    'name': tenant.name,
                    'subdomain': tenant.subdomain,
                }
            })
            
        except Exception as e:
            logger.error(f"Azure login initiation error: {e}")
            return Response({
                'error': 'Internal server error',
                'code': 'INIT_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TenantAzureCallbackView(APIView, TenantValidationMixin):
    """
    Handle Azure AD callback and complete authentication.
    
    This endpoint:
    1. Validates the authorization code
    2. Exchanges code for tokens using tenant-specific configuration
    3. Gets user information from Azure AD
    4. Links user to tenant (creates user if auto-creation enabled)
    5. Returns JWT tokens with tenant context
    """
    
    permission_classes = [AllowAny]
    
    @method_decorator(csrf_exempt)
    def post(self, request):
        """Handle Azure AD callback"""
        try:
            # Get tenant from request context
            if not hasattr(request, 'tenant') or not request.tenant:
                return Response({
                    'error': 'No tenant context found',
                    'code': 'NO_TENANT_CONTEXT'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            tenant = request.tenant
            
            # Get authorization code and state
            code = request.data.get('code')
            state = request.data.get('state')
            
            if not code:
                return Response({
                    'error': 'Authorization code is required',
                    'code': 'MISSING_CODE'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate state parameter
            if state:
                stored_state = request.session.get(f'azure_state_{tenant.id}')
                stored_time = request.session.get(f'azure_state_time_{tenant.id}')
                
                if not stored_state or stored_state != state:
                    return Response({
                        'error': 'Invalid state parameter',
                        'code': 'INVALID_STATE'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # Check state age (max 10 minutes)
                if stored_time:
                    state_time = timezone.datetime.fromisoformat(stored_time)
                    if timezone.now() - state_time > timedelta(minutes=10):
                        return Response({
                            'error': 'State parameter expired',
                            'code': 'STATE_EXPIRED'
                        }, status=status.HTTP_400_BAD_REQUEST)
                
                # Clean up state
                del request.session[f'azure_state_{tenant.id}']
                del request.session[f'azure_state_time_{tenant.id}']
            
            # Rate limiting
            ip_address = request.META.get('REMOTE_ADDR')
            if not rate_limit_login_attempts(request, f"azure_{tenant.id}"):
                return Response({
                    'error': 'Too many login attempts. Please try again later.',
                    'code': 'RATE_LIMITED'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Initialize Azure auth service
            azure_service = TenantAzureAuthService(tenant)
            
            # Complete authentication
            success, auth_result = azure_service.authenticate_user(code, ip_address)
            
            if not success:
                # Log failed attempt
                audit_tenant_access(
                    user=None,
                    tenant=tenant,
                    action='azure_login_failed',
                    details={
                        'ip_address': ip_address,
                        'error': auth_result.get('error', 'Unknown error')
                    }
                )
                
                return Response({
                    'error': auth_result.get('error', 'Authentication failed'),
                    'code': 'AUTH_FAILED'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Log successful authentication
            audit_tenant_access(
                user=User.objects.get(id=auth_result['user']['id']),
                tenant=tenant,
                action='azure_login_success',
                details={
                    'ip_address': ip_address,
                    'user_agent': request.META.get('HTTP_USER_AGENT')
                }
            )
            
            return Response(auth_result)
            
        except Exception as e:
            logger.error(f"Azure callback error: {e}")
            return Response({
                'error': 'Internal server error',
                'code': 'CALLBACK_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TenantAzureRefreshView(APIView, TenantValidationMixin):
    """
    Refresh Azure AD access token.
    
    This endpoint validates the refresh token and issues a new access token
    with tenant context.
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Refresh access token"""
        try:
            # Get tenant from request context
            if not hasattr(request, 'tenant') or not request.tenant:
                return Response({
                    'error': 'No tenant context found',
                    'code': 'NO_TENANT_CONTEXT'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            tenant = request.tenant
            refresh_token = request.data.get('refresh_token')
            
            if not refresh_token:
                return Response({
                    'error': 'Refresh token is required',
                    'code': 'MISSING_REFRESH_TOKEN'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Initialize Azure auth service
            azure_service = TenantAzureAuthService(tenant)
            
            # Refresh token
            success, token_data = azure_service.refresh_access_token(refresh_token)
            
            if not success:
                return Response({
                    'error': token_data.get('error', 'Token refresh failed'),
                    'code': 'REFRESH_FAILED'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            return Response(token_data)
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return Response({
                'error': 'Internal server error',
                'code': 'REFRESH_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TenantAzureConfigView(APIView, TenantValidationMixin):
    """
    Manage Azure AD configuration for a tenant.
    
    Only tenant administrators can configure Azure AD settings.
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get Azure AD configuration for current tenant"""
        try:
            # Validate tenant access
            if not hasattr(request, 'tenant') or not request.tenant:
                return Response({
                    'error': 'No tenant context found',
                    'code': 'NO_TENANT_CONTEXT'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            tenant = request.tenant
            
            # Check if user has permission to view config
            if not request.user.can_access_tenant(tenant.id):
                return Response({
                    'error': 'Access denied',
                    'code': 'TENANT_ACCESS_DENIED'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check if user has admin permissions
            try:
                membership = TenantMembership.objects.get(
                    user=request.user,
                    tenant=tenant,
                    is_active=True
                )
                if not membership.can_manage_settings:
                    return Response({
                        'error': 'Permission denied',
                        'code': 'PERMISSION_DENIED'
                    }, status=status.HTTP_403_FORBIDDEN)
            except TenantMembership.DoesNotExist:
                return Response({
                    'error': 'User not found in tenant',
                    'code': 'MEMBERSHIP_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get Azure configuration
            azure_service = TenantAzureAuthService(tenant)
            config = azure_service.get_tenant_config()
            
            return Response(config)
            
        except Exception as e:
            logger.error(f"Get Azure config error: {e}")
            return Response({
                'error': 'Internal server error',
                'code': 'CONFIG_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create or update Azure AD configuration"""
        try:
            # Validate tenant access
            if not hasattr(request, 'tenant') or not request.tenant:
                return Response({
                    'error': 'No tenant context found',
                    'code': 'NO_TENANT_CONTEXT'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            tenant = request.tenant
            
            # Check if user has permission to manage config
            if not request.user.can_access_tenant(tenant.id):
                return Response({
                    'error': 'Access denied',
                    'code': 'TENANT_ACCESS_DENIED'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check admin permissions
            try:
                membership = TenantMembership.objects.get(
                    user=request.user,
                    tenant=tenant,
                    is_active=True
                )
                if not membership.can_manage_settings:
                    return Response({
                        'error': 'Permission denied',
                        'code': 'PERMISSION_DENIED'
                    }, status=status.HTTP_403_FORBIDDEN)
            except TenantMembership.DoesNotExist:
                return Response({
                    'error': 'User not found in tenant',
                    'code': 'MEMBERSHIP_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get configuration data
            client_id = request.data.get('client_id')
            client_secret = request.data.get('client_secret')
            azure_tenant_id = request.data.get('azure_tenant_id')
            scopes = request.data.get('scopes', ['openid', 'profile', 'email', 'User.Read'])
            allowed_domains = request.data.get('allowed_domains', [])
            auto_create_users = request.data.get('auto_create_users', True)
            require_email_verification = request.data.get('require_email_verification', False)
            
            if not client_id or not client_secret:
                return Response({
                    'error': 'Client ID and Client Secret are required',
                    'code': 'MISSING_CREDENTIALS'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Generate redirect URI
            redirect_uri = f"https://{tenant.subdomain}.yourdomain.com/api/auth/azure/callback"
            
            # Create or update OAuth config
            oauth_config, created = TenantOAuthConfig.objects.get_or_create(
                tenant=tenant,
                provider='azure',
                defaults={
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'redirect_uri': redirect_uri,
                    'provider_tenant_id': azure_tenant_id,
                    'scopes': scopes,
                    'allowed_domains': allowed_domains,
                    'auto_create_users': auto_create_users,
                    'require_email_verification': require_email_verification,
                    'created_by': request.user,
                }
            )
            
            if not created:
                # Update existing config
                oauth_config.client_id = client_id
                oauth_config.client_secret = client_secret
                oauth_config.redirect_uri = redirect_uri
                oauth_config.provider_tenant_id = azure_tenant_id
                oauth_config.scopes = scopes
                oauth_config.allowed_domains = allowed_domains
                oauth_config.auto_create_users = auto_create_users
                oauth_config.require_email_verification = require_email_verification
                oauth_config.save()
            
            # Log configuration change
            audit_tenant_access(
                user=request.user,
                tenant=tenant,
                action='azure_config_updated',
                details={
                    'client_id': client_id,
                    'azure_tenant_id': azure_tenant_id,
                    'auto_create_users': auto_create_users
                }
            )
            
            return Response({
                'message': 'Azure AD configuration updated successfully',
                'config': {
                    'client_id': client_id,
                    'azure_tenant_id': azure_tenant_id,
                    'redirect_uri': redirect_uri,
                    'scopes': scopes,
                    'allowed_domains': allowed_domains,
                    'auto_create_users': auto_create_users,
                    'require_email_verification': require_email_verification,
                }
            })
            
        except Exception as e:
            logger.error(f"Update Azure config error: {e}")
            return Response({
                'error': 'Internal server error',
                'code': 'CONFIG_UPDATE_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request):
        """Delete Azure AD configuration"""
        try:
            # Validate tenant access
            if not hasattr(request, 'tenant') or not request.tenant:
                return Response({
                    'error': 'No tenant context found',
                    'code': 'NO_TENANT_CONTEXT'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            tenant = request.tenant
            
            # Check permissions
            if not request.user.can_access_tenant(tenant.id):
                return Response({
                    'error': 'Access denied',
                    'code': 'TENANT_ACCESS_DENIED'
                }, status=status.HTTP_403_FORBIDDEN)
            
            try:
                membership = TenantMembership.objects.get(
                    user=request.user,
                    tenant=tenant,
                    is_active=True
                )
                if not membership.can_manage_settings:
                    return Response({
                        'error': 'Permission denied',
                        'code': 'PERMISSION_DENIED'
                    }, status=status.HTTP_403_FORBIDDEN)
            except TenantMembership.DoesNotExist:
                return Response({
                    'error': 'User not found in tenant',
                    'code': 'MEMBERSHIP_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Delete Azure configuration
            try:
                oauth_config = TenantOAuthConfig.objects.get(
                    tenant=tenant,
                    provider='azure'
                )
                oauth_config.delete()
                
                # Log deletion
                audit_tenant_access(
                    user=request.user,
                    tenant=tenant,
                    action='azure_config_deleted',
                    details={}
                )
                
                return Response({
                    'message': 'Azure AD configuration deleted successfully'
                })
                
            except TenantOAuthConfig.DoesNotExist:
                return Response({
                    'error': 'Azure AD configuration not found',
                    'code': 'CONFIG_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            logger.error(f"Delete Azure config error: {e}")
            return Response({
                'error': 'Internal server error',
                'code': 'CONFIG_DELETE_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_azure_login_url(request):
    """
    Get Azure AD login URL for current tenant.
    This is a convenience endpoint for frontend applications.
    """
    try:
        # Get tenant from request context
        if not hasattr(request, 'tenant') or not request.tenant:
            return Response({
                'error': 'No tenant context found',
                'code': 'NO_TENANT_CONTEXT'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        tenant = request.tenant
        
        # Initialize Azure auth service
        azure_service = TenantAzureAuthService(tenant)
        
        if not azure_service.is_configured():
            return Response({
                'error': 'Azure AD not configured for this organization',
                'code': 'AZURE_NOT_CONFIGURED'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate authorization URL
        state = secrets.token_urlsafe(32)
        request.session[f'azure_state_{tenant.id}'] = state
        request.session[f'azure_state_time_{tenant.id}'] = timezone.now().isoformat()
        
        auth_url = azure_service.get_authorization_url(state=state)
        
        return Response({
            'login_url': auth_url,
            'state': state
        })
        
    except Exception as e:
        logger.error(f"Get Azure login URL error: {e}")
        return Response({
            'error': 'Internal server error',
            'code': 'LOGIN_URL_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
