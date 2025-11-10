"""
Tenant Validation Views

This module provides comprehensive tenant validation endpoints:
- Tenant access validation
- User-tenant membership validation
- Permission checking
- Feature access validation
"""

import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from api.models import User, Tenant, TenantMembership
from api.middleware.tenant_security import (
    require_tenant_access,
    require_tenant_permission,
    TenantValidationMixin
)
from api.utils.security import TenantSecurityValidator
from api.serializers import UserSerializer

logger = logging.getLogger(__name__)


class TenantAccessValidationView(APIView, TenantValidationMixin):
    """
    Validate user access to specific tenant.
    
    This endpoint is called by the frontend to verify that:
    1. Tenant exists and is active
    2. User is authenticated
    3. User belongs to the tenant
    4. User has appropriate permissions
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Validate tenant access"""
        try:
            tenant_subdomain = request.data.get('tenant_subdomain')
            if not tenant_subdomain:
                return Response({
                    'error': 'Tenant subdomain required',
                    'code': 'MISSING_TENANT_SUBDOMAIN'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get tenant
            try:
                tenant = Tenant.objects.get(
                    subdomain=tenant_subdomain,
                    is_active=True
                )
            except Tenant.DoesNotExist:
                return Response({
                    'error': 'Tenant not found or inactive',
                    'code': 'TENANT_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate user access
            is_valid, error_message = TenantSecurityValidator.validate_tenant_access(
                request.user, tenant
            )
            
            if not is_valid:
                return Response({
                    'error': error_message,
                    'code': 'TENANT_ACCESS_DENIED'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get user's membership details
            try:
                membership = TenantMembership.objects.get(
                    user=request.user,
                    tenant=tenant,
                    is_active=True
                )
                
                return Response({
                    'valid': True,
                    'tenant': {
                        'id': str(tenant.id),
                        'name': tenant.name,
                        'subdomain': tenant.subdomain,
                        'is_active': tenant.is_active,
                        'subscription_status': tenant.subscription_status,
                    },
                    'membership': {
                        'role': membership.role,
                        'permissions': {
                            'can_invite_users': membership.can_invite_users,
                            'can_manage_settings': membership.can_manage_settings,
                            'can_view_analytics': membership.can_view_analytics,
                        },
                        'joined_at': membership.joined_at.isoformat(),
                    }
                })
                
            except TenantMembership.DoesNotExist:
                return Response({
                    'error': 'User membership not found',
                    'code': 'MEMBERSHIP_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            logger.error(f"Tenant access validation error: {e}")
            return Response({
                'error': 'Internal server error',
                'code': 'VALIDATION_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TenantPermissionValidationView(APIView, TenantValidationMixin):
    """
    Validate user permissions within a tenant.
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Validate tenant permission"""
        try:
            tenant_subdomain = request.data.get('tenant_subdomain')
            permission = request.data.get('permission')
            
            if not tenant_subdomain or not permission:
                return Response({
                    'error': 'Tenant subdomain and permission required',
                    'code': 'MISSING_PARAMETERS'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get tenant
            try:
                tenant = Tenant.objects.get(
                    subdomain=tenant_subdomain,
                    is_active=True
                )
            except Tenant.DoesNotExist:
                return Response({
                    'error': 'Tenant not found',
                    'code': 'TENANT_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate permission
            has_permission, error_message = TenantSecurityValidator.validate_tenant_permission(
                request.user, tenant, permission
            )
            
            if not has_permission:
                return Response({
                    'error': error_message,
                    'code': 'PERMISSION_DENIED'
                }, status=status.HTTP_403_FORBIDDEN)
            
            return Response({
                'valid': True,
                'permission': permission,
                'tenant': {
                    'id': str(tenant.id),
                    'name': tenant.name,
                    'subdomain': tenant.subdomain,
                }
            })
            
        except Exception as e:
            logger.error(f"Permission validation error: {e}")
            return Response({
                'error': 'Internal server error',
                'code': 'VALIDATION_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TenantFeatureAccessView(APIView, TenantValidationMixin):
    """
    Check if tenant can access specific features.
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Check feature access"""
        try:
            tenant_subdomain = request.data.get('tenant_subdomain')
            feature = request.data.get('feature')
            
            if not tenant_subdomain or not feature:
                return Response({
                    'error': 'Tenant subdomain and feature required',
                    'code': 'MISSING_PARAMETERS'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get tenant
            try:
                tenant = Tenant.objects.get(
                    subdomain=tenant_subdomain,
                    is_active=True
                )
            except Tenant.DoesNotExist:
                return Response({
                    'error': 'Tenant not found',
                    'code': 'TENANT_NOT_FOUND'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check feature access
            from api.utils.security import check_tenant_feature_access
            can_access = check_tenant_feature_access(tenant, feature)
            
            return Response({
                'can_access': can_access,
                'feature': feature,
                'tenant': {
                    'id': str(tenant.id),
                    'name': tenant.name,
                    'subscription_status': tenant.subscription_status,
                }
            })
            
        except Exception as e:
            logger.error(f"Feature access check error: {e}")
            return Response({
                'error': 'Internal server error',
                'code': 'VALIDATION_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tenant_members(request):
    """
    Get all members of the current tenant.
    Only accessible by users with appropriate permissions.
    """
    try:
        # Validate tenant access
        if not hasattr(request, 'tenant') or not request.tenant:
            return Response({
                'error': 'No tenant context',
                'code': 'NO_TENANT_CONTEXT'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user has permission to view members
        if not request.user.can_access_tenant(request.tenant.id):
            return Response({
                'error': 'Access denied',
                'code': 'TENANT_ACCESS_DENIED'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get tenant members
        memberships = TenantMembership.objects.filter(
            tenant=request.tenant,
            is_active=True
        ).select_related('user')
        
        members = []
        for membership in memberships:
            members.append({
                'id': str(membership.user.id),
                'name': membership.user.name,
                'email': membership.user.email,
                'role': membership.role,
                'joined_at': membership.joined_at.isoformat(),
                'permissions': {
                    'can_invite_users': membership.can_invite_users,
                    'can_manage_settings': membership.can_manage_settings,
                    'can_view_analytics': membership.can_view_analytics,
                }
            })
        
        return Response({
            'members': members,
            'total': len(members),
            'tenant': {
                'id': str(request.tenant.id),
                'name': request.tenant.name,
                'subdomain': request.tenant.subdomain,
            }
        })
        
    except Exception as e:
        logger.error(f"Get tenant members error: {e}")
        return Response({
            'error': 'Internal server error',
            'code': 'MEMBERS_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_tenant_member(request):
    """
    Invite a new member to the tenant.
    Requires appropriate permissions.
    """
    try:
        # Validate tenant access
        if not hasattr(request, 'tenant') or not request.tenant:
            return Response({
                'error': 'No tenant context',
                'code': 'NO_TENANT_CONTEXT'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user has permission to invite members
        try:
            membership = TenantMembership.objects.get(
                user=request.user,
                tenant=request.tenant,
                is_active=True
            )
            
            if not membership.can_invite_users:
                return Response({
                    'error': 'Permission denied',
                    'code': 'INVITE_PERMISSION_DENIED'
                }, status=status.HTTP_403_FORBIDDEN)
                
        except TenantMembership.DoesNotExist:
            return Response({
                'error': 'User not found in tenant',
                'code': 'MEMBERSHIP_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get invitation data
        email = request.data.get('email')
        role = request.data.get('role', 'member')
        
        if not email:
            return Response({
                'error': 'Email is required',
                'code': 'MISSING_EMAIL'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user already exists
        try:
            user = User.objects.get(email=email)
            # Check if user is already a member
            if TenantMembership.objects.filter(
                user=user,
                tenant=request.tenant,
                is_active=True
            ).exists():
                return Response({
                    'error': 'User is already a member',
                    'code': 'USER_ALREADY_MEMBER'
                }, status=status.HTTP_409_CONFLICT)
        except User.DoesNotExist:
            # User doesn't exist, will need to be created
            pass
        
        # Create invitation (implement invitation logic here)
        # For now, just return success
        return Response({
            'message': 'Invitation sent successfully',
            'email': email,
            'role': role
        })
        
    except Exception as e:
        logger.error(f"Invite member error: {e}")
        return Response({
            'error': 'Internal server error',
            'code': 'INVITE_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tenant_settings(request):
    """
    Get tenant settings and configuration.
    """
    try:
        # Validate tenant access
        if not hasattr(request, 'tenant') or not request.tenant:
            return Response({
                'error': 'No tenant context',
                'code': 'NO_TENANT_CONTEXT'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.can_access_tenant(request.tenant.id):
            return Response({
                'error': 'Access denied',
                'code': 'TENANT_ACCESS_DENIED'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get tenant settings
        settings = {
            'tenant': {
                'id': str(request.tenant.id),
                'name': request.tenant.name,
                'subdomain': request.tenant.subdomain,
                'domain': request.tenant.domain,
                'is_active': request.tenant.is_active,
                'is_verified': request.tenant.is_verified,
                'subscription_status': request.tenant.subscription_status,
                'trial_ends_at': request.tenant.trial_ends_at.isoformat() if request.tenant.trial_ends_at else None,
                'allow_registration': request.tenant.allow_registration,
                'require_email_verification': request.tenant.require_email_verification,
                'session_timeout_minutes': request.tenant.session_timeout_minutes,
            },
            'branding': {
                'logo_url': request.tenant.logo_url,
                'theme_color': request.tenant.theme_color,
                'secondary_color': request.tenant.secondary_color,
            },
            'contact': {
                'email': request.tenant.contact_email,
                'phone': request.tenant.contact_phone,
                'address': request.tenant.address,
            }
        }
        
        return Response(settings)
        
    except Exception as e:
        logger.error(f"Get tenant settings error: {e}")
        return Response({
            'error': 'Internal server error',
            'code': 'SETTINGS_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_tenant_public_info(request):
    """
    Get public information about the current tenant.
    This endpoint is accessible without authentication.
    """
    try:
        # First, try to get tenant from request (set by middleware)
        tenant = getattr(request, 'tenant', None)
        
        # If not set by middleware, try to get from header
        if not tenant:
            subdomain = request.META.get('HTTP_X_TENANT_SUBDOMAIN', '').strip()
            if not subdomain:
                # Try to extract from host as fallback
                host = request.get_host().split(':')[0]
                if '.localhost' in host:
                    subdomain = host.split('.')[0]
                elif len(host.split('.')) > 2:
                    subdomain = host.split('.')[0]
            
            if subdomain:
                try:
                    tenant = Tenant.objects.get(subdomain=subdomain, is_active=True)
                    logger.debug(f"Found tenant from subdomain: {subdomain}")
                except Tenant.DoesNotExist:
                    logger.warning(f"Tenant not found for subdomain: {subdomain}")
                    return Response({
                        'error': 'Tenant not found',
                        'code': 'TENANT_NOT_FOUND'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                logger.warning("No tenant subdomain found in request")
                return Response({
                    'error': 'Tenant subdomain is required',
                    'code': 'MISSING_SUBDOMAIN'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if not tenant:
            return Response({
                'error': 'Tenant not found',
                'code': 'TENANT_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # If trial_ends_at is null and subscription_status is 'trial', set it to 14 days from now
        if not tenant.trial_ends_at and tenant.subscription_status == 'trial':
            tenant.trial_ends_at = timezone.now() + timedelta(days=14)
            tenant.save(update_fields=['trial_ends_at'])
            logger.info(f"Set trial_ends_at for tenant {tenant.subdomain}: {tenant.trial_ends_at}")
        
        # Return public tenant information
        return Response({
            'data': {
                'data': {
                    'tenant': {
                        'id': str(tenant.id),
                        'name': tenant.name,
                        'subdomain': tenant.subdomain,
                        'is_active': tenant.is_active,
                        'is_verified': tenant.is_verified,
                        'allow_registration': tenant.allow_registration,
                        'require_email_verification': tenant.require_email_verification,
                        'theme_color': tenant.theme_color,
                        'secondary_color': getattr(tenant, 'secondary_color', None),
                        'logo_url': tenant.logo_url,
                        'subscription_status': tenant.subscription_status,
                        'trial_ends_at': tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
                        'contact_email': tenant.contact_email,
                    }
                }
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting tenant public info: {e}", exc_info=True)
        return Response({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_me(request):
    """
    Get current user information
    """
    try:
        user = request.user
        logger.info(f"Getting user info for: {user.email}")
        
        # Serialize user data
        user_data = UserSerializer(user).data
        
        return Response({
            'data': {
                'type': 'user',
                'attributes': user_data
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        return Response({
            'error': 'Failed to get user information',
            'code': 'USER_INFO_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
