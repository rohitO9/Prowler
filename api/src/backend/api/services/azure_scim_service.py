"""
Azure SCIM Service - Handles user synchronization with Azure AD via SCIM API
"""

import logging
import requests
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from api.models import User, Tenant, TenantMembership
from api.v1.models.azure_sso import AzureSSOConfig, AzureUserSync, AzureADAuditLog
from api.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)


class AzureSCIMService:
    """Service for managing SCIM user synchronization with Azure AD."""
    
    def __init__(self, tenant: Tenant):
        self.tenant = tenant
        try:
            self.sso_config = tenant.azure_sso_config
        except AzureSSOConfig.DoesNotExist:
            raise ValueError(f"Azure SSO not configured for tenant {tenant.name}")
        
        self.audit_log = AuditLogService()
    
    def handle_user_create(self, scim_user_data: Dict[str, Any]) -> User:
        """
        Handle SCIM user creation from Azure AD
        
        Args:
            scim_user_data: SCIM user data from Azure AD
            
        Returns:
            Created User object
        """
        try:
            # Extract user data from SCIM format
            azure_id = scim_user_data.get('id')
            email = scim_user_data.get('userName')
            first_name = scim_user_data.get('name', {}).get('givenName', '')
            last_name = scim_user_data.get('name', {}).get('familyName', '')
            department = scim_user_data.get('department', '')
            job_title = scim_user_data.get('title', '')
            active = scim_user_data.get('active', True)
            
            # Determine role from Azure AD groups
            groups = scim_user_data.get('groups', [])
            role = self._determine_role_from_groups(groups)
            
            with transaction.atomic():
                # Create user
                user = User.objects.create(
                    azure_id=azure_id,
                    azure_tenant_id=self.sso_config.azure_tenant_id,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    department=department,
                    job_title=job_title,
                    is_sso_user=True,
                    is_active=active,
                    primary_tenant=self.tenant
                )
                
                # Create tenant membership
                membership = TenantMembership.objects.create(
                    user=user,
                    tenant=self.tenant,
                    role=role,
                    is_active=active
                )
                
                # Set permissions based on role
                self._set_role_permissions(membership, role)
                
                # Log sync event
                AzureUserSync.objects.create(
                    tenant=self.tenant,
                    user=user,
                    azure_user_id=azure_id,
                    azure_user_data=scim_user_data,
                    action='created',
                    status='success'
                )
                
                # Log audit event
                AzureADAuditLog.log_event(
                    tenant=self.tenant,
                    user=user,
                    event_type='AZURE_USER_SYNCED',
                    description=f'User {email} synced from Azure AD',
                    details={'azure_id': azure_id, 'role': role}
                )
                
                logger.info(f"Created user {email} for tenant {self.tenant.name}")
                return user
                
        except Exception as e:
            logger.error(f"Failed to create user from SCIM data: {e}")
            raise
    
    def handle_user_update(self, azure_user_id: str, scim_user_data: Dict[str, Any]) -> User:
        """
        Handle SCIM user update from Azure AD
        
        Args:
            azure_user_id: Azure AD user ID
            scim_user_data: SCIM user data from Azure AD
            
        Returns:
            Updated User object
        """
        try:
            user = User.objects.get(azure_id=azure_user_id, primary_tenant=self.tenant)
            
            # Track changes
            changes = {}
            if 'name' in scim_user_data:
                if 'givenName' in scim_user_data['name']:
                    changes['first_name'] = scim_user_data['name']['givenName']
                if 'familyName' in scim_user_data['name']:
                    changes['last_name'] = scim_user_data['name']['familyName']
            
            if 'department' in scim_user_data:
                changes['department'] = scim_user_data['department']
            if 'title' in scim_user_data:
                changes['job_title'] = scim_user_data['title']
            if 'active' in scim_user_data:
                changes['is_active'] = scim_user_data['active']
            
            # Update user
            for field, value in changes.items():
                setattr(user, field, value)
            user.save()
            
            # Update membership if active status changed
            if 'is_active' in changes:
                membership = user.tenant_memberships.get(tenant=self.tenant)
                membership.is_active = changes['is_active']
                membership.save()
            
            # Log sync event
            AzureUserSync.objects.create(
                tenant=self.tenant,
                user=user,
                azure_user_id=azure_user_id,
                azure_user_data=scim_user_data,
                action='updated',
                changes=changes,
                status='success'
            )
            
            logger.info(f"Updated user {user.email} for tenant {self.tenant.name}")
            return user
            
        except User.DoesNotExist:
            raise ValueError(f"User with Azure ID {azure_user_id} not found")
        except Exception as e:
            logger.error(f"Failed to update user {azure_user_id}: {e}")
            raise
    
    def handle_user_delete(self, azure_user_id: str) -> bool:
        """
        Handle SCIM user deletion from Azure AD
        
        Args:
            azure_user_id: Azure AD user ID
            
        Returns:
            True if successful
        """
        try:
            user = User.objects.get(azure_id=azure_user_id, primary_tenant=self.tenant)
            
            if self.sso_config.auto_deprovision_users:
                # Soft delete
                user.is_active = False
                user.deactivated_at = timezone.now()
                user.deactivation_reason = 'REMOVED_FROM_AZURE'
                user.save()
                
                # Deactivate membership
                membership = user.tenant_memberships.get(tenant=self.tenant)
                membership.is_active = False
                membership.save()
                
                # Log sync event
                AzureUserSync.objects.create(
                    tenant=self.tenant,
                    user=user,
                    azure_user_id=azure_user_id,
                    azure_user_data={},
                    action='deleted',
                    status='success'
                )
                
                # Log audit event
                AzureADAuditLog.log_event(
                    tenant=self.tenant,
                    user=user,
                    event_type='AZURE_USER_REMOVED',
                    description=f'User {user.email} deactivated from Azure AD',
                    details={'azure_id': azure_user_id}
                )
                
                logger.info(f"Deactivated user {user.email} for tenant {self.tenant.name}")
            
            return True
            
        except User.DoesNotExist:
            raise ValueError(f"User with Azure ID {azure_user_id} not found")
        except Exception as e:
            logger.error(f"Failed to delete user {azure_user_id}: {e}")
            raise
    
    def sync_all_users(self) -> Dict[str, int]:
        """
        Perform full synchronization with Azure AD via Microsoft Graph API
        
        Returns:
            Dictionary with sync statistics
        """
        try:
            stats = {
                'total': 0,
                'created': 0,
                'updated': 0,
                'deactivated': 0,
                'errors': 0
            }
            
            # Get access token for Microsoft Graph API
            access_token = self._get_graph_api_token()
            if not access_token:
                raise ValueError("Failed to obtain access token for Microsoft Graph API")
            
            # Fetch users from Microsoft Graph API
            users_data = self._fetch_users_from_graph_api(access_token)
            
            # Process each user
            for user_data in users_data:
                try:
                    user, created = self._create_or_update_user(user_data)
                    
                    if created:
                        stats['created'] += 1
                        logger.info(f"Created user from Azure AD: {user.email}")
                    else:
                        stats['updated'] += 1
                        logger.info(f"Updated user from Azure AD: {user.email}")
                    
                    # Create or update tenant membership (separate try-catch to ensure membership is created)
                    try:
                        self._create_or_update_membership(user, user_data)
                    except Exception as membership_error:
                        logger.warning(f"Failed to create membership for user {user.email}, but user was created: {membership_error}")
                        # Try to create membership with default role
                        try:
                            self._create_or_update_membership(user, {'role': 'member', 'accountEnabled': True})
                        except Exception as fallback_error:
                            logger.error(f"Failed to create membership with fallback role for user {user.email}: {fallback_error}")
                            stats['errors'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process user {user_data.get('mail', 'unknown')}: {e}")
                    stats['errors'] += 1
            
            stats['total'] = stats['created'] + stats['updated']
            
            # Update sync status
            self.sso_config.last_sync_at = timezone.now()
            self.sso_config.last_sync_status = 'success'
            self.sso_config.save()
            
            # Log sync completion
            AzureADAuditLog.log_event(
                tenant=self.tenant,
                event_type='SCIM_SYNC_COMPLETED',
                description='Full user sync completed',
                details=stats
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to sync users for tenant {self.tenant.name}: {e}")
            
            # Update sync status with error
            self.sso_config.last_sync_at = timezone.now()
            self.sso_config.last_sync_status = 'failed'
            self.sso_config.last_sync_error = str(e)
            self.sso_config.save()
            
            # Log sync failure
            AzureADAuditLog.log_event(
                tenant=self.tenant,
                event_type='SCIM_SYNC_FAILED',
                description='Full user sync failed',
                details={'error': str(e)}
            )
            
            raise
    
    def _get_graph_api_token(self) -> Optional[str]:
        """
        Get access token for Microsoft Graph API using client credentials flow
        """
        try:
            token_url = f"https://login.microsoftonline.com/{self.sso_config.azure_tenant_id}/oauth2/v2.0/token"
            
            token_data = {
                'client_id': self.sso_config.client_id,
                'client_secret': self.sso_config.client_secret,
                'scope': 'https://graph.microsoft.com/.default',
                'grant_type': 'client_credentials'
            }
            
            response = requests.post(token_url, data=token_data)
            response.raise_for_status()
            
            token_response = response.json()
            return token_response.get('access_token')
            
        except Exception as e:
            logger.error(f"Failed to get Graph API token: {e}")
            return None
    
    def _fetch_users_from_graph_api(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Fetch users from Microsoft Graph API
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Fetch users with specific properties
            graph_url = "https://graph.microsoft.com/v1.0/users"
            params = {
                '$select': 'id,mail,displayName,givenName,surname,jobTitle,department,officeLocation,userPrincipalName,accountEnabled',
                '$top': 999  # Maximum users per request
            }
            
            all_users = []
            next_url = graph_url
            
            while next_url:
                if next_url == graph_url:
                    response = requests.get(next_url, headers=headers, params=params)
                else:
                    response = requests.get(next_url, headers=headers)
                
                response.raise_for_status()
                data = response.json()
                
                users = data.get('value', [])
                all_users.extend(users)
                
                # Check for next page
                next_url = data.get('@odata.nextLink')
            
            logger.info(f"Fetched {len(all_users)} users from Microsoft Graph API")
            return all_users
            
        except Exception as e:
            logger.error(f"Failed to fetch users from Graph API: {e}")
            raise
    
    def _create_or_update_user(self, user_data: Dict[str, Any]) -> Tuple[User, bool]:
        """
        Create or update user from Azure AD data
        """
        email = user_data.get('mail') or user_data.get('userPrincipalName')
        if not email:
            raise ValueError("User has no email address")
        
        # Extract user information
        first_name = user_data.get('givenName', '')
        last_name = user_data.get('surname', '')
        display_name = user_data.get('displayName', '')
        job_title = user_data.get('jobTitle', '')
        department = user_data.get('department', '')
        office_location = user_data.get('officeLocation', '')
        azure_id = user_data.get('id', '')
        account_enabled = user_data.get('accountEnabled', True)
        
        # Create or update user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'username': email,  # Use email as username
                'azure_id': azure_id,
                'azure_upn': user_data.get('userPrincipalName', ''),
                'department': department,
                'job_title': job_title,
                'is_sso_user': True,
                'is_active': account_enabled,
                'is_staff': False,
                'is_superuser': False
            }
        )
        
        if not created:
            # Update existing user
            user.first_name = first_name
            user.last_name = last_name
            user.azure_id = azure_id
            user.azure_upn = user_data.get('userPrincipalName', '')
            user.department = department
            user.job_title = job_title
            user.is_sso_user = True
            user.is_active = account_enabled
            user.save()
        
        return user, created
    
    def _create_or_update_membership(self, user: User, user_data: Dict[str, Any]) -> None:
        """
        Create or update tenant membership for user
        """
        # Determine role based on user properties or groups
        role = self._determine_user_role(user_data)
        
        membership, created = TenantMembership.objects.get_or_create(
            user=user,
            tenant=self.tenant,
            defaults={
                'role': role,
                'is_active': user_data.get('accountEnabled', True),
                'can_run_scans': True,
                'can_export_reports': True,
                'can_invite_users': role == 'admin',
                'can_manage_users': role == 'admin',
                'can_manage_settings': role == 'admin',
                'can_view_analytics': True,
                'can_manage_billing': role == 'admin',
                'can_manage_providers': role == 'admin',
                'can_manage_integrations': role == 'admin',
                'can_manage_scans': role == 'admin',
                'unlimited_visibility': role == 'admin'
            }
        )
        
        if not created:
            # Update existing membership
            membership.role = role
            membership.is_active = user_data.get('accountEnabled', True)
            membership.save()
    
    def _determine_user_role(self, user_data: Dict[str, Any]) -> str:
        """
        Determine user role based on Azure AD data
        """
        # Check if user has admin indicators
        # Handle None values properly
        job_title = user_data.get('jobTitle') or ''
        department = user_data.get('department') or ''
        
        # Convert to lowercase safely
        job_title = job_title.lower() if isinstance(job_title, str) else ''
        department = department.lower() if isinstance(department, str) else ''
        
        # Admin indicators
        admin_indicators = [
            'admin', 'administrator', 'manager', 'director', 'head', 'lead',
            'chief', 'vp', 'vice president', 'president', 'ceo', 'cto', 'cfo'
        ]
        
        if job_title and any(indicator in job_title for indicator in admin_indicators):
            return 'admin'
        
        if department and any(indicator in department for indicator in ['it', 'technology', 'security']):
            return 'admin'
        
        # Default to member
        return 'member'
    
    def _determine_role_from_groups(self, groups: List[Dict[str, Any]]) -> str:
        """
        Map Azure AD groups to roles
        
        Args:
            groups: List of Azure AD groups
            
        Returns:
            Role name
        """
        group_role_mapping = self.sso_config.group_role_mapping
        
        for group in groups:
            group_id = group.get('value')
            if group_id in group_role_mapping:
                return group_role_mapping[group_id]
        
        return 'viewer'  # Default role
    
    def _set_role_permissions(self, membership: TenantMembership, role: str):
        """
        Set permissions based on role
        
        Args:
            membership: TenantMembership object
            role: Role name
        """
        role_permissions = {
            'owner': {
                'can_run_scans': True,
                'can_manage_users': True,
                'can_manage_integrations': True,
                'can_export_reports': True,
                'can_invite_users': True,
                'can_manage_settings': True,
                'can_manage_billing': True,
                'can_manage_providers': True,
                'can_manage_scans': True,
                'unlimited_visibility': True
            },
            'admin': {
                'can_run_scans': True,
                'can_manage_users': True,
                'can_manage_integrations': True,
                'can_export_reports': True,
                'can_invite_users': True,
                'can_manage_settings': True,
                'can_manage_billing': False,
                'can_manage_providers': True,
                'can_manage_scans': True,
                'unlimited_visibility': False
            },
            'auditor': {
                'can_run_scans': True,
                'can_manage_users': False,
                'can_manage_integrations': False,
                'can_export_reports': True,
                'can_invite_users': False,
                'can_manage_settings': False,
                'can_manage_billing': False,
                'can_manage_providers': False,
                'can_manage_scans': False,
                'unlimited_visibility': False
            },
            'viewer': {
                'can_run_scans': False,
                'can_manage_users': False,
                'can_manage_integrations': False,
                'can_export_reports': False,
                'can_invite_users': False,
                'can_manage_settings': False,
                'can_manage_billing': False,
                'can_manage_providers': False,
                'can_manage_scans': False,
                'unlimited_visibility': False
            }
        }
        
        permissions = role_permissions.get(role, role_permissions['viewer'])
        for permission, value in permissions.items():
            setattr(membership, permission, value)
        membership.save()
    
    def _format_scim_user(self, user: User) -> Dict[str, Any]:
        """
        Format user data for SCIM response
        
        Args:
            user: User object
            
        Returns:
            SCIM-formatted user data
        """
        return {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "id": user.azure_id,
            "externalId": user.azure_id,
            "userName": user.email,
            "name": {
                "givenName": user.first_name,
                "familyName": user.last_name
            },
            "emails": [{"primary": True, "value": user.email}],
            "active": user.is_active,
            "department": user.department,
            "title": user.job_title,
            "phoneNumbers": [{"primary": True, "value": user.phone_number}] if user.phone_number else [],
            "meta": {
                "created": user.created_at.isoformat(),
                "lastModified": user.updated_at.isoformat()
            }
        }
