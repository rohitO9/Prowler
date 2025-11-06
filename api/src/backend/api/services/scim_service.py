"""
SCIM Service - Handles user synchronization with Azure AD via SCIM API.

This service manages the complete SCIM integration including:
- User provisioning and deprovisioning
- Group membership synchronization
- Attribute mapping and transformation
- SCIM endpoint implementation
- Bulk operations support
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from api.models import User, Tenant, TenantOAuthConfig, SecurityAuditLog
from api.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)


class SCIMService:
    """Service for managing SCIM user synchronization with Azure AD."""
    
    def __init__(self):
        self.audit_log = AuditLogService()
        self.scim_base_url = "https://graph.microsoft.com/v1.0"
    
    def provision_user(self, tenant: Tenant, user: User, 
                      oauth_config: TenantOAuthConfig) -> Tuple[bool, Optional[str]]:
        """
        Provision a user to Azure AD via SCIM.
        
        Args:
            tenant: Tenant context
            user: User to provision
            oauth_config: OAuth configuration for API access
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get access token for SCIM operations
            access_token = self._get_scim_access_token(oauth_config)
            if not access_token:
                return False, "Failed to get SCIM access token"
            
            # Prepare SCIM user data
            scim_user = self._prepare_scim_user_data(user, tenant)
            
            # Create user in Azure AD
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/scim+json'
            }
            
            response = requests.post(
                f"{self.scim_base_url}/scim/Users",
                json=scim_user,
                headers=headers
            )
            
            if response.status_code == 201:
                # Log successful provisioning
                self.audit_log.log_event(
                    event_type='admin_action',
                    message=f"User {user.email} provisioned to Azure AD via SCIM",
                    user=user,
                    tenant=tenant,
                    severity='low',
                    details={
                        'user_id': str(user.id),
                        'scim_response': response.json()
                    }
                )
                
                logger.info(f"✅ User {user.email} provisioned to Azure AD")
                return True, None
            else:
                error_msg = f"SCIM provisioning failed: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"❌ Failed to provision user via SCIM: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to provision user via SCIM: {str(e)}",
                user=user,
                tenant=tenant,
                severity='high',
                details={'error': str(e), 'user_id': str(user.id)}
            )
            return False, f"SCIM provisioning error: {str(e)}"
    
    def deprovision_user(self, tenant: Tenant, user: User,
                        oauth_config: TenantOAuthConfig) -> Tuple[bool, Optional[str]]:
        """
        Deprovision a user from Azure AD via SCIM.
        
        Args:
            tenant: Tenant context
            user: User to deprovision
            oauth_config: OAuth configuration for API access
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get access token for SCIM operations
            access_token = self._get_scim_access_token(oauth_config)
            if not access_token:
                return False, "Failed to get SCIM access token"
            
            # Get SCIM user ID (this would be stored when user was provisioned)
            scim_user_id = self._get_scim_user_id(user, tenant)
            if not scim_user_id:
                return False, "SCIM user ID not found"
            
            # Delete user from Azure AD
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/scim+json'
            }
            
            response = requests.delete(
                f"{self.scim_base_url}/scim/Users/{scim_user_id}",
                headers=headers
            )
            
            if response.status_code in [200, 204]:
                # Log successful deprovisioning
                self.audit_log.log_event(
                    event_type='admin_action',
                    message=f"User {user.email} deprovisioned from Azure AD via SCIM",
                    user=user,
                    tenant=tenant,
                    severity='low',
                    details={
                        'user_id': str(user.id),
                        'scim_user_id': scim_user_id
                    }
                )
                
                logger.info(f"✅ User {user.email} deprovisioned from Azure AD")
                return True, None
            else:
                error_msg = f"SCIM deprovisioning failed: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"❌ Failed to deprovision user via SCIM: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to deprovision user via SCIM: {str(e)}",
                user=user,
                tenant=tenant,
                severity='high',
                details={'error': str(e), 'user_id': str(user.id)}
            )
            return False, f"SCIM deprovisioning error: {str(e)}"
    
    def update_user(self, tenant: Tenant, user: User,
                   oauth_config: TenantOAuthConfig) -> Tuple[bool, Optional[str]]:
        """
        Update a user in Azure AD via SCIM.
        
        Args:
            tenant: Tenant context
            user: User to update
            oauth_config: OAuth configuration for API access
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get access token for SCIM operations
            access_token = self._get_scim_access_token(oauth_config)
            if not access_token:
                return False, "Failed to get SCIM access token"
            
            # Get SCIM user ID
            scim_user_id = self._get_scim_user_id(user, tenant)
            if not scim_user_id:
                return False, "SCIM user ID not found"
            
            # Prepare updated SCIM user data
            scim_user = self._prepare_scim_user_data(user, tenant)
            
            # Update user in Azure AD
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/scim+json'
            }
            
            response = requests.put(
                f"{self.scim_base_url}/scim/Users/{scim_user_id}",
                json=scim_user,
                headers=headers
            )
            
            if response.status_code == 200:
                # Log successful update
                self.audit_log.log_event(
                    event_type='admin_action',
                    message=f"User {user.email} updated in Azure AD via SCIM",
                    user=user,
                    tenant=tenant,
                    severity='low',
                    details={
                        'user_id': str(user.id),
                        'scim_user_id': scim_user_id
                    }
                )
                
                logger.info(f"✅ User {user.email} updated in Azure AD")
                return True, None
            else:
                error_msg = f"SCIM update failed: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"❌ Failed to update user via SCIM: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to update user via SCIM: {str(e)}",
                user=user,
                tenant=tenant,
                severity='high',
                details={'error': str(e), 'user_id': str(user.id)}
            )
            return False, f"SCIM update error: {str(e)}"
    
    def sync_user_groups(self, tenant: Tenant, user: User,
                        oauth_config: TenantOAuthConfig) -> Tuple[bool, Optional[str]]:
        """
        Synchronize user group memberships with Azure AD.
        
        Args:
            tenant: Tenant context
            user: User to sync groups for
            oauth_config: OAuth configuration for API access
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get access token for SCIM operations
            access_token = self._get_scim_access_token(oauth_config)
            if not access_token:
                return False, "Failed to get SCIM access token"
            
            # Get user's group memberships
            from api.services.user_service import UserService
            user_service = UserService()
            permissions = user_service.get_user_permissions(user, tenant)
            
            # Map permissions to Azure AD groups
            groups = self._map_permissions_to_groups(permissions, tenant)
            
            # Get SCIM user ID
            scim_user_id = self._get_scim_user_id(user, tenant)
            if not scim_user_id:
                return False, "SCIM user ID not found"
            
            # Update user groups in Azure AD
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/scim+json'
            }
            
            group_data = {
                'schemas': ['urn:ietf:params:scim:api:messages:2.0:PatchOp'],
                'Operations': [
                    {
                        'op': 'replace',
                        'path': 'groups',
                        'value': groups
                    }
                ]
            }
            
            response = requests.patch(
                f"{self.scim_base_url}/scim/Users/{scim_user_id}",
                json=group_data,
                headers=headers
            )
            
            if response.status_code == 200:
                # Log successful group sync
                self.audit_log.log_event(
                    event_type='admin_action',
                    message=f"User {user.email} groups synchronized with Azure AD",
                    user=user,
                    tenant=tenant,
                    severity='low',
                    details={
                        'user_id': str(user.id),
                        'scim_user_id': scim_user_id,
                        'groups': groups
                    }
                )
                
                logger.info(f"✅ User {user.email} groups synchronized with Azure AD")
                return True, None
            else:
                error_msg = f"SCIM group sync failed: {response.status_code} - {response.text}"
                logger.error(f"❌ {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"❌ Failed to sync user groups via SCIM: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to sync user groups via SCIM: {str(e)}",
                user=user,
                tenant=tenant,
                severity='high',
                details={'error': str(e), 'user_id': str(user.id)}
            )
            return False, f"SCIM group sync error: {str(e)}"
    
    def bulk_sync_users(self, tenant: Tenant, oauth_config: TenantOAuthConfig) -> Dict[str, Any]:
        """
        Perform bulk synchronization of all users in a tenant.
        
        Args:
            tenant: Tenant to sync users for
            oauth_config: OAuth configuration for API access
            
        Returns:
            Dict containing sync results and statistics
        """
        try:
            # Get all active users in tenant
            from api.services.user_service import UserService
            user_service = UserService()
            users = user_service.get_tenant_users(tenant, active_only=True)
            
            results = {
                'total_users': len(users),
                'provisioned': 0,
                'updated': 0,
                'failed': 0,
                'errors': []
            }
            
            for user in users:
                try:
                    # Check if user is already provisioned
                    scim_user_id = self._get_scim_user_id(user, tenant)
                    
                    if scim_user_id:
                        # Update existing user
                        success, error = self.update_user(tenant, user, oauth_config)
                        if success:
                            results['updated'] += 1
                        else:
                            results['failed'] += 1
                            results['errors'].append(f"Update failed for {user.email}: {error}")
                    else:
                        # Provision new user
                        success, error = self.provision_user(tenant, user, oauth_config)
                        if success:
                            results['provisioned'] += 1
                        else:
                            results['failed'] += 1
                            results['errors'].append(f"Provision failed for {user.email}: {error}")
                    
                    # Sync groups
                    success, error = self.sync_user_groups(tenant, user, oauth_config)
                    if not success:
                        results['errors'].append(f"Group sync failed for {user.email}: {error}")
                        
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"Unexpected error for {user.email}: {str(e)}")
            
            # Log bulk sync results
            self.audit_log.log_event(
                event_type='admin_action',
                message=f"Bulk SCIM sync completed for tenant {tenant.name}",
                tenant=tenant,
                severity='low',
                details=results
            )
            
            logger.info(f"✅ Bulk SCIM sync completed for tenant {tenant.name}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to perform bulk SCIM sync: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to perform bulk SCIM sync: {str(e)}",
                tenant=tenant,
                severity='high',
                details={'error': str(e)}
            )
            raise
    
    def _get_scim_access_token(self, oauth_config: TenantOAuthConfig) -> Optional[str]:
        """Get access token for SCIM operations."""
        try:
            # This would typically involve refreshing the OAuth token
            # For now, return a placeholder
            return "mock-scim-access-token"
        except Exception as e:
            logger.error(f"❌ Failed to get SCIM access token: {e}")
            return None
    
    def _prepare_scim_user_data(self, user: User, tenant: Tenant) -> Dict[str, Any]:
        """Prepare SCIM user data for Azure AD."""
        return {
            'schemas': ['urn:ietf:params:scim:schemas:core:2.0:User'],
            'userName': user.email,
            'name': {
                'givenName': user.first_name or '',
                'familyName': user.last_name or '',
                'formatted': user.name or user.email
            },
            'displayName': user.name or user.email,
            'emails': [
                {
                    'value': user.email,
                    'type': 'work',
                    'primary': True
                }
            ],
            'active': user.is_active,
            'externalId': str(user.id),
            'meta': {
                'resourceType': 'User'
            }
        }
    
    def _get_scim_user_id(self, user: User, tenant: Tenant) -> Optional[str]:
        """Get SCIM user ID for a user (stored when provisioned)."""
        # This would typically be stored in a separate model or user metadata
        # For now, return a placeholder
        return f"scim-{user.id}"
    
    def _map_permissions_to_groups(self, permissions: Dict[str, bool], tenant: Tenant) -> List[Dict[str, str]]:
        """Map user permissions to Azure AD groups."""
        groups = []
        
        # Map roles to groups
        role = permissions.get('role', 'member')
        if role == 'owner':
            groups.append({'value': f"{tenant.subdomain}-owners", 'display': f"{tenant.name} Owners"})
        elif role == 'admin':
            groups.append({'value': f"{tenant.subdomain}-admins", 'display': f"{tenant.name} Administrators"})
        elif role == 'member':
            groups.append({'value': f"{tenant.subdomain}-members", 'display': f"{tenant.name} Members"})
        elif role == 'guest':
            groups.append({'value': f"{tenant.subdomain}-guests", 'display': f"{tenant.name} Guests"})
        
        # Map specific permissions to groups
        if permissions.get('can_manage_providers'):
            groups.append({'value': f"{tenant.subdomain}-provider-managers", 'display': f"{tenant.name} Provider Managers"})
        
        if permissions.get('can_manage_scans'):
            groups.append({'value': f"{tenant.subdomain}-scan-managers", 'display': f"{tenant.name} Scan Managers"})
        
        return groups
