"""
Azure AD Utility Functions
"""

import logging
import requests
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response

from api.models import User, Tenant
from api.v1.models import Role

logger = logging.getLogger(__name__)
User = get_user_model()


class AzureADUtils:
    """Utility class for Azure AD operations"""

    @staticmethod
    def validate_token(token: str) -> Tuple[bool, Dict]:
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
            
            # Get the key ID from header
            kid = header.get('kid')
            if not kid:
                return False, {'error': 'No key ID in token header'}

            # Get public keys from Azure AD
            keys_url = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/discovery/v2.0/keys"
            response = requests.get(keys_url)
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
                audience=settings.AZURE_AD_CLIENT_ID,
                issuer=f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/v2.0"
            )
            
            return True, decoded
            
        except jwt.ExpiredSignatureError:
            return False, {'error': 'Token has expired'}
        except jwt.InvalidTokenError as e:
            return False, {'error': f'Invalid token: {str(e)}'}
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return False, {'error': 'Token validation failed'}

    @staticmethod
    def get_user_groups(access_token: str) -> List[Dict]:
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
                f'{settings.AZURE_AD_GRAPH_API_BASE_URL}/v1.0/me/memberOf',
                headers=headers
            )
            response.raise_for_status()
            
            return response.json().get('value', [])
            
        except requests.RequestException as e:
            logger.error(f"Failed to get user groups: {str(e)}")
            return []

    @staticmethod
    def sync_user_groups(user: User, access_token: str) -> bool:
        """
        Sync user groups from Azure AD to local roles
        
        Args:
            user: User object
            access_token: Azure AD access token
            
        Returns:
            True if sync was successful
        """
        try:
            if not settings.AZURE_AD_SYNC_GROUPS:
                return True
                
            groups = AzureADUtils.get_user_groups(access_token)
            
            # Clear existing roles
            user.roles.clear()
            
            # Map Azure AD groups to local roles
            for group in groups:
                group_id = group.get('id')
                
                # Check if group maps to admin role
                if group_id == settings.AZURE_AD_GROUP_MAPPING.get('admin_group_id'):
                    admin_role = Role.objects.filter(name='admin').first()
                    if admin_role:
                        user.roles.add(admin_role)
                
                # Check if group maps to user role
                elif group_id == settings.AZURE_AD_GROUP_MAPPING.get('user_group_id'):
                    user_role = Role.objects.filter(name='user').first()
                    if user_role:
                        user.roles.add(user_role)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync user groups: {str(e)}")
            return False

    @staticmethod
    def validate_domain(email: str) -> bool:
        """
        Validate if email domain is allowed
        
        Args:
            email: User email address
            
        Returns:
            True if domain is allowed
        """
        if not settings.AZURE_AD_ALLOWED_DOMAINS:
            return True
            
        domain = email.split('@')[1] if '@' in email else ''
        return domain in settings.AZURE_AD_ALLOWED_DOMAINS

    @staticmethod
    def create_user_from_azure_info(user_info: Dict) -> Optional[User]:
        """
        Create user from Azure AD information
        
        Args:
            user_info: User information from Azure AD
            
        Returns:
            User object or None
        """
        try:
            azure_id = user_info.get('id')
            email = user_info.get('mail') or user_info.get('userPrincipalName')
            
            if not email:
                logger.error("No email found in Azure AD user info")
                return None
            
            # Validate domain
            if not AzureADUtils.validate_domain(email):
                logger.error(f"Domain not allowed for email: {email}")
                return None
            
            # Check if user already exists
            user = User.objects.filter(
                azure_ad_id=azure_id
            ).first() or User.objects.filter(
                email=email
            ).first()
            
            if user:
                # Update Azure AD ID if not set
                if not user.azure_ad_id:
                    user.azure_ad_id = azure_id
                    user.save()
                return user
            
            # Create new user
            user = User.objects.create(
                email=email,
                azure_ad_id=azure_id,
                first_name=user_info.get('givenName', ''),
                last_name=user_info.get('surname', ''),
                is_active=True,
                email_verified=True
            )
            
            return user
            
        except Exception as e:
            logger.error(f"Failed to create user from Azure info: {str(e)}")
            return None

    @staticmethod
    def get_tenant_from_azure_groups(access_token: str) -> Optional[Tenant]:
        """
        Get tenant based on Azure AD groups
        
        Args:
            access_token: Azure AD access token
            
        Returns:
            Tenant object or None
        """
        try:
            groups = AzureADUtils.get_user_groups(access_token)
            
            for group in groups:
                group_id = group.get('id')
                group_name = group.get('displayName', '').lower()
                
                # Look for tenant-specific groups
                if 'tenant' in group_name or 'prowler' in group_name:
                    # Try to find tenant by group ID or name
                    tenant = Tenant.objects.filter(
                        azure_group_id=group_id
                    ).first() or Tenant.objects.filter(
                        name__icontains=group_name
                    ).first()
                    
                    if tenant:
                        return tenant
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get tenant from Azure groups: {str(e)}")
            return None

    @staticmethod
    def refresh_access_token(refresh_token: str) -> Optional[Dict]:
        """
        Refresh Azure AD access token
        
        Args:
            refresh_token: Azure AD refresh token
            
        Returns:
            New token data or None
        """
        try:
            token_url = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/oauth2/v2.0/token"
            
            data = {
                'client_id': settings.AZURE_AD_CLIENT_ID,
                'client_secret': settings.AZURE_AD_CLIENT_SECRET,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token',
                'scope': ' '.join(settings.AZURE_AD_SCOPES)
            }
            
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Failed to refresh token: {str(e)}")
            return None

    @staticmethod
    def get_user_photo(access_token: str) -> Optional[str]:
        """
        Get user profile photo from Azure AD
        
        Args:
            access_token: Azure AD access token
            
        Returns:
            Photo URL or None
        """
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                f'{settings.AZURE_AD_GRAPH_API_BASE_URL}/v1.0/me/photo/$value',
                headers=headers
            )
            
            if response.status_code == 200:
                # Convert to base64 or return URL
                return f"data:image/jpeg;base64,{response.content.decode('base64')}"
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user photo: {str(e)}")
            return None 