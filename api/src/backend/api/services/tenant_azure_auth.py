"""
Tenant-Aware Azure AD Authentication Service

This service provides complete tenant isolation for Azure AD authentication.
Each tenant can have their own Azure AD configuration and users are strictly
isolated to their authorized tenants.
"""

import logging
import requests
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response

from api.models import Tenant, TenantMembership
from api.models import TenantOAuthConfig, TenantOAuthUser
from api.utils.security import generate_secure_token, audit_tenant_access

logger = logging.getLogger(__name__)
User = get_user_model()


class TenantAzureAuthService:
    """
    Service class for tenant-aware Azure AD authentication.
    Provides complete tenant isolation and security.
    """
    
    def __init__(self, tenant: Tenant):
        self.tenant = tenant
        self.oauth_config = self._get_azure_config()
    
    def _get_azure_config(self) -> Optional[TenantOAuthConfig]:
        """Get Azure AD configuration for this tenant"""
        try:
            return TenantOAuthConfig.objects.get(
                tenant=self.tenant,
                provider='azure',
                is_active=True
            )
        except TenantOAuthConfig.DoesNotExist:
            return None
    
    def is_configured(self) -> bool:
        """Check if Azure AD is configured for this tenant"""
        return self.oauth_config is not None
    
    def get_authorization_url(self, state: str = None, **kwargs) -> str:
        """
        Generate Azure AD authorization URL for this tenant.
        
        Args:
            state: Optional state parameter for CSRF protection
            **kwargs: Additional parameters (domain_hint, login_hint, etc.)
        
        Returns:
            Azure AD authorization URL
        """
        if not self.is_configured():
            raise ValueError("Azure AD not configured for this tenant")
        
        return self.oauth_config.get_authorization_url(state, **kwargs)
    
    def exchange_code_for_token(self, code: str) -> Tuple[bool, Dict]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from Azure AD
        
        Returns:
            Tuple of (success, token_data)
        """
        if not self.is_configured():
            return False, {'error': 'Azure AD not configured for this tenant'}
        
        try:
            token_data = self.oauth_config.exchange_code_for_token(code)
            self.oauth_config.update_last_used()
            return True, token_data
        except Exception as e:
            logger.error(f"Token exchange failed for tenant {self.tenant.subdomain}: {e}")
            return False, {'error': 'Token exchange failed'}
    
    def get_user_info(self, access_token: str) -> Tuple[bool, Dict]:
        """
        Get user information from Azure AD.
        
        Args:
            access_token: Azure AD access token
        
        Returns:
            Tuple of (success, user_info)
        """
        if not self.is_configured():
            return False, {'error': 'Azure AD not configured for this tenant'}
        
        try:
            user_info = self.oauth_config.get_user_info(access_token)
            return True, user_info
        except Exception as e:
            logger.error(f"Failed to get user info for tenant {self.tenant.subdomain}: {e}")
            return False, {'error': 'Failed to get user information'}
    
    def authenticate_user(self, code: str, ip_address: str = None) -> Tuple[bool, Dict]:
        """
        Complete authentication flow for a user.
        
        Args:
            code: Authorization code from Azure AD
            ip_address: User's IP address for audit logging
        
        Returns:
            Tuple of (success, auth_result)
        """
        try:
            # Exchange code for token
            success, token_data = self.exchange_code_for_token(code)
            if not success:
                return False, token_data
            
            access_token = token_data.get('access_token')
            if not access_token:
                return False, {'error': 'No access token received'}
            
            # Get user info
            success, user_info = self.get_user_info(access_token)
            if not success:
                return False, user_info
            
            # Extract user details
            email = user_info.get('mail') or user_info.get('userPrincipalName')
            name = user_info.get('displayName', '')
            azure_object_id = user_info.get('id')
            
            if not email:
                return False, {'error': 'No email found in user information'}
            
            # Check if user exists and belongs to this tenant
            user = self._get_or_create_user(email, name, azure_object_id)
            if not user:
                return False, {'error': 'User not authorized for this tenant'}
            
            # Create or update OAuth user record
            oauth_user = self._create_or_update_oauth_user(
                user, azure_object_id, email, token_data
            )
            
            # Generate JWT tokens with tenant context
            jwt_tokens = self._generate_tenant_jwt(user)
            
            # Update last login
            oauth_user.update_last_login()
            user.record_successful_login(ip_address)
            
            # Audit log
            audit_tenant_access(user, self.tenant, 'azure_login', {
                'ip_address': ip_address,
                'azure_object_id': azure_object_id
            })
            
            return True, {
                'access_token': jwt_tokens['access_token'],
                'refresh_token': jwt_tokens['refresh_token'],
                'token_type': 'Bearer',
                'expires_in': 3600,
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'name': user.name,
                },
                'tenant': {
                    'id': str(self.tenant.id),
                    'name': self.tenant.name,
                    'subdomain': self.tenant.subdomain,
                },
                'membership': {
                    'role': oauth_user.user.get_tenant_role(self.tenant.id),
                    'permissions': self._get_user_permissions(user)
                }
            }
            
        except Exception as e:
            logger.error(f"Authentication failed for tenant {self.tenant.subdomain}: {e}")
            return False, {'error': 'Authentication failed'}
    
    def _get_or_create_user(self, email: str, name: str, azure_object_id: str) -> Optional[User]:
        """
        Get or create user, ensuring they belong to this tenant.
        
        SECURITY: Users must have explicit tenant membership (via invitation) to authenticate.
        Auto-creation is only allowed if:
        1. User has a pending invitation for this tenant, OR
        2. Auto-creation is enabled AND user's email domain matches allowed domains
        
        Args:
            email: User's email address
            name: User's display name
            azure_object_id: Azure AD object ID
        
        Returns:
            User instance or None if not authorized
        """
        try:
            # Check if user exists
            user = User.objects.get(email=email)
            
            # SECURITY CHECK: Verify user has active membership in this tenant
            try:
                membership = TenantMembership.objects.get(
                    user=user,
                    tenant=self.tenant,
                    is_active=True
                )
                logger.info(f"User {email} authenticated for tenant {self.tenant.subdomain} with role {membership.role}")
                return user
            except TenantMembership.DoesNotExist:
                # User exists but doesn't belong to this tenant
                logger.warning(
                    f"SECURITY: User {email} attempted login to unauthorized tenant {self.tenant.subdomain}. "
                    f"User belongs to other tenants but not this one."
                )
                # Audit this security violation
                audit_tenant_access(
                    user=user,
                    tenant=self.tenant,
                    action='unauthorized_tenant_access_attempt',
                    details={
                        'email': email,
                        'azure_object_id': azure_object_id,
                        'reason': 'User does not have membership in this tenant'
                    }
                )
                return None
            
        except User.DoesNotExist:
            # User doesn't exist - check if they should be created
            
            # SECURITY: Check for pending invitation first
            from api.models import Invitation
            pending_invite = Invitation.objects.filter(
                email=email,
                tenant=self.tenant,
                status='pending',
                expires_at__gt=timezone.now()
            ).first()
            
            if pending_invite:
                # User has a valid invitation - create account and accept invite
                logger.info(f"User {email} has pending invitation for tenant {self.tenant.subdomain} - creating account")
                with transaction.atomic():
                    user = User.objects.create_user(
                        email=email,
                        name=name,
                        is_verified=not self.oauth_config.require_email_verification,
                        primary_tenant=self.tenant
                    )
                    
                    # Create tenant membership with role from invitation
                    TenantMembership.objects.create(
                        user=user,
                        tenant=self.tenant,
                        role=pending_invite.role or 'member',
                        is_active=True,
                        invited_by=pending_invite.invited_by
                    )
                    
                    # Mark invitation as accepted
                    pending_invite.status = 'accepted'
                    pending_invite.accepted_at = timezone.now()
                    pending_invite.save()
                    
                    logger.info(f"Created user {email} for tenant {self.tenant.subdomain} from invitation")
                    return user
            
            # No invitation found - check if auto-creation is enabled
            if not self.oauth_config.auto_create_users:
                logger.warning(
                    f"SECURITY: User {email} attempted login to tenant {self.tenant.subdomain} "
                    f"but no account exists and auto-creation is disabled. No invitation found."
                )
                return None
            
            # Auto-creation is enabled - check if email domain is allowed
            if not self._is_email_domain_allowed(email):
                logger.warning(
                    f"SECURITY: Email domain not allowed for tenant {self.tenant.subdomain}: {email}"
                )
                return None
            
            # SECURITY WARNING: Auto-creating user without explicit invitation
            # This should be logged as a security event
            logger.warning(
                f"SECURITY: Auto-creating user {email} for tenant {self.tenant.subdomain} "
                f"without explicit invitation. This should be reviewed."
            )
            
            # Create new user with minimal permissions
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    name=name,
                    is_verified=not self.oauth_config.require_email_verification,
                    primary_tenant=self.tenant
                )
                
                # Create tenant membership with restricted role
                TenantMembership.objects.create(
                    user=user,
                    tenant=self.tenant,
                    role='member',  # Default role - admin should review and promote if needed
                    is_active=True
                )
                
                # Audit auto-creation
                audit_tenant_access(
                    user=user,
                    tenant=self.tenant,
                    action='user_auto_created_via_azure',
                    details={
                        'email': email,
                        'azure_object_id': azure_object_id,
                        'auto_creation_enabled': True,
                        'warning': 'User created without explicit invitation'
                    }
                )
                
                logger.info(f"Auto-created user {email} for tenant {self.tenant.subdomain}")
                return user
    
    def _create_or_update_oauth_user(self, user: User, azure_object_id: str, 
                                   email: str, token_data: Dict) -> TenantOAuthUser:
        """Create or update OAuth user record"""
        oauth_user, created = TenantOAuthUser.objects.get_or_create(
            tenant=self.tenant,
            oauth_config=self.oauth_config,
            provider_user_id=azure_object_id,
            defaults={
                'user': user,
                'provider_email': email,
            }
        )
        
        # Update tokens
        oauth_user.update_tokens(
            access_token=token_data.get('access_token'),
            refresh_token=token_data.get('refresh_token'),
            expires_in=token_data.get('expires_in')
        )
        
        return oauth_user
    
    def _is_email_domain_allowed(self, email: str) -> bool:
        """Check if email domain is allowed for this tenant"""
        if not self.oauth_config.allowed_domains:
            return True  # No domain restrictions
        
        domain = email.split('@')[1].lower()
        return domain in [d.lower() for d in self.oauth_config.allowed_domains]
    
    def _generate_tenant_jwt(self, user: User) -> Dict[str, str]:
        """Generate JWT tokens with tenant context"""
        # Get user's role in this tenant
        membership = TenantMembership.objects.get(
            user=user,
            tenant=self.tenant,
            is_active=True
        )
        
        # Access token payload
        access_payload = {
            'user_id': str(user.id),
            'email': user.email,
            'tenant_id': str(self.tenant.id),
            'tenant_name': self.tenant.name,
            'tenant_subdomain': self.tenant.subdomain,
            'role': membership.role,
            'permissions': {
                'can_invite_users': membership.can_invite_users,
                'can_manage_settings': membership.can_manage_settings,
                'can_view_analytics': membership.can_view_analytics,
            },
            'iat': timezone.now(),
            'exp': timezone.now() + timedelta(hours=1),
            'iss': settings.SECRET_KEY,
            'aud': 'prowler-multi-tenant'
        }
        
        # Refresh token payload
        refresh_payload = {
            'user_id': str(user.id),
            'tenant_id': str(self.tenant.id),
            'iat': timezone.now(),
            'exp': timezone.now() + timedelta(days=7),
            'iss': settings.SECRET_KEY,
            'aud': 'prowler-multi-tenant'
        }
        
        access_token = generate_secure_token(access_payload, expires_in=3600)
        refresh_token = generate_secure_token(refresh_payload, expires_in=7*24*3600)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
    
    def _get_user_permissions(self, user: User) -> Dict[str, bool]:
        """Get user's permissions in this tenant"""
        try:
            membership = TenantMembership.objects.get(
                user=user,
                tenant=self.tenant,
                is_active=True
            )
            return {
                'can_invite_users': membership.can_invite_users,
                'can_manage_settings': membership.can_manage_settings,
                'can_view_analytics': membership.can_view_analytics,
            }
        except TenantMembership.DoesNotExist:
            return {
                'can_invite_users': False,
                'can_manage_settings': False,
                'can_view_analytics': False,
            }
    
    def refresh_access_token(self, refresh_token: str) -> Tuple[bool, Dict]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: JWT refresh token
        
        Returns:
            Tuple of (success, token_data)
        """
        try:
            # Validate refresh token
            from api.utils.security import validate_token
            payload = validate_token(refresh_token)
            if not payload:
                return False, {'error': 'Invalid refresh token'}
            
            # Check if token belongs to this tenant
            if payload.get('tenant_id') != str(self.tenant.id):
                return False, {'error': 'Token does not belong to this tenant'}
            
            # Get user
            user = User.objects.get(id=payload['user_id'])
            if not user.can_access_tenant(self.tenant.id):
                return False, {'error': 'User no longer has access to this tenant'}
            
            # Generate new access token
            jwt_tokens = self._generate_tenant_jwt(user)
            
            return True, {
                'access_token': jwt_tokens['access_token'],
                'token_type': 'Bearer',
                'expires_in': 3600
            }
            
        except Exception as e:
            logger.error(f"Token refresh failed for tenant {self.tenant.subdomain}: {e}")
            return False, {'error': 'Token refresh failed'}
    
    def validate_tenant_access(self, user: User) -> bool:
        """
        Validate that user has access to this tenant.
        
        Args:
            user: User instance
        
        Returns:
            True if user has access, False otherwise
        """
        return user.can_access_tenant(self.tenant.id)
    
    def get_tenant_config(self) -> Dict[str, Any]:
        """Get tenant's Azure AD configuration (without secrets)"""
        if not self.is_configured():
            return {'configured': False}
        
        return {
            'configured': True,
            'client_id': self.oauth_config.client_id,
            'provider_tenant_id': self.oauth_config.provider_tenant_id,
            'scopes': self.oauth_config.scopes,
            'allowed_domains': self.oauth_config.allowed_domains,
            'auto_create_users': self.oauth_config.auto_create_users,
            'require_email_verification': self.oauth_config.require_email_verification,
            'last_used': self.oauth_config.last_used,
        }
