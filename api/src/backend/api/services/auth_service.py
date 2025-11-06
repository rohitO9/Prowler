"""
Auth Service - Handles OAuth integration, JWT management, and authentication.

This service manages the complete authentication flow including:
- Azure AD OAuth integration
- JWT token generation and validation
- Silent SSO login
- Token refresh and management
- Multi-tenant authentication
"""

import logging
import jwt
import requests
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from api.models import User, Tenant, TenantOAuthConfig, TenantOAuthUser, SecurityAuditLog
from api.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)


class AuthService:
    """Service for managing OAuth authentication and JWT tokens."""
    
    def __init__(self):
        self.audit_log = AuditLogService()
        self.jwt_secret = settings.SECRET_KEY
        self.azure_authority = "https://login.microsoftonline.com"
        self.azure_graph_endpoint = "https://graph.microsoft.com/v1.0"
    
    def initiate_azure_oauth(self, tenant: Tenant, redirect_uri: str, 
                            state: Optional[str] = None) -> str:
        """
        Initiate Azure AD OAuth flow for a tenant.
        
        Args:
            tenant: Tenant to authenticate for
            redirect_uri: Redirect URI after authentication
            state: Optional state parameter for CSRF protection
            
        Returns:
            str: Azure AD authorization URL
        """
        try:
            # Get OAuth configuration for tenant
            oauth_config = TenantOAuthConfig.objects.filter(
                tenant=tenant,
                provider='azure',
                is_active=True
            ).first()
            
            if not oauth_config:
                raise ValidationError("Azure AD OAuth not configured for this tenant")
            
            # Generate state parameter if not provided
            if not state:
                state = self._generate_state_parameter(tenant)
            
            # Build authorization URL
            auth_url = (
                f"{self.azure_authority}/{oauth_config.provider_tenant_id}/oauth2/v2.0/authorize"
                f"?client_id={oauth_config.client_id}"
                f"&response_type=code"
                f"&redirect_uri={redirect_uri}"
                f"&scope={' '.join(oauth_config.scopes)}"
                f"&state={state}"
                f"&response_mode=query"
            )
            
            # Log OAuth initiation
            self.audit_log.log_event(
                event_type='oauth_login',
                message=f"Azure AD OAuth initiated for tenant {tenant.name}",
                tenant=tenant,
                severity='low',
                details={
                    'tenant_id': str(tenant.id),
                    'redirect_uri': redirect_uri,
                    'state': state
                }
            )
            
            logger.info(f"✅ Azure AD OAuth initiated for tenant {tenant.name}")
            return auth_url
            
        except Exception as e:
            logger.error(f"❌ Failed to initiate Azure OAuth: {e}")
            self.audit_log.log_event(
                event_type='oauth_failed',
                message=f"Failed to initiate Azure OAuth: {str(e)}",
                tenant=tenant,
                severity='medium',
                details={'error': str(e), 'redirect_uri': redirect_uri}
            )
            raise
    
    def exchange_azure_code(self, tenant: Tenant, authorization_code: str,
                           redirect_uri: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Exchange Azure AD authorization code for tokens.
        
        Args:
            tenant: Tenant context
            authorization_code: Authorization code from Azure AD
            redirect_uri: Redirect URI used in authorization
            
        Returns:
            Tuple of (success, token_data, error_message)
        """
        try:
            # Get OAuth configuration
            oauth_config = TenantOAuthConfig.objects.filter(
                tenant=tenant,
                provider='azure',
                is_active=True
            ).first()
            
            if not oauth_config:
                return False, None, "Azure AD OAuth not configured for this tenant"
            
            # Prepare token request
            token_url = f"{self.azure_authority}/{oauth_config.provider_tenant_id}/oauth2/v2.0/token"
            
            token_data = {
                'client_id': oauth_config.client_id,
                'client_secret': oauth_config.client_secret,
                'code': authorization_code,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
                'scope': ' '.join(oauth_config.scopes)
            }
            
            # Exchange code for tokens
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            
            token_response = response.json()
            
            # Log successful token exchange
            self.audit_log.log_event(
                event_type='oauth_login',
                message=f"Azure AD tokens obtained for tenant {tenant.name}",
                tenant=tenant,
                severity='low',
                details={
                    'tenant_id': str(tenant.id),
                    'token_type': token_response.get('token_type'),
                    'expires_in': token_response.get('expires_in')
                }
            )
            
            logger.info(f"✅ Azure AD tokens obtained for tenant {tenant.name}")
            return True, token_response, None
            
        except requests.RequestException as e:
            logger.error(f"❌ Failed to exchange Azure code: {e}")
            self.audit_log.log_event(
                event_type='oauth_failed',
                message=f"Failed to exchange Azure code: {str(e)}",
                tenant=tenant,
                severity='medium',
                details={'error': str(e), 'authorization_code': authorization_code[:10] + '...'}
            )
            return False, None, f"Token exchange failed: {str(e)}"
        except Exception as e:
            logger.error(f"❌ Unexpected error in Azure code exchange: {e}")
            return False, None, f"Unexpected error: {str(e)}"
    
    def get_azure_user_info(self, access_token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Get user information from Azure AD using access token.
        
        Args:
            access_token: Azure AD access token
            
        Returns:
            Tuple of (success, user_info, error_message)
        """
        try:
            # Get user info from Microsoft Graph
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.azure_graph_endpoint}/me",
                headers=headers
            )
            response.raise_for_status()
            
            user_info = response.json()
            
            logger.info(f"✅ Retrieved Azure user info for {user_info.get('mail', 'unknown')}")
            return True, user_info, None
            
        except requests.RequestException as e:
            logger.error(f"❌ Failed to get Azure user info: {e}")
            return False, None, f"Failed to get user info: {str(e)}"
        except Exception as e:
            logger.error(f"❌ Unexpected error getting Azure user info: {e}")
            return False, None, f"Unexpected error: {str(e)}"
    
    def create_or_update_oauth_user(self, tenant: Tenant, oauth_config: TenantOAuthConfig,
                                  user_info: Dict[str, Any], tokens: Dict[str, Any]) -> Tuple[bool, Optional[User], Optional[str]]:
        """
        Create or update OAuth user account.
        
        Args:
            tenant: Tenant context
            oauth_config: OAuth configuration
            user_info: User information from OAuth provider
            tokens: OAuth tokens
            
        Returns:
            Tuple of (success, user, error_message)
        """
        try:
            with transaction.atomic():
                # Extract user information
                email = user_info.get('mail') or user_info.get('userPrincipalName')
                if not email:
                    return False, None, "No email found in user info"
                
                provider_user_id = user_info.get('id')
                if not provider_user_id:
                    return False, None, "No user ID found in user info"
                
                # Check if OAuth user already exists
                oauth_user = TenantOAuthUser.objects.filter(
                    tenant=tenant,
                    oauth_config=oauth_config,
                    provider_user_id=provider_user_id
                ).first()
                
                if oauth_user:
                    # Update existing OAuth user
                    oauth_user.provider_email = email
                    oauth_user.update_tokens(
                        access_token=tokens.get('access_token'),
                        refresh_token=tokens.get('refresh_token'),
                        expires_in=tokens.get('expires_in')
                    )
                    oauth_user.update_last_login()
                    
                    user = oauth_user.user
                    logger.info(f"✅ Updated OAuth user {user.email}")
                    
                else:
                    # Check if regular user exists
                    user = User.objects.filter(email=email).first()
                    
                    if not user:
                        # Create new user
                        user = User.objects.create(
                            email=email,
                            username=email,
                            first_name=user_info.get('givenName', ''),
                            last_name=user_info.get('surname', ''),
                            name=user_info.get('displayName', ''),
                            primary_tenant=tenant,
                            is_active=True,
                            is_verified=True,
                            date_joined=timezone.now()
                        )
                        
                        # Create tenant membership
                        from api.services.user_service import UserService
                        user_service = UserService()
                        user_service._set_default_permissions(
                            TenantMembership.objects.create(
                                user=user,
                                tenant=tenant,
                                role='member',
                                is_active=True
                            ),
                            'member'
                        )
                    
                    # Create OAuth user record
                    oauth_user = TenantOAuthUser.objects.create(
                        tenant=tenant,
                        user=user,
                        oauth_config=oauth_config,
                        provider_user_id=provider_user_id,
                        provider_email=email
                    )
                    oauth_user.update_tokens(
                        access_token=tokens.get('access_token'),
                        refresh_token=tokens.get('refresh_token'),
                        expires_in=tokens.get('expires_in')
                    )
                    oauth_user.update_last_login()
                
                # Log OAuth user creation/update
                self.audit_log.log_event(
                    event_type='oauth_login',
                    message=f"OAuth user {user.email} authenticated via {oauth_config.provider}",
                    user=user,
                    tenant=tenant,
                    severity='low',
                    details={
                        'user_id': str(user.id),
                        'oauth_user_id': str(oauth_user.id),
                        'provider': oauth_config.provider,
                        'provider_user_id': provider_user_id
                    }
                )
                
                return True, user, None
                
        except Exception as e:
            logger.error(f"❌ Failed to create/update OAuth user: {e}")
            self.audit_log.log_event(
                event_type='oauth_failed',
                message=f"Failed to create/update OAuth user: {str(e)}",
                tenant=tenant,
                severity='high',
                details={'error': str(e), 'user_info': user_info}
            )
            return False, None, f"Failed to create/update OAuth user: {str(e)}"
    
    def generate_jwt_token(self, user: User, tenant: Tenant, 
                          expires_in: int = 3600) -> str:
        """
        Generate JWT token for user authentication.
        
        Args:
            user: User to generate token for
            tenant: Tenant context
            expires_in: Token expiration time in seconds
            
        Returns:
            str: JWT token
        """
        try:
            # Get user permissions
            from api.services.user_service import UserService
            user_service = UserService()
            permissions = user_service.get_user_permissions(user, tenant)
            
            # Create JWT payload
            payload = {
                'user_id': str(user.id),
                'email': user.email,
                'tenant_id': str(tenant.id),
                'tenant_name': tenant.name,
                'tenant_subdomain': tenant.subdomain,
                'permissions': permissions,
                'exp': int((timezone.now() + timedelta(seconds=expires_in)).timestamp()),
                'iat': int(timezone.now().timestamp()),
                'iss': 'prowler-multi-tenant',
                'aud': 'prowler-users'
            }
            
            # Generate JWT token
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            
            # Log token generation
            self.audit_log.log_event(
                event_type='login_success',
                message=f"JWT token generated for user {user.email}",
                user=user,
                tenant=tenant,
                severity='low',
                details={
                    'user_id': str(user.id),
                    'tenant_id': str(tenant.id),
                    'expires_in': expires_in
                }
            )
            
            logger.info(f"✅ JWT token generated for user {user.email}")
            return token
            
        except Exception as e:
            logger.error(f"❌ Failed to generate JWT token: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to generate JWT token: {str(e)}",
                user=user,
                tenant=tenant,
                severity='high',
                details={'error': str(e)}
            )
            raise
    
    def validate_jwt_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate JWT token and return payload.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Tuple of (is_valid, payload, error_message)
        """
        try:
            # Decode JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # Validate required fields
            required_fields = ['user_id', 'email', 'tenant_id', 'exp', 'iat']
            for field in required_fields:
                if field not in payload:
                    return False, None, f"Missing required field: {field}"
            
            # Check expiration
            if payload['exp'] < int(timezone.now().timestamp()):
                return False, None, "Token has expired"
            
            return True, payload, None
            
        except jwt.ExpiredSignatureError:
            return False, None, "Token has expired"
        except jwt.InvalidTokenError:
            return False, None, "Invalid token"
        except Exception as e:
            logger.error(f"❌ Failed to validate JWT token: {e}")
            return False, None, f"Token validation error: {str(e)}"
    
    def refresh_azure_token(self, oauth_user: TenantOAuthUser) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Refresh Azure AD access token using refresh token.
        
        Args:
            oauth_user: OAuth user record
            
        Returns:
            Tuple of (success, token_data, error_message)
        """
        try:
            # Get OAuth configuration
            oauth_config = oauth_user.oauth_config
            
            # Prepare refresh request
            token_url = f"{self.azure_authority}/{oauth_config.provider_tenant_id}/oauth2/v2.0/token"
            
            token_data = {
                'client_id': oauth_config.client_id,
                'client_secret': oauth_config.client_secret,
                'refresh_token': oauth_user.refresh_token,
                'grant_type': 'refresh_token',
                'scope': ' '.join(oauth_config.scopes)
            }
            
            # Refresh token
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            
            token_response = response.json()
            
            # Update stored tokens
            oauth_user.update_tokens(
                access_token=token_response.get('access_token'),
                refresh_token=token_response.get('refresh_token'),
                expires_in=token_response.get('expires_in')
            )
            
            logger.info(f"✅ Azure token refreshed for user {oauth_user.user.email}")
            return True, token_response, None
            
        except requests.RequestException as e:
            logger.error(f"❌ Failed to refresh Azure token: {e}")
            return False, None, f"Token refresh failed: {str(e)}"
        except Exception as e:
            logger.error(f"❌ Unexpected error refreshing Azure token: {e}")
            return False, None, f"Unexpected error: {str(e)}"
    
    def revoke_azure_token(self, oauth_user: TenantOAuthUser) -> bool:
        """
        Revoke Azure AD access token.
        
        Args:
            oauth_user: OAuth user record
            
        Returns:
            bool: True if token was revoked successfully
        """
        try:
            # Get OAuth configuration
            oauth_config = oauth_user.oauth_config
            
            # Prepare revocation request
            revoke_url = f"{self.azure_authority}/{oauth_config.provider_tenant_id}/oauth2/v2.0/logout"
            
            revoke_data = {
                'client_id': oauth_config.client_id,
                'client_secret': oauth_config.client_secret,
                'token': oauth_user.access_token
            }
            
            # Revoke token
            response = requests.post(revoke_url, data=revoke_data)
            response.raise_for_status()
            
            # Clear stored tokens
            oauth_user.access_token = None
            oauth_user.refresh_token = None
            oauth_user.token_expires_at = None
            oauth_user.save()
            
            logger.info(f"✅ Azure token revoked for user {oauth_user.user.email}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"❌ Failed to revoke Azure token: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error revoking Azure token: {e}")
            return False
    
    def _generate_state_parameter(self, tenant: Tenant) -> str:
        """Generate a secure state parameter for OAuth flow."""
        import secrets
        import hashlib
        
        # Create a unique state parameter
        timestamp = str(int(timezone.now().timestamp()))
        random_data = secrets.token_urlsafe(32)
        tenant_id = str(tenant.id)
        
        # Combine and hash
        combined = f"{tenant_id}:{timestamp}:{random_data}"
        state = hashlib.sha256(combined.encode()).hexdigest()
        
        return state
