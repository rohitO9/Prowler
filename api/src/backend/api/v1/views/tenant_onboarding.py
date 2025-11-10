"""
Tenant Onboarding Views - API endpoints for the new invite-based onboarding flow.

This module provides API endpoints for:
- Tenant creation and SSO setup
- User invitation management
- Azure AD OAuth integration
- Domain verification
- Admin dashboard functionality
"""

import logging
from typing import Dict, Any
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
import json

from api.models import Tenant, User, Invitation, TenantOAuthConfig
from api.v1.models.azure_sso import AzureSSOConfig, AzureADAuditLog
from api.services.tenant_service import TenantService
from api.services.invite_service import InviteService
from api.services.auth_service import AuthService
from api.services.domain_service import DomainService
from api.services.user_service import UserService
from api.services.audit_log_service import AuditLogService
from api.services.azure_scim_service import AzureSCIMService

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_tenant(request):
    """
    Create a new tenant with initial configuration.
    
    POST /api/v1/tenant/create/
    """
    try:
        data = request.data
        tenant_service = TenantService()
        
        # Create tenant
        tenant = tenant_service.create_tenant(
            tenant_data=data,
            created_by_user=request.user
        )
        
        return Response({
            'success': True,
            'message': f"Tenant '{tenant.name}' created successfully",
            'tenant': {
                'id': str(tenant.id),
                'name': tenant.name,
                'subdomain': tenant.subdomain,
                'domain': tenant.domain,
                'contact_email': tenant.contact_email,
                'is_active': tenant.is_active,
                'is_verified': tenant.is_verified,
                'subscription_status': tenant.subscription_status,
                'trial_ends_at': tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None
            }
        }, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"❌ Failed to create tenant: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def setup_azure_sso(request):
    """
    Set up Azure AD SSO for a tenant.
    
    POST /api/v1/tenant/setup-azure-sso/
    """
    try:
        data = request.data
        tenant = request.user.primary_tenant
        
        # Validate required fields
        azure_tenant_id = data.get('azure_tenant_id')
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        
        if not all([azure_tenant_id, client_id, client_secret]):
            return Response({
                'error': 'Missing required fields: azure_tenant_id, client_id, client_secret'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Test Azure AD connection
        authority = f"https://login.microsoftonline.com/{azure_tenant_id}"
        token_endpoint = f"{authority}/oauth2/v2.0/token"
        
        # Test connection by getting a token
        import requests
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'https://graph.microsoft.com/.default',
            'grant_type': 'client_credentials'
        }
        
        response = requests.post(token_endpoint, data=token_data, timeout=10)
        if response.status_code != 200:
            return Response({
                'error': 'Invalid Azure AD credentials'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create or update Azure SSO config
        sso_config, created = AzureSSOConfig.objects.get_or_create(
            tenant=tenant,
            defaults={
                'azure_tenant_id': azure_tenant_id,
                'client_id': client_id,
                'client_secret': client_secret,
                'authority': authority,
                'authorization_endpoint': f"{authority}/oauth2/v2.0/authorize",
                'token_endpoint': token_endpoint,
                'scim_base_url': f"https://{tenant.subdomain}.localhost:3000/api/v1",
                'is_active': True
            }
        )
        
        if not created:
            # Update existing config
            sso_config.azure_tenant_id = azure_tenant_id
            sso_config.client_id = client_id
            sso_config.client_secret = client_secret
            sso_config.authority = authority
            sso_config.authorization_endpoint = f"{authority}/oauth2/v2.0/authorize"
            sso_config.token_endpoint = token_endpoint
            sso_config.is_active = True
            sso_config.save()
        
        # Log audit event
        AzureADAuditLog.log_event(
            tenant=tenant,
            user=request.user,
            event_type='SSO_CONFIGURED',
            description=f'Azure AD SSO configured for tenant {tenant.name}',
            details={
                'azure_tenant_id': azure_tenant_id,
                'client_id': client_id
            },
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        return Response({
            'id': str(sso_config.id),
            'azure_tenant_id': sso_config.azure_tenant_id,
            'client_id': sso_config.client_id,
            'authority': sso_config.authority,
            'authorization_endpoint': sso_config.authorization_endpoint,
            'token_endpoint': sso_config.token_endpoint,
            'scim_enabled': sso_config.scim_enabled,
            'scim_token': sso_config.scim_token,
            'scim_base_url': sso_config.scim_base_url,
            'scim_url': sso_config.get_scim_url(),
            'auto_provision_users': sso_config.auto_provision_users,
            'auto_deprovision_users': sso_config.auto_deprovision_users,
            'sync_user_attributes': sso_config.sync_user_attributes,
            'attribute_mapping': sso_config.attribute_mapping,
            'group_role_mapping': sso_config.group_role_mapping,
            'last_sync_at': sso_config.last_sync_at,
            'last_sync_status': sso_config.last_sync_status,
            'last_sync_error': sso_config.last_sync_error,
            'is_active': sso_config.is_active,
            'created_at': sso_config.created_at,
            'updated_at': sso_config.updated_at,
            'status': 'configured',
            'message': 'Azure AD SSO configured successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Azure SSO setup error: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def get_azure_sso_config(request):
    """
    Get current Azure SSO configuration for the tenant.
    
    GET /api/v1/tenant/sso-config/
    """
    try:
        tenant = request.user.primary_tenant
        
        try:
            sso_config = tenant.azure_sso_config
        except AzureSSOConfig.DoesNotExist:
            return Response({
                'error': 'Azure SSO not configured for this tenant'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'id': str(sso_config.id),
            'azure_tenant_id': sso_config.azure_tenant_id,
            'client_id': sso_config.client_id,
            'authority': sso_config.authority,
            'authorization_endpoint': sso_config.authorization_endpoint,
            'token_endpoint': sso_config.token_endpoint,
            'scim_enabled': sso_config.scim_enabled,
            'scim_token': sso_config.scim_token,
            'scim_base_url': sso_config.scim_base_url,
            'scim_url': sso_config.get_scim_url(),
            'auto_provision_users': sso_config.auto_provision_users,
            'auto_deprovision_users': sso_config.auto_deprovision_users,
            'sync_user_attributes': sso_config.sync_user_attributes,
            'attribute_mapping': sso_config.attribute_mapping,
            'group_role_mapping': sso_config.group_role_mapping,
            'last_sync_at': sso_config.last_sync_at,
            'last_sync_status': sso_config.last_sync_status,
            'last_sync_error': sso_config.last_sync_error,
            'is_active': sso_config.is_active,
            'created_at': sso_config.created_at,
            'updated_at': sso_config.updated_at
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Get Azure SSO config error: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([])  # No authentication required for public config check
@parser_classes([JSONParser, FormParser, MultiPartParser])
def get_azure_ad_config_for_auth(request):
    """
    Get Azure AD configuration for authentication (used by frontend auth system).
    
    GET /api/v1/tokens/azure/config
    Can also accept ?tenant_subdomain=<subdomain> query parameter
    """
    try:
        # Priority 1: Check for tenant subdomain in query parameter
        subdomain = request.GET.get('tenant_subdomain')
        
        # Priority 2: Check X-Tenant-Subdomain header
        if not subdomain:
            subdomain = request.META.get('HTTP_X_TENANT_SUBDOMAIN')
        
        # Priority 3: Extract from hostname
        if not subdomain:
            host = request.META.get('HTTP_HOST', '')
            
            # Extract subdomain from hostname
            if '.localhost' in host:
                subdomain = host.split('.')[0].lower()
            elif '.' in host and not host.startswith('www.'):
                # Production: extract subdomain (e.g., company1.example.com -> company1)
                subdomain = host.split('.')[0].lower()
        
        if not subdomain:
            return Response({
                'error': 'Invalid tenant subdomain. Please provide tenant_subdomain query parameter or access via subdomain URL.',
                'hint': 'Access via tenant subdomain (e.g., company1.localhost:3000) or add ?tenant_subdomain=company1'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Skip common non-tenant subdomains
        if subdomain in ['www', 'api', 'admin', 'app', 'dashboard']:
            return Response({
                'error': 'Invalid tenant subdomain'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get tenant by subdomain
        try:
            tenant = Tenant.objects.get(subdomain=subdomain, is_active=True)
        except Tenant.DoesNotExist:
            return Response({
                'error': f'Tenant not found for subdomain: {subdomain}'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            sso_config = tenant.azure_sso_config
        except AzureSSOConfig.DoesNotExist:
            return Response({
                'error': 'Azure AD not configured for this tenant'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Construct redirect URI - always use subdomain format with localhost:3000
        callback_url = f"http://{subdomain}.localhost:3000/api/auth/callback/azure"
        
        # Return configuration in the format expected by the frontend auth system
        return Response({
            'client_id': sso_config.client_id,
            'azure_tenant_id': sso_config.azure_tenant_id,  # Include both names for compatibility
            'tenant_id': sso_config.azure_tenant_id,
            'redirect_uri': callback_url,
            'authority': sso_config.authority or f"https://login.microsoftonline.com/{sso_config.azure_tenant_id}",
            'scopes': ['openid', 'profile', 'email', 'User.Read']
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Get Azure AD config for auth error: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def sync_users_from_azure(request):
    """
    Sync users from Azure AD via SCIM.
    
    POST /api/v1/tenant/sync-users/
    """
    try:
        tenant = request.user.primary_tenant
        
        # Check if Azure SSO is configured
        try:
            sso_config = tenant.azure_sso_config
            if not sso_config.is_active:
                return Response({
                    'error': 'Azure SSO is not active for this tenant'
                }, status=status.HTTP_400_BAD_REQUEST)
        except AzureSSOConfig.DoesNotExist:
            return Response({
                'error': 'Azure SSO not configured for this tenant'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Trigger sync
        scim_service = AzureSCIMService(tenant)
        stats = scim_service.sync_all_users()
        
        # Log audit event
        AzureADAuditLog.log_event(
            tenant=tenant,
            user=request.user,
            event_type='SCIM_SYNC_STARTED',
            description=f'Manual user sync initiated by {request.user.email}',
            details=stats,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        # Build response message
        message_parts = []
        if stats.get('created', 0) > 0:
            message_parts.append(f"{stats['created']} new user(s) created")
        if stats.get('skipped_existing', 0) > 0:
            message_parts.append(f"{stats['skipped_existing']} existing user(s) skipped")
        if stats.get('memberships_created', 0) > 0:
            message_parts.append(f"{stats['memberships_created']} membership(s) created")
        
        message = 'User sync completed. ' + ', '.join(message_parts) if message_parts else 'User sync completed.'
        
        # Add warning if users were skipped
        if stats.get('skipped_existing', 0) > 0:
            existing_users = stats.get('existing_users', [])
            if existing_users:
                message += f" {len(existing_users)} user(s) already exist in other tenant(s) and were not added."
        
        return Response({
            'status': 'success',
            'message': message,
            'stats': stats
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"User sync error: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tenant_users(request):
    """
    Get all users for a tenant with their roles and status.
    
    GET /api/v1/tenant/users/
    """
    try:
        tenant = request.user.primary_tenant
        
        # Get query parameters
        role = request.GET.get('role')
        is_active = request.GET.get('is_active')
        search = request.GET.get('search')
        
        # Get users for tenant
        from api.models import TenantMembership
        memberships = TenantMembership.objects.filter(
            tenant=tenant
        ).select_related('user')
        
        # Apply filters
        if role:
            memberships = memberships.filter(role=role)
        if is_active is not None:
            memberships = memberships.filter(is_active=is_active.lower() == 'true')
        if search:
            memberships = memberships.filter(
                user__email__icontains=search
            ) | memberships.filter(
                user__first_name__icontains=search
            ) | memberships.filter(
                user__last_name__icontains=search
            )
        
        # Format response
        users = []
        for membership in memberships:
            user_data = {
                'id': str(membership.user.id),
                'email': membership.user.email,
                'first_name': membership.user.first_name,
                'last_name': membership.user.last_name,
                'department': membership.user.department,
                'job_title': membership.user.job_title,
                'role': membership.role,
                'is_active': membership.is_active,
                'is_sso_user': membership.user.is_sso_user,
                'invite_status': 'accepted' if membership.invite_accepted_at else 'pending' if membership.invite_token else 'not_invited',
                'invited_at': membership.invited_at,
                'accepted_invite_at': membership.invite_accepted_at,
                'joined_at': membership.joined_at,
                'permissions': {
                    'can_run_scans': membership.can_run_scans,
                    'can_manage_users': membership.can_manage_users,
                    'can_manage_integrations': membership.can_manage_integrations,
                    'can_export_reports': membership.can_export_reports,
                }
            }
            users.append(user_data)
        
        return Response({
            'users': users,
            'total': len(users)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Get tenant users error: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_user_role(request, user_id):
    """
    Assign role to a user.
    
    POST /api/v1/tenant/users/{user_id}/assign-role/
    """
    try:
        tenant = request.user.primary_tenant
        role = request.data.get('role')
        
        if not role:
            return Response({
                'error': 'Role is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if role not in ['owner', 'admin', 'auditor', 'viewer']:
            return Response({
                'error': 'Invalid role'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user membership
        from api.models import TenantMembership
        try:
            membership = TenantMembership.objects.get(
                user_id=user_id,
                tenant=tenant
            )
        except TenantMembership.DoesNotExist:
            return Response({
                'error': 'User not found in tenant'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update role
        old_role = membership.role
        membership.role = role
        
        # Set permissions based on role
        scim_service = AzureSCIMService(tenant)
        scim_service._set_role_permissions(membership, role)
        
        # Log audit event
        AzureADAuditLog.log_event(
            tenant=tenant,
            user=request.user,
            event_type='ROLE_CHANGED',
            description=f'Role changed from {old_role} to {role} for user {membership.user.email}',
            details={
                'user_id': str(membership.user.id),
                'old_role': old_role,
                'new_role': role
            },
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        return Response({
            'status': 'success',
            'message': f'Role updated to {role}',
            'membership': {
                'user_id': str(membership.user.id),
                'email': membership.user.email,
                'role': membership.role,
                'permissions': {
                    'can_run_scans': membership.can_run_scans,
                    'can_manage_users': membership.can_manage_users,
                    'can_manage_integrations': membership.can_manage_integrations,
                    'can_export_reports': membership.can_export_reports,
                }
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Assign role error: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_tenant_user(request, user_id):
    """
    Delete a user from the tenant (removes membership, soft deletes user if no other tenants).
    
    DELETE /api/v1/tenant/users/{user_id}/
    """
    try:
        tenant = request.user.primary_tenant
        
        # Get user membership
        from api.models import TenantMembership, User
        try:
            membership = TenantMembership.objects.get(
                user_id=user_id,
                tenant=tenant
            )
        except TenantMembership.DoesNotExist:
            return Response({
                'error': 'User not found in tenant'
            }, status=status.HTTP_404_NOT_FOUND)
        
        user_email = membership.user.email
        
        # Prevent deleting yourself
        if membership.user.id == request.user.id:
            return Response({
                'error': 'You cannot delete your own account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Log audit event before deletion
        AzureADAuditLog.log_event(
            tenant=tenant,
            user=request.user,
            event_type='USER_DELETED',
            description=f'User {user_email} removed from tenant {tenant.name}',
            details={
                'deleted_user_id': str(membership.user.id),
                'deleted_user_email': user_email,
            },
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        # Get user before deleting membership
        user = membership.user
        
        # Delete membership (removes user from tenant)
        membership.delete()
        
        # Check if user has other tenant memberships
        remaining_memberships = TenantMembership.objects.filter(user_id=user_id).count()
        
        # If user has no other tenant memberships, soft delete the user
        if remaining_memberships == 0:
            user.is_active = False
            user.deactivated_at = timezone.now()
            # Use valid choice value - detailed reason is already logged in audit log above
            # The field max_length is 50 and has choices, so use the choice value
            user.deactivation_reason = 'MANUAL'
            user.save()
        
        return Response({
            'status': 'success',
            'message': f'User {user_email} has been removed from the tenant'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def update_user_permissions(request, user_id):
    """
    Update user permissions.
    
    PATCH /api/v1/tenant/users/{user_id}/permissions/
    """
    try:
        tenant = request.user.primary_tenant
        permissions = request.data.get('permissions', {})
        
        # Get user membership
        from api.models import TenantMembership
        try:
            membership = TenantMembership.objects.get(
                user_id=user_id,
                tenant=tenant
            )
        except TenantMembership.DoesNotExist:
            return Response({
                'error': 'User not found in tenant'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update permissions
        permission_fields = {
            'can_run_scans': membership.can_run_scans,
            'can_export_reports': membership.can_export_reports,
            'can_invite_users': membership.can_invite_users,
            'can_manage_users': membership.can_manage_users,
            'can_manage_settings': membership.can_manage_settings,
            'can_view_analytics': membership.can_view_analytics,
            'can_manage_billing': membership.can_manage_billing,
            'can_manage_providers': membership.can_manage_providers,
            'can_manage_integrations': membership.can_manage_integrations,
            'can_manage_scans': membership.can_manage_scans,
            'unlimited_visibility': membership.unlimited_visibility,
        }
        
        # Track changes
        changes = {}
        for field, old_value in permission_fields.items():
            if field in permissions:
                new_value = bool(permissions[field])
                if old_value != new_value:
                    setattr(membership, field, new_value)
                    changes[field] = {'old': old_value, 'new': new_value}
        
        membership.save()
        
        # Log audit event
        if changes:
            AzureADAuditLog.log_event(
                tenant=tenant,
                user=request.user,
                event_type='PERMISSIONS_CHANGED',
                description=f'Permissions updated for user {membership.user.email}',
                details={
                    'user_id': str(membership.user.id),
                    'user_email': membership.user.email,
                    'changes': changes
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
        
        return Response({
            'status': 'success',
            'message': 'Permissions updated successfully',
            'permissions': {
                'can_run_scans': membership.can_run_scans,
                'can_export_reports': membership.can_export_reports,
                'can_invite_users': membership.can_invite_users,
                'can_manage_users': membership.can_manage_users,
                'can_manage_settings': membership.can_manage_settings,
                'can_view_analytics': membership.can_view_analytics,
                'can_manage_billing': membership.can_manage_billing,
                'can_manage_providers': membership.can_manage_providers,
                'can_manage_integrations': membership.can_manage_integrations,
                'can_manage_scans': membership.can_manage_scans,
                'unlimited_visibility': membership.unlimited_visibility,
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Update permissions error: {e}")
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def invite_user(request):
    """
    Invite a user to the tenant (simplified endpoint for Azure AD config page).
    
    POST /api/v1/tenant/invite-user/
    """
    try:
        logger.info(f"🔔 Invite user request received - User: {request.user.email if request.user else 'Anonymous'}")
        data = request.data
        email = data.get('email')
        role = data.get('role', 'member')
        
        logger.info(f"📧 Inviting user: {email} with role: {role}")
        
        if not email:
            logger.warning("❌ Email is missing from request")
            return Response({
                'error': 'Email is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Ensure user is authenticated
        if not request.user or not hasattr(request.user, 'id'):
            logger.warning(f"❌ User not authenticated: {request.user}")
            return Response({
                'error': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        tenant = request.user.primary_tenant
        logger.info(f"🏢 Tenant: {tenant.name} (subdomain: {tenant.subdomain})")
        
        # Check if user exists and has membership
        from api.models import TenantMembership
        try:
            user = User.objects.get(email=email)
            logger.info(f"✅ User found: {user.email} (ID: {user.id})")
            # User exists, check membership
            try:
                membership = TenantMembership.objects.get(
                    user=user,
                    tenant=tenant
                )
                logger.info(f"✅ Membership found: {membership.id}, invite_token: {bool(membership.invite_token)}, invite_accepted_at: {membership.invite_accepted_at}")
                # User already has membership, check invite status
                invitation = None  # Initialize to track if we need to create a new invite
                
                if membership.invite_token:
                    logger.info(f"📨 User already has invite token, checking expiry...")
                    # User is already invited but hasn't accepted
                    if membership.invite_expires_at:
                        # Compare datetimes - ensure both are timezone-aware
                        expires_at = membership.invite_expires_at
                        now = timezone.now()
                        logger.info(f"⏰ Invite expires at: {expires_at}, Now: {now}")
                        # Handle timezone-naive datetimes by making them aware
                        try:
                            if timezone.is_naive(expires_at):
                                logger.info("🕐 Converting naive datetime to aware")
                                expires_at = timezone.make_aware(expires_at)
                        except (ValueError, TypeError) as e:
                            logger.warning(f"⚠️ Error converting datetime: {e}, using as-is")
                            # If datetime is already aware or invalid, use as-is
                            pass
                        if expires_at < now:
                            logger.info("⏰ Invite expired, creating new invite...")
                            # Invite expired, create new invite
                            invite_service = InviteService()
                            invitation = invite_service.create_invite(
                                tenant=tenant,
                                email=email,
                                role=role,
                                invited_by=request.user
                            )
                            logger.info(f"✅ New invitation created: {invitation.id}")
                            # Update membership with new invite
                            membership.invite_token = invitation.token
                            membership.invited_at = invitation.inserted_at
                            membership.invite_expires_at = invitation.expires_at
                            membership.save()
                            logger.info("✅ Membership updated with new invite")
                        else:
                            logger.info("✅ Invite still valid, resending invitation email...")
                            # Invite still valid - but resend email anyway (user requested)
                            # Find the existing invitation by token
                            from api.models import Invitation
                            try:
                                existing_invitation = Invitation.objects.get(
                                    tenant_id=tenant.id,
                                    token=membership.invite_token,
                                    email=email
                                )
                                logger.info(f"📧 Found existing invitation: {existing_invitation.id}, resending email...")
                                # Resend the invitation email
                                invite_service = InviteService()
                                email_sent = invite_service.send_invite_email(invitation=existing_invitation)
                                logger.info(f"✅ Resent invitation email: {email_sent}")
                                
                                # Log audit event
                                AzureADAuditLog.log_event(
                                    tenant=tenant,
                                    user=request.user,
                                    event_type='USER_INVITED',
                                    description=f'Invitation email resent to {email} for tenant {tenant.name}',
                                    details={
                                        'invited_email': email,
                                        'role': role,
                                        'email_sent': email_sent,
                                        'resend': True
                                    },
                                    ip_address=request.META.get('REMOTE_ADDR'),
                                    user_agent=request.META.get('HTTP_USER_AGENT')
                                )
                                
                                return Response({
                                    'status': 'success',
                                    'message': f'Invitation email resent to {email}',
                                    'invite_status': 'pending',
                                    'invited_at': membership.invited_at.isoformat() if membership.invited_at else None,
                                    'email_sent': email_sent,
                                    'invitation': {
                                        'email': email,
                                        'role': role,
                                        'expires_at': membership.invite_expires_at.isoformat() if membership.invite_expires_at else None
                                    }
                                }, status=status.HTTP_200_OK)
                            except Invitation.DoesNotExist:
                                logger.warning(f"⚠️ Invitation not found for token, creating new invite...")
                                # Invitation doesn't exist, create new one
                                invite_service = InviteService()
                                invitation = invite_service.create_invite(
                                    tenant=tenant,
                                    email=email,
                                    role=role,
                                    invited_by=request.user
                                )
                                logger.info(f"✅ New invitation created: {invitation.id}")
                                # Update membership with new invite
                                membership.invite_token = invitation.token
                                membership.invited_at = invitation.inserted_at
                                membership.invite_expires_at = invitation.expires_at
                                membership.save()
                                logger.info("✅ Membership updated with new invite")
                                
                                # Send invitation email
                                logger.info(f"📧 Sending invitation email...")
                                email_sent = invite_service.send_invite_email(invitation=invitation)
                                logger.info(f"✅ Email sent: {email_sent}")
                                
                                # Log audit event
                                AzureADAuditLog.log_event(
                                    tenant=tenant,
                                    user=request.user,
                                    event_type='USER_INVITED',
                                    description=f'User {email} invited to tenant {tenant.name}',
                                    details={
                                        'invited_email': email,
                                        'role': role,
                                        'email_sent': email_sent
                                    },
                                    ip_address=request.META.get('REMOTE_ADDR'),
                                    user_agent=request.META.get('HTTP_USER_AGENT')
                                )
                                
                                return Response({
                                    'status': 'success',
                                    'message': f"Invitation sent to {email}",
                                    'invitation': {
                                        'id': str(invitation.id),
                                        'email': invitation.email,
                                        'role': role,
                                        'expires_at': invitation.expires_at.isoformat(),
                                        'email_sent': email_sent
                                    }
                                }, status=status.HTTP_201_CREATED)
                    else:
                        logger.info("⚠️ No expiry date on invite, resending email...")
                        # No expiry - but resend email anyway
                        # Find the existing invitation by token
                        from api.models import Invitation
                        try:
                            existing_invitation = Invitation.objects.get(
                                tenant_id=tenant.id,
                                token=membership.invite_token,
                                email=email
                            )
                            logger.info(f"📧 Found existing invitation: {existing_invitation.id}, resending email...")
                            # Resend the invitation email
                            invite_service = InviteService()
                            email_sent = invite_service.send_invite_email(invitation=existing_invitation)
                            logger.info(f"✅ Resent invitation email: {email_sent}")
                            
                            # Log audit event
                            AzureADAuditLog.log_event(
                                tenant=tenant,
                                user=request.user,
                                event_type='USER_INVITED',
                                description=f'Invitation email resent to {email} for tenant {tenant.name}',
                                details={
                                    'invited_email': email,
                                    'role': role,
                                    'email_sent': email_sent,
                                    'resend': True
                                },
                                ip_address=request.META.get('REMOTE_ADDR'),
                                user_agent=request.META.get('HTTP_USER_AGENT')
                            )
                            
                            return Response({
                                'status': 'success',
                                'message': f'Invitation email resent to {email}',
                                'invite_status': 'pending',
                                'invited_at': membership.invited_at.isoformat() if membership.invited_at else None,
                                'email_sent': email_sent,
                                'invitation': {
                                    'email': email,
                                    'role': role
                                }
                            }, status=status.HTTP_200_OK)
                        except Invitation.DoesNotExist:
                            logger.warning(f"⚠️ Invitation not found, creating new invite...")
                            # Invitation doesn't exist, create new one
                            invite_service = InviteService()
                            invitation = invite_service.create_invite(
                                tenant=tenant,
                                email=email,
                                role=role,
                                invited_by=request.user
                            )
                            logger.info(f"✅ New invitation created: {invitation.id}")
                            # Update membership with new invite
                            membership.invite_token = invitation.token
                            membership.invited_at = invitation.inserted_at
                            membership.invite_expires_at = invitation.expires_at
                            membership.save()
                            logger.info("✅ Membership updated with new invite")
                            
                            # Send invitation email
                            logger.info(f"📧 Sending invitation email...")
                            email_sent = invite_service.send_invite_email(invitation=invitation)
                            logger.info(f"✅ Email sent: {email_sent}")
                            
                            # Log audit event
                            AzureADAuditLog.log_event(
                                tenant=tenant,
                                user=request.user,
                                event_type='USER_INVITED',
                                description=f'User {email} invited to tenant {tenant.name}',
                                details={
                                    'invited_email': email,
                                    'role': role,
                                    'email_sent': email_sent
                                },
                                ip_address=request.META.get('REMOTE_ADDR'),
                                user_agent=request.META.get('HTTP_USER_AGENT')
                            )
                            
                            return Response({
                                'status': 'success',
                                'message': f"Invitation sent to {email}",
                                'invitation': {
                                    'id': str(invitation.id),
                                    'email': invitation.email,
                                    'role': role,
                                    'expires_at': invitation.expires_at.isoformat(),
                                    'email_sent': email_sent
                                }
                            }, status=status.HTTP_201_CREATED)
                elif membership.invite_accepted_at:
                    logger.info(f"✅ User already accepted invite at {membership.invite_accepted_at}")
                    # User already accepted invite
                    return Response({
                        'error': 'User has already been invited and accepted the invitation.',
                        'invite_status': 'accepted',
                        'accepted_at': membership.invite_accepted_at.isoformat()
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    logger.info("📨 User has membership but no invite token - creating new invite...")
                    # User has membership but no invite token - create new invite
                    invite_service = InviteService()
                    invitation = invite_service.create_invite(
                        tenant=tenant,
                        email=email,
                        role=role,
                        invited_by=request.user
                    )
                    logger.info(f"✅ Invitation created: {invitation.id}")
                    # Update membership with invite
                    membership.invite_token = invitation.token
                    membership.invited_at = invitation.inserted_at
                    membership.invite_expires_at = invitation.expires_at
                    membership.save()
                    logger.info("✅ Membership updated with invite token")
                
                # If we created a new invitation, continue to send email
                if invitation:
                    logger.info(f"📧 Sending invitation email for invitation: {invitation.id}")
                    invite_service = InviteService()
                    email_sent = invite_service.send_invite_email(invitation=invitation)
                    logger.info(f"✅ Email sent: {email_sent}")
                    
                    # Log audit event
                    AzureADAuditLog.log_event(
                        tenant=tenant,
                        user=request.user,
                        event_type='USER_INVITED',
                        description=f'User {email} invited to tenant {tenant.name}',
                        details={
                            'invited_email': email,
                            'role': role,
                            'email_sent': email_sent
                        },
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT')
                    )
                    
                    return Response({
                        'status': 'success',
                        'message': f"Invitation sent to {email}",
                        'invitation': {
                            'id': str(invitation.id),
                            'email': invitation.email,
                            'role': role,
                            'expires_at': invitation.expires_at.isoformat(),
                            'email_sent': email_sent
                        }
                    }, status=status.HTTP_201_CREATED)
            except TenantMembership.DoesNotExist:
                logger.info("📨 User exists but no membership - creating invite and membership...")
                # User exists but no membership - create invite and membership
                invite_service = InviteService()
                invitation = invite_service.create_invite(
                    tenant=tenant,
                    email=email,
                    role=role,
                    invited_by=request.user
                )
                logger.info(f"✅ Invitation created: {invitation.id}")
                # Create membership for existing user with invite token
                membership = TenantMembership.objects.create(
                    user=user,
                    tenant=tenant,
                    role=role,
                    invite_token=invitation.token,
                    invited_at=invitation.inserted_at,
                    invite_expires_at=invitation.expires_at,
                    is_active=True
                )
                logger.info(f"✅ Membership created: {membership.id}")
                
                # Send invitation email
                logger.info(f"📧 Sending invitation email...")
                email_sent = invite_service.send_invite_email(invitation=invitation)
                logger.info(f"✅ Email sent: {email_sent}")
                
                # Log audit event
                AzureADAuditLog.log_event(
                    tenant=tenant,
                    user=request.user,
                    event_type='USER_INVITED',
                    description=f'User {email} invited to tenant {tenant.name}',
                    details={
                        'invited_email': email,
                        'role': role,
                        'email_sent': email_sent
                    },
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )
                
                return Response({
                    'status': 'success',
                    'message': f"Invitation sent to {email}",
                    'invitation': {
                        'id': str(invitation.id),
                        'email': invitation.email,
                        'role': role,
                        'expires_at': invitation.expires_at.isoformat(),
                        'email_sent': email_sent
                    }
                }, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            logger.info("📨 User doesn't exist - creating invitation for new user...")
            # User doesn't exist, create invitation for new user
            invite_service = InviteService()
            invitation = invite_service.create_invite(
                tenant=tenant,
                email=email,
                role=role,
                invited_by=request.user
            )
            logger.info(f"✅ Invitation created: {invitation.id}")
            
            # Send invitation email
            logger.info(f"📧 Sending invitation email...")
            email_sent = invite_service.send_invite_email(invitation=invitation)
            logger.info(f"✅ Email sent: {email_sent}")
            
            # Log audit event
            AzureADAuditLog.log_event(
                tenant=tenant,
                user=request.user,
                event_type='USER_INVITED',
                description=f'User {email} invited to tenant {tenant.name}',
                details={
                    'invited_email': email,
                    'role': role,
                    'email_sent': email_sent
                },
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            return Response({
                'status': 'success',
                'message': f"Invitation sent to {email}",
                'invitation': {
                    'id': str(invitation.id),
                    'email': invitation.email,
                    'role': role,
                    'expires_at': invitation.expires_at.isoformat(),
                    'email_sent': email_sent
                }
            }, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import traceback
        logger.error(f"Invite user error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return Response({
            'error': str(e),
            'detail': traceback.format_exc()
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_invite(request):
    """
    Create a user invitation.
    
    POST /api/v1/tenant/invite/
    """
    try:
        data = request.data
        tenant_id = data.get('tenant_id')
        email = data.get('email')
        role = data.get('role', 'member')
        
        if not tenant_id or not email:
            return Response({
                'success': False,
                'error': 'tenant_id and email are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get tenant
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Tenant not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create invitation
        invite_service = InviteService()
        invitation = invite_service.create_invite(
            tenant=tenant,
            email=email,
            role=role,
            invited_by=request.user,
            custom_message=data.get('custom_message'),
            expires_hours=data.get('expires_hours')
        )
        
        # Send invitation email
        email_sent = invite_service.send_invite_email(
            invitation=invitation,
            custom_message=data.get('custom_message')
        )
        
        return Response({
            'success': True,
            'message': f"Invitation sent to {email}",
            'invitation': {
                'id': str(invitation.id),
                'email': invitation.email,
                'tenant': tenant.name,
                'role': role,
                'expires_at': invitation.expires_at.isoformat(),
                'email_sent': email_sent
            }
        }, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"❌ Failed to create invitation: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_bulk_invites(request):
    """
    Create multiple user invitations.
    
    POST /api/v1/tenant/bulk-invite/
    """
    try:
        data = request.data
        tenant_id = data.get('tenant_id')
        invite_data = data.get('invites', [])
        
        if not tenant_id or not invite_data:
            return Response({
                'success': False,
                'error': 'tenant_id and invites are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get tenant
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Tenant not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create bulk invitations
        invite_service = InviteService()
        invitations = invite_service.create_bulk_invites(
            tenant=tenant,
            invite_data=invite_data,
            invited_by=request.user
        )
        
        # Send invitation emails
        email_results = []
        for invitation in invitations:
            email_sent = invite_service.send_invite_email(invitation)
            email_results.append({
                'invitation_id': str(invitation.id),
                'email': invitation.email,
                'email_sent': email_sent
            })
        
        return Response({
            'success': True,
            'message': f"Created {len(invitations)} invitations",
            'invitations': email_results
        }, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"❌ Failed to create bulk invitations: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def validate_invite_token(request):
    """
    Validate an invitation token.
    
    GET /api/v1/tenant/validate-invite/?token=<token>
    """
    try:
        token = request.GET.get('token')
        if not token:
            return Response({
                'success': False,
                'error': 'Token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate token
        invite_service = InviteService()
        is_valid, invitation, error = invite_service.validate_invite_token(token)
        
        if not is_valid:
            return Response({
                'success': False,
                'error': error
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'invitation': {
                'id': str(invitation.id),
                'email': invitation.email,
                'tenant': {
                    'id': str(invitation.tenant_id.id),
                    'name': invitation.tenant_id.name,
                    'subdomain': invitation.tenant_id.subdomain
                },
                'expires_at': invitation.expires_at.isoformat(),
                'inviter': invitation.inviter.name if invitation.inviter else None
            },
            'tenant_id': str(invitation.tenant_id.id),
            'tenant_name': invitation.tenant_id.name,
            'tenant_subdomain': invitation.tenant_id.subdomain,
            'user_email': invitation.email
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Failed to validate invite token: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def accept_invite(request):
    """
    Accept an invitation and create user account.
    
    POST /api/v1/tenant/accept-invite/
    """
    try:
        data = request.data
        token = data.get('token')
        user_data = data.get('user_data', {})
        
        if not token:
            return Response({
                'success': False,
                'error': 'Token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate token
        invite_service = InviteService()
        is_valid, invitation, error = invite_service.validate_invite_token(token)
        
        if not is_valid:
            return Response({
                'success': False,
                'error': error
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Accept invitation
        success, user, error = invite_service.accept_invite(
            invitation=invitation,
            user_data=user_data,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        if not success:
            return Response({
                'success': False,
                'error': error
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Return tenant subdomain and Azure AD SSO login URL
        tenant_subdomain = invitation.tenant_id.subdomain
        
        # Get Azure AD SSO configuration for direct login URL
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        sso_redirect_url = None
        azure_login_url = None
        
        try:
            sso_config = invitation.tenant_id.azure_sso_config
            if sso_config and sso_config.is_active:
                # Construct Azure AD OAuth authorization URL directly using tenant's SSO config from DB
                authority = sso_config.authority or f"https://login.microsoftonline.com/{sso_config.azure_tenant_id}"
                
                # Construct redirect URI - always use tenant subdomain format with localhost:3000
                callback_url = f"http://{tenant_subdomain}.localhost:3000/api/auth/callback/azure"
                
                # Construct Azure AD OAuth authorization URL
                from urllib.parse import urlencode
                params = {
                    'client_id': sso_config.client_id,
                    'response_type': 'code',
                    'redirect_uri': callback_url,
                    'response_mode': 'query',
                    'scope': 'openid profile email User.Read',
                    'state': f"tenant:{tenant_subdomain}:invite_accepted"
                }
                
                azure_login_url = f"{authority}/oauth2/v2.0/authorize?{urlencode(params)}"
                
                logger.info(f"✅ Generated Azure AD login URL for tenant {tenant_subdomain}: {azure_login_url[:100]}...")
                
                # Also provide a fallback sign-in page URL - always use subdomain format with localhost:3000
                sso_redirect_url = f"http://{tenant_subdomain}.localhost:3000/sign-in?mode=sso&invite_accepted=true"
        except AzureSSOConfig.DoesNotExist:
            logger.warning(f"Azure SSO not configured for tenant {tenant_subdomain}")
            # Fallback to sign-in page - always use subdomain format with localhost:3000
            sso_redirect_url = f"http://{tenant_subdomain}.localhost:3000/sign-in?mode=sso&invite_accepted=true"
        
        return Response({
            'success': True,
            'message': f"Welcome to {invitation.tenant_id.name}! Redirecting to Azure AD SSO login...",
            'user': {
                'id': str(user.id),
                'email': user.email,
                'name': user.name,
                'is_sso_user': user.is_sso_user,
            },
            'tenant': {
                'id': str(invitation.tenant_id.id),
                'name': invitation.tenant_id.name,
                'subdomain': tenant_subdomain
            },
            'sso_redirect_url': sso_redirect_url,  # Fallback to sign-in page
            'azure_login_url': azure_login_url,  # Direct Azure AD OAuth URL
            'requires_sso': True  # Flag indicating user must use SSO
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"❌ Failed to accept invitation: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tenant_invites(request):
    """
    Get all invitations for a tenant.
    
    GET /api/v1/tenant/invites/?tenant_id=<id>&status=<status>
    """
    try:
        tenant_id = request.GET.get('tenant_id')
        status_filter = request.GET.get('status')
        
        if not tenant_id:
            return Response({
                'success': False,
                'error': 'tenant_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get tenant
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Tenant not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get invitations
        invite_service = InviteService()
        invitations = invite_service.get_tenant_invites(tenant, status_filter)
        
        return Response({
            'success': True,
            'invitations': [
                {
                    'id': str(invitation.id),
                    'email': invitation.email,
                    'state': invitation.state,
                    'expires_at': invitation.expires_at.isoformat(),
                    'inviter': invitation.inviter.name if invitation.inviter else None,
                    'created_at': invitation.inserted_at.isoformat()
                }
                for invitation in invitations
            ]
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Failed to get tenant invitations: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_invite(request):
    """
    Revoke an invitation.
    
    POST /api/v1/tenant/revoke-invite/
    """
    try:
        data = request.data
        invitation_id = data.get('invitation_id')
        
        if not invitation_id:
            return Response({
                'success': False,
                'error': 'invitation_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get invitation
        try:
            invitation = Invitation.objects.get(id=invitation_id)
        except Invitation.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Invitation not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Revoke invitation
        invite_service = InviteService()
        success = invite_service.revoke_invite(
            invitation=invitation,
            revoked_by=request.user
        )
        
        if not success:
            return Response({
                'success': False,
                'error': 'Failed to revoke invitation'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'message': f"Invitation for {invitation.email} has been revoked"
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Failed to revoke invitation: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_tenant_summary(request):
    """
    Get comprehensive tenant summary.
    
    GET /api/v1/tenant/summary/?tenant_id=<id>
    """
    try:
        tenant_id = request.GET.get('tenant_id')
        
        if not tenant_id:
            return Response({
                'success': False,
                'error': 'tenant_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get tenant
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Tenant not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get tenant summary
        tenant_service = TenantService()
        summary = tenant_service.get_tenant_summary(tenant)
        
        return Response({
            'success': True,
            'summary': summary
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Failed to get tenant summary: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_domain(request):
    """
    Verify domain ownership for a tenant.
    
    POST /api/v1/tenant/verify-domain/
    """
    try:
        data = request.data
        tenant_id = data.get('tenant_id')
        domain = data.get('domain')
        verification_method = data.get('method', 'dns')
        
        if not tenant_id or not domain:
            return Response({
                'success': False,
                'error': 'tenant_id and domain are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get tenant
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Tenant not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Verify domain
        domain_service = DomainService()
        is_verified, error = domain_service.verify_domain_ownership(
            tenant=tenant,
            domain=domain,
            verification_method=verification_method
        )
        
        if not is_verified:
            return Response({
                'success': False,
                'error': error
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'message': f"Domain {domain} verified successfully"
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Failed to verify domain: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_domain_verification_instructions(request):
    """
    Get domain verification instructions.
    
    GET /api/v1/tenant/domain-instructions/?tenant_id=<id>&domain=<domain>&method=<method>
    """
    try:
        tenant_id = request.GET.get('tenant_id')
        domain = request.GET.get('domain')
        verification_method = request.GET.get('method', 'dns')
        
        if not tenant_id or not domain:
            return Response({
                'success': False,
                'error': 'tenant_id and domain are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get tenant
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Tenant not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get verification instructions
        domain_service = DomainService()
        instructions = domain_service.get_domain_verification_instructions(
            tenant=tenant,
            domain=domain,
            verification_method=verification_method
        )
        
        if 'error' in instructions:
            return Response({
                'success': False,
                'error': instructions['error']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': True,
            'instructions': instructions
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"❌ Failed to get domain verification instructions: {e}")
        return Response({
            'success': False,
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
