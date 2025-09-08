"""
Azure AD Authentication Service
Handles Azure AD OAuth2 flow, token validation, and user management
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

from api.models.azure_rbac import (
    Company, AzureADUserProfile, AzureADTokenCache, 
    UserRoleAssignment, AuditLog, AzureADGroupMapping
)
from api.models.enhanced_role import EnhancedRole

logger = logging.getLogger(__name__)
User = get_user_model()


class AzureADAuthService:
    """
    Service class for Azure AD authentication and user management
    """
    
    def __init__(self, company: Company):
        self.company = company
        self.tenant_id = company.azure_tenant_id
        self.client_id = company.azure_client_id
        self.client_secret = company.azure_client_secret
        self.redirect_uri = company.azure_redirect_uri
        self.scopes = company.azure_scopes or ['openid', 'profile', 'email', 'User.Read']
    
    def get_authorization_url(self, state: str = None) -> str:
        """
        Generate Azure AD authorization URL
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL
        """
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.scopes),
            'response_mode': 'query',
            'state': state or 'default',
            'prompt': 'select_account',
        }
        
        authority_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        auth_url = f"{authority_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        
        return auth_url
    
    def exchange_code_for_token(self, auth_code: str) -> Tuple[bool, Dict]:
        """
        Exchange authorization code for access token
        
        Args:
            auth_code: Authorization code from Azure AD
            
        Returns:
            Tuple of (success, token_data)
        """
        try:
            token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': auth_code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri,
                'scope': ' '.join(self.scopes)
            }
            
            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            
            # Log successful token exchange
            AuditLog.log_action(
                company=self.company,
                action_type='token_refresh',
                action_description='Authorization code exchanged for token',
                success=True,
                details={'token_type': token_data.get('token_type')}
            )
            
            return True, token_data
            
        except requests.RequestException as e:
            logger.error(f"Token exchange failed for company {self.company.name}: {str(e)}")
            
            AuditLog.log_action(
                company=self.company,
                action_type='error',
                action_description='Token exchange failed',
                success=False,
                error_message=str(e)
            )
            
            return False, {'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error during token exchange: {str(e)}")
            return False, {'error': 'Token exchange failed'}
    
    def validate_token(self, token: str) -> Tuple[bool, Dict]:
        """
        Validate Azure AD token
        
        Args:
            token: JWT token from Azure AD
            
        Returns:
            Tuple of (is_valid, token_data)
        """
        try:
            # Decode token without verification first to get header
            header = jwt.get_unverified_header(token)
            kid = header.get('kid')
            
            if not kid:
                return False, {'error': 'No key ID in token header'}
            
            # Get public keys from Azure AD
            keys_url = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
            response = requests.get(keys_url, timeout=30)
            response.raise_for_status()
            
            keys_data = response.json()
            public_key = None
            
            # Find the matching key
            for key in keys_data.get('keys', []):
                if key.get('kid') == kid:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break
            
            if not public_key:
                return False, {'error': 'Public key not found for token'}
            
            # Verify and decode token
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
            )
            
            return True, decoded
            
        except jwt.ExpiredSignatureError:
            return False, {'error': 'Token has expired'}
        except jwt.InvalidTokenError as e:
            return False, {'error': f'Invalid token: {str(e)}'}
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return False, {'error': 'Token validation failed'}
    
    def get_user_info(self, access_token: str) -> Tuple[bool, Dict]:
        """
        Get user information from Azure AD
        
        Args:
            access_token: Azure AD access token
            
        Returns:
            Tuple of (success, user_info)
        """
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            user_info = response.json()
            
            # Validate email domain
            email = user_info.get('mail') or user_info.get('userPrincipalName')
            if email and not self._is_domain_allowed(email):
                return False, {'error': f'Domain not allowed: {email.split("@")[1]}'}
            
            return True, user_info
            
        except requests.RequestException as e:
            logger.error(f"Failed to get user info: {str(e)}")
            return False, {'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error getting user info: {str(e)}")
            return False, {'error': 'Failed to get user information'}
    
    def get_user_groups(self, access_token: str) -> List[Dict]:
        """
        Get user groups from Azure AD
        
        Args:
            access_token: Azure AD access token
            
        Returns:
            List of group information
        """
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                'https://graph.microsoft.com/v1.0/me/memberOf',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json().get('value', [])
            
        except requests.RequestException as e:
            logger.error(f"Failed to get user groups: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting user groups: {str(e)}")
            return []
    
    def create_or_update_user(self, user_info: Dict, access_token: str) -> Tuple[bool, User]:
        """
        Create or update user based on Azure AD information
        
        Args:
            user_info: User information from Azure AD
            access_token: Azure AD access token
            
        Returns:
            Tuple of (success, user)
        """
        try:
            with transaction.atomic():
                azure_id = user_info.get('id')
                email = user_info.get('mail') or user_info.get('userPrincipalName')
                
                if not email:
                    return False, None
                
                # Find or create user
                user = User.objects.filter(email=email).first()
                
                if not user:
                    # Create new user
                    display_name = user_info.get('displayName', '')
                    if not display_name:
                        given = user_info.get('givenName', '')
                        surname = user_info.get('surname', '')
                        display_name = f"{given} {surname}".strip() or email.split('@')[0]
                    
                    # Generate random password for Azure AD users
                    from django.contrib.auth.hashers import make_password
                    import secrets
                    random_password = secrets.token_urlsafe(32)
                    
                    user = User.objects.create(
                        email=email,
                        name=display_name,
                        is_active=True,
                        password=make_password(random_password),
                    )
                    
                    # Start trial for new users
                    user.start_trial(days=7)
                    
                    AuditLog.log_action(
                        user=user,
                        company=self.company,
                        action_type='login',
                        action_description='New user created from Azure AD',
                        success=True,
                        details={'azure_id': azure_id, 'email': email}
                    )
                
                # Create or update Azure AD profile
                profile, created = AzureADUserProfile.objects.get_or_create(
                    user=user,
                    company=self.company,
                    defaults={
                        'azure_ad_id': azure_id,
                        'azure_ad_object_id': user_info.get('id'),
                        'job_title': user_info.get('jobTitle', ''),
                        'department': user_info.get('department', ''),
                        'office_location': user_info.get('officeLocation', ''),
                        'business_phones': user_info.get('businessPhones', []),
                        'mobile_phone': user_info.get('mobilePhone', ''),
                        'preferred_language': user_info.get('preferredLanguage', ''),
                        'photo_url': user_info.get('photo', ''),
                        'sync_status': 'success'
                    }
                )
                
                if not created:
                    # Update existing profile
                    profile.azure_ad_id = azure_id
                    profile.azure_ad_object_id = user_info.get('id')
                    profile.job_title = user_info.get('jobTitle', '')
                    profile.department = user_info.get('department', '')
                    profile.office_location = user_info.get('officeLocation', '')
                    profile.business_phones = user_info.get('businessPhones', [])
                    profile.mobile_phone = user_info.get('mobilePhone', '')
                    profile.preferred_language = user_info.get('preferredLanguage', '')
                    profile.photo_url = user_info.get('photo', '')
                    profile.sync_status = 'success'
                    profile.save()
                
                # Cache tokens
                self._cache_tokens(user, access_token, user_info)
                
                # Sync user groups and roles
                self._sync_user_groups(user, access_token)
                
                return True, user
                
        except Exception as e:
            logger.error(f"Failed to create/update user: {str(e)}")
            return False, None
    
    def _is_domain_allowed(self, email: str) -> bool:
        """Check if email domain is allowed for this company"""
        if not self.company.azure_allowed_domains:
            return True
        
        domain = email.split('@')[1] if '@' in email else ''
        return domain in self.company.azure_allowed_domains
    
    def _cache_tokens(self, user: User, access_token: str, user_info: Dict):
        """Cache Azure AD tokens for the user"""
        try:
            # Calculate expiration time
            expires_in = user_info.get('expires_in', 3600)
            expires_at = timezone.now() + timedelta(seconds=expires_in)
            
            # Create or update token cache
            token_cache, created = AzureADTokenCache.objects.get_or_create(
                user=user,
                company=self.company,
                defaults={
                    'access_token': access_token,
                    'refresh_token': user_info.get('refresh_token', ''),
                    'id_token': user_info.get('id_token', ''),
                    'token_type': user_info.get('token_type', 'Bearer'),
                    'scope': ' '.join(self.scopes),
                    'expires_at': expires_at
                }
            )
            
            if not created:
                token_cache.access_token = access_token
                token_cache.refresh_token = user_info.get('refresh_token', '')
                token_cache.id_token = user_info.get('id_token', '')
                token_cache.expires_at = expires_at
                token_cache.save()
                
        except Exception as e:
            logger.error(f"Failed to cache tokens: {str(e)}")
    
    def _sync_user_groups(self, user: User, access_token: str):
        """Sync user groups from Azure AD and assign roles"""
        try:
            groups = self.get_user_groups(access_token)
            
            # Update Azure groups in profile
            profile = user.azure_profile.filter(company=self.company).first()
            if profile:
                profile.azure_groups = groups
                profile.save()
            
            # Clear existing role assignments for this company
            UserRoleAssignment.objects.filter(
                user=user,
                company=self.company,
                assignment_source='azure_group'
            ).delete()
            
            # Map Azure groups to roles
            for group in groups:
                group_id = group.get('id')
                
                # Find group mapping
                group_mapping = AzureADGroupMapping.objects.filter(
                    company=self.company,
                    azure_group_id=group_id,
                    is_active=True
                ).first()
                
                if group_mapping:
                    # Assign role to user
                    UserRoleAssignment.objects.get_or_create(
                        user=user,
                        role=group_mapping.role,
                        company=self.company,
                        defaults={
                            'assignment_source': 'azure_group',
                            'source_reference': group_id,
                            'is_active': True
                        }
                    )
            
            # If no roles assigned, assign default role
            if not UserRoleAssignment.objects.filter(
                user=user,
                company=self.company,
                is_active=True
            ).exists():
                default_role = EnhancedRole.objects.filter(
                    tenant_id=self.company.id,
                    is_default=True,
                    is_active=True
                ).first()
                
                if default_role:
                    UserRoleAssignment.objects.create(
                        user=user,
                        role=default_role,
                        company=self.company,
                        assignment_source='default',
                        is_active=True
                    )
            
            AuditLog.log_action(
                user=user,
                company=self.company,
                action_type='group_sync',
                action_description='User groups synced from Azure AD',
                success=True,
                details={'groups_count': len(groups)}
            )
            
        except Exception as e:
            logger.error(f"Failed to sync user groups: {str(e)}")
            
            AuditLog.log_action(
                user=user,
                company=self.company,
                action_type='group_sync',
                action_description='User groups sync failed',
                success=False,
                error_message=str(e)
            )
    
    def refresh_access_token(self, refresh_token: str) -> Tuple[bool, Dict]:
        """
        Refresh Azure AD access token
        
        Args:
            refresh_token: Azure AD refresh token
            
        Returns:
            Tuple of (success, new_token_data)
        """
        try:
            token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
                'scope': ' '.join(self.scopes)
            }
            
            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()
            
            return True, response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to refresh token: {str(e)}")
            return False, {'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error refreshing token: {str(e)}")
            return False, {'error': 'Token refresh failed'}
    
    def authenticate_user(self, auth_code: str) -> Tuple[bool, Dict]:
        """
        Complete authentication flow for a user
        
        Args:
            auth_code: Authorization code from Azure AD
            
        Returns:
            Tuple of (success, auth_result)
        """
        try:
            # Exchange code for token
            success, token_data = self.exchange_code_for_token(auth_code)
            if not success:
                return False, token_data
            
            access_token = token_data.get('access_token')
            if not access_token:
                return False, {'error': 'No access token received'}
            
            # Get user info
            success, user_info = self.get_user_info(access_token)
            if not success:
                return False, user_info
            
            # Create or update user
            success, user = self.create_or_update_user(user_info, access_token)
            if not success:
                return False, {'error': 'Failed to create/update user'}
            
            # Generate JWT tokens for our application
            from rest_framework_simplejwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)
            access_token_jwt = refresh.access_token
            
            # Add company context to JWT
            access_token_jwt['company_id'] = str(self.company.id)
            access_token_jwt['company_name'] = self.company.name
            access_token_jwt['azure_tenant_id'] = self.tenant_id
            
            # Add user roles to JWT
            user_roles = UserRoleAssignment.objects.filter(
                user=user,
                company=self.company,
                is_active=True
            ).select_related('role')
            
            access_token_jwt['roles'] = [str(role.role.id) for role in user_roles]
            access_token_jwt['permissions'] = []
            
            for role_assignment in user_roles:
                role_permissions = role_assignment.role.get_permissions()
                access_token_jwt['permissions'].extend([p.name for p in role_permissions])
            
            # Remove duplicates
            access_token_jwt['permissions'] = list(set(access_token_jwt['permissions']))
            
            # Log successful authentication
            AuditLog.log_action(
                user=user,
                company=self.company,
                action_type='login',
                action_description='User authenticated via Azure AD',
                success=True,
                details={
                    'azure_id': user_info.get('id'),
                    'email': user_info.get('mail') or user_info.get('userPrincipalName')
                }
            )
            
            return True, {
                'user': user,
                'access_token': str(access_token_jwt),
                'refresh_token': str(refresh),
                'company': self.company,
                'azure_user_info': user_info
            }
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False, {'error': 'Authentication failed'}


class AzureADRBACManager:
    """
    Manager class for Azure AD RBAC operations
    """
    
    @staticmethod
    def create_company_with_azure_config(
        name: str,
        domain: str,
        azure_tenant_id: str,
        azure_client_id: str,
        azure_client_secret: str,
        azure_redirect_uri: str,
        created_by: User = None
    ) -> Company:
        """
        Create a new company with Azure AD configuration
        
        Args:
            name: Company name
            domain: Primary email domain
            azure_tenant_id: Azure AD Tenant ID
            azure_client_id: Azure AD Application Client ID
            azure_client_secret: Azure AD Client Secret
            azure_redirect_uri: Azure AD Redirect URI
            created_by: User who created the company
            
        Returns:
            Created Company instance
        """
        try:
            with transaction.atomic():
                # Create company
                company = Company.objects.create(
                    name=name,
                    domain=domain,
                    azure_tenant_id=azure_tenant_id,
                    azure_client_id=azure_client_id,
                    azure_client_secret=azure_client_secret,
                    azure_redirect_uri=azure_redirect_uri,
                    azure_scopes=['openid', 'profile', 'email', 'User.Read'],
                    azure_allowed_domains=[domain],
                    created_by=created_by
                )
                
                # Create default roles for the company
                EnhancedRole.create_default_roles(company.id)
                
                # Log company creation
                AuditLog.log_action(
                    user=created_by,
                    company=company,
                    action_type='company_created',
                    action_description=f'Company {name} created with Azure AD integration',
                    success=True,
                    details={
                        'domain': domain,
                        'azure_tenant_id': azure_tenant_id
                    }
                )
                
                return company
                
        except Exception as e:
            logger.error(f"Failed to create company: {str(e)}")
            raise
    
    @staticmethod
    def sync_azure_groups_to_roles(company: Company, access_token: str) -> bool:
        """
        Sync Azure AD groups to application roles
        
        Args:
            company: Company instance
            access_token: Azure AD access token
            
        Returns:
            True if sync was successful
        """
        try:
            auth_service = AzureADAuthService(company)
            groups = auth_service.get_user_groups(access_token)
            
            synced_count = 0
            for group in groups:
                group_id = group.get('id')
                group_name = group.get('displayName', '')
                
                # Check if mapping already exists
                existing_mapping = AzureADGroupMapping.objects.filter(
                    company=company,
                    azure_group_id=group_id
                ).first()
                
                if not existing_mapping:
                    # Create new role for this group
                    role = EnhancedRole.objects.create(
                        tenant_id=company.id,
                        name=f"azure_{group_id[:8]}",
                        display_name=group_name,
                        description=f"Role synced from Azure AD group: {group_name}",
                        role_type='azure_sync',
                        azure_group_id=group_id,
                        azure_group_name=group_name,
                        auto_sync_from_azure=True
                    )
                    
                    # Create group mapping
                    AzureADGroupMapping.objects.create(
                        company=company,
                        azure_group_id=group_id,
                        azure_group_name=group_name,
                        azure_group_description=group.get('description', ''),
                        role=role
                    )
                    
                    synced_count += 1
            
            AuditLog.log_action(
                company=company,
                action_type='group_sync',
                action_description=f'Synced {synced_count} Azure AD groups to roles',
                success=True,
                details={'groups_synced': synced_count}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync Azure groups: {str(e)}")
            
            AuditLog.log_action(
                company=company,
                action_type='group_sync',
                action_description='Azure AD group sync failed',
                success=False,
                error_message=str(e)
            )
            
            return False
