"""
Azure AD Edge Cases Handler
Handles complex scenarios in Azure AD integration
"""

import logging
from typing import Dict, Any, Optional, List
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from api.models import User, Tenant, TenantMembership
from api.v1.models.azure_sso import AzureSSOConfig, AzureUserSync, AzureADAuditLog
from api.services.audit_log_service import AuditLogService
from api.utils.error_handling import ErrorContext

logger = logging.getLogger(__name__)


class AzureADEdgeCaseHandler:
    """
    Handles edge cases in Azure AD integration
    """
    
    def __init__(self):
        self.audit_log = AuditLogService()
    
    def handle_user_removed_from_azure(self, tenant: Tenant, azure_user_id: str, 
                                     user_data: Dict[str, Any]) -> bool:
        """
        Handle when Azure AD user is removed
        
        Args:
            tenant: Tenant object
            azure_user_id: Azure AD user ID
            user_data: Azure AD user data
            
        Returns:
            bool: True if handled successfully
        """
        with ErrorContext("handle_user_removed_from_azure", tenant):
            try:
                # Find user by Azure ID
                user = User.objects.get(
                    azure_id=azure_user_id,
                    primary_tenant=tenant
                )
                
                # Soft delete user
                user.is_active = False
                user.deactivated_at = timezone.now()
                user.deactivation_reason = 'REMOVED_FROM_AZURE'
                user.save()
                
                # Deactivate all tenant memberships
                memberships = user.tenant_memberships.filter(tenant=tenant)
                for membership in memberships:
                    membership.is_active = False
                    membership.save()
                
                # Revoke all active sessions
                self._revoke_user_sessions(user)
                
                # Notify admin
                self._notify_admin_user_removed(tenant, user)
                
                # Log sync event
                AzureUserSync.objects.create(
                    tenant=tenant,
                    user=user,
                    azure_user_id=azure_user_id,
                    azure_user_data=user_data,
                    action='deleted',
                    status='success'
                )
                
                # Log audit event
                AzureADAuditLog.log_event(
                    tenant=tenant,
                    user=user,
                    event_type='AZURE_USER_REMOVED',
                    description=f'User {user.email} removed from Azure AD',
                    details={'azure_id': azure_user_id}
                )
                
                logger.info(f"Successfully handled user removal: {user.email}")
                return True
                
            except User.DoesNotExist:
                logger.warning(f"User with Azure ID {azure_user_id} not found for removal")
                return False
            except Exception as e:
                logger.error(f"Failed to handle user removal: {e}")
                return False
    
    def handle_user_disabled_in_azure(self, tenant: Tenant, azure_user_id: str,
                                    user_data: Dict[str, Any]) -> bool:
        """
        Handle when Azure AD user is disabled
        
        Args:
            tenant: Tenant object
            azure_user_id: Azure AD user ID
            user_data: Azure AD user data
            
        Returns:
            bool: True if handled successfully
        """
        with ErrorContext("handle_user_disabled_in_azure", tenant):
            try:
                # Find user by Azure ID
                user = User.objects.get(
                    azure_id=azure_user_id,
                    primary_tenant=tenant
                )
                
                # Deactivate user but keep membership
                user.is_active = False
                user.deactivated_at = timezone.now()
                user.deactivation_reason = 'DISABLED_IN_AZURE'
                user.save()
                
                # Keep membership active but mark as disabled
                membership = user.tenant_memberships.get(tenant=tenant)
                membership.is_active = False
                membership.save()
                
                # Block login attempts
                user.locked_until = timezone.now() + timezone.timedelta(days=365)  # Effectively permanent
                user.save()
                
                # Log sync event
                AzureUserSync.objects.create(
                    tenant=tenant,
                    user=user,
                    azure_user_id=azure_user_id,
                    azure_user_data=user_data,
                    action='disabled',
                    status='success'
                )
                
                # Log audit event
                AzureADAuditLog.log_event(
                    tenant=tenant,
                    user=user,
                    event_type='USER_DEACTIVATED',
                    description=f'User {user.email} disabled in Azure AD',
                    details={'azure_id': azure_user_id, 'reason': 'DISABLED_IN_AZURE'}
                )
                
                logger.info(f"Successfully handled user disable: {user.email}")
                return True
                
            except User.DoesNotExist:
                logger.warning(f"User with Azure ID {azure_user_id} not found for disable")
                return False
            except Exception as e:
                logger.error(f"Failed to handle user disable: {e}")
                return False
    
    def handle_user_exists_in_multiple_tenants(self, email: str, azure_user_id: str,
                                             tenant: Tenant) -> User:
        """
        Handle when user exists in multiple tenants
        
        Args:
            email: User email
            azure_user_id: Azure AD user ID
            tenant: Current tenant
            
        Returns:
            User: User object
        """
        with ErrorContext("handle_user_exists_in_multiple_tenants", tenant):
            try:
                # Check if user exists in other tenants
                existing_users = User.objects.filter(email=email).exclude(
                    primary_tenant=tenant
                )
                
                if existing_users.exists():
                    # User exists in other tenants - create new user for this tenant
                    # This allows same email across different tenants
                    user = User.objects.create(
                        email=email,
                        azure_id=azure_user_id,
                        azure_tenant_id=tenant.azure_sso_config.azure_tenant_id,
                        is_sso_user=True,
                        is_active=True,
                        primary_tenant=tenant
                    )
                    
                    # Create tenant membership
                    membership = TenantMembership.objects.create(
                        user=user,
                        tenant=tenant,
                        role='viewer',  # Default role
                        is_active=True
                    )
                    
                    logger.info(f"Created new user {email} for tenant {tenant.name}")
                    return user
                else:
                    # User doesn't exist - create normally
                    user = User.objects.create(
                        email=email,
                        azure_id=azure_user_id,
                        azure_tenant_id=tenant.azure_sso_config.azure_tenant_id,
                        is_sso_user=True,
                        is_active=True,
                        primary_tenant=tenant
                    )
                    
                    # Create tenant membership
                    membership = TenantMembership.objects.create(
                        user=user,
                        tenant=tenant,
                        role='viewer',  # Default role
                        is_active=True
                    )
                    
                    logger.info(f"Created new user {email} for tenant {tenant.name}")
                    return user
                    
            except Exception as e:
                logger.error(f"Failed to handle multi-tenant user: {e}")
                raise
    
    def handle_invite_expired(self, invite_token: str) -> Dict[str, Any]:
        """
        Handle expired invitation
        
        Args:
            invite_token: JWT invite token
            
        Returns:
            dict: Response data
        """
        with ErrorContext("handle_invite_expired"):
            try:
                from api.utils.jwt_tokens import validate_token
                
                # Try to validate token to get user info
                try:
                    payload = validate_token(invite_token, 'invite')
                    user_id = payload.get('user_id')
                    tenant_id = payload.get('tenant_id')
                    
                    # Get user and tenant for context
                    user = User.objects.get(id=user_id)
                    tenant = Tenant.objects.get(id=tenant_id)
                    
                    # Log expired invite attempt
                    AzureADAuditLog.log_event(
                        tenant=tenant,
                        user=user,
                        event_type='INVITE_EXPIRED',
                        description=f'User {user.email} attempted to use expired invite',
                        details={'invite_token': invite_token[:10] + '...'}
                    )
                    
                    return {
                        'error': 'Invitation expired',
                        'message': 'This invitation has expired. Please contact your administrator for a new invitation.',
                        'user_email': user.email,
                        'tenant_name': tenant.name
                    }
                    
                except Exception:
                    # Token is completely invalid
                    return {
                        'error': 'Invalid invitation',
                        'message': 'This invitation is invalid or has expired. Please contact your administrator.'
                    }
                    
            except Exception as e:
                logger.error(f"Failed to handle expired invite: {e}")
                return {
                    'error': 'Invalid invitation',
                    'message': 'This invitation is invalid or has expired.'
                }
    
    def handle_role_changed_in_azure(self, tenant: Tenant, azure_user_id: str,
                                   new_groups: List[Dict[str, Any]]) -> bool:
        """
        Handle when user's role changes in Azure AD
        
        Args:
            tenant: Tenant object
            azure_user_id: Azure AD user ID
            new_groups: New Azure AD groups
            
        Returns:
            bool: True if handled successfully
        """
        with ErrorContext("handle_role_changed_in_azure", tenant):
            try:
                # Find user
                user = User.objects.get(
                    azure_id=azure_user_id,
                    primary_tenant=tenant
                )
                
                # Get current membership
                membership = user.tenant_memberships.get(tenant=tenant)
                old_role = membership.role
                
                # Determine new role from groups
                from api.services.azure_scim_service import AzureSCIMService
                scim_service = AzureSCIMService(tenant)
                new_role = scim_service._determine_role_from_groups(new_groups)
                
                if old_role != new_role:
                    # Update role
                    membership.role = new_role
                    
                    # Update permissions
                    scim_service._set_role_permissions(membership, new_role)
                    
                    # Notify admin if permissions changed significantly
                    if self._permissions_changed_significantly(old_role, new_role):
                        self._notify_admin_role_changed(tenant, user, old_role, new_role)
                    
                    # Log audit event
                    AzureADAuditLog.log_event(
                        tenant=tenant,
                        user=user,
                        event_type='ROLE_CHANGED',
                        description=f'Role changed from {old_role} to {new_role} for user {user.email}',
                        details={
                            'old_role': old_role,
                            'new_role': new_role,
                            'azure_groups': [g.get('display', '') for g in new_groups]
                        }
                    )
                    
                    logger.info(f"Successfully updated role for {user.email}: {old_role} -> {new_role}")
                    return True
                else:
                    logger.info(f"No role change needed for {user.email}")
                    return True
                    
            except User.DoesNotExist:
                logger.warning(f"User with Azure ID {azure_user_id} not found for role change")
                return False
            except Exception as e:
                logger.error(f"Failed to handle role change: {e}")
                return False
    
    def handle_sso_credentials_invalid(self, tenant: Tenant) -> bool:
        """
        Handle when SSO credentials become invalid
        
        Args:
            tenant: Tenant object
            
        Returns:
            bool: True if handled successfully
        """
        with ErrorContext("handle_sso_credentials_invalid", tenant):
            try:
                # Get SSO config
                sso_config = tenant.azure_sso_config
                
                # Disable SSO temporarily
                sso_config.is_active = False
                sso_config.save()
                
                # Log audit event
                AzureADAuditLog.log_event(
                    tenant=tenant,
                    event_type='SSO_DISABLED',
                    description=f'SSO disabled due to invalid credentials for tenant {tenant.name}',
                    details={'reason': 'invalid_credentials'}
                )
                
                # Notify admin
                self._notify_admin_sso_invalid(tenant)
                
                logger.warning(f"SSO disabled for tenant {tenant.name} due to invalid credentials")
                return True
                
            except Exception as e:
                logger.error(f"Failed to handle invalid SSO credentials: {e}")
                return False
    
    def handle_sync_conflicts(self, tenant: Tenant, azure_users: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Handle sync conflicts between Azure AD and local data
        
        Args:
            tenant: Tenant object
            azure_users: List of users from Azure AD
            
        Returns:
            dict: Sync statistics
        """
        with ErrorContext("handle_sync_conflicts", tenant):
            try:
                stats = {
                    'created': 0,
                    'updated': 0,
                    'deactivated': 0,
                    'conflicts': 0
                }
                
                # Get all local users for tenant
                local_users = User.objects.filter(
                    primary_tenant=tenant,
                    is_sso_user=True
                )
                
                azure_user_ids = {user.get('id') for user in azure_users}
                local_user_ids = set(local_users.values_list('azure_id', flat=True))
                
                # Users in Azure but not local - create
                missing_users = azure_user_ids - local_user_ids
                for azure_user in azure_users:
                    if azure_user.get('id') in missing_users:
                        # Create user
                        self._create_user_from_azure(tenant, azure_user)
                        stats['created'] += 1
                
                # Users in local but not Azure - deactivate
                extra_users = local_user_ids - azure_user_ids
                for azure_id in extra_users:
                    user = local_users.get(azure_id=azure_id)
                    if user:
                        user.is_active = False
                        user.deactivated_at = timezone.now()
                        user.deactivation_reason = 'REMOVED_FROM_AZURE'
                        user.save()
                        stats['deactivated'] += 1
                
                # Users in both - update if different
                common_users = azure_user_ids & local_user_ids
                for azure_user in azure_users:
                    if azure_user.get('id') in common_users:
                        user = local_users.get(azure_id=azure_user.get('id'))
                        if user and self._user_data_different(user, azure_user):
                            # Azure wins - update local data
                            self._update_user_from_azure(user, azure_user)
                            stats['updated'] += 1
                
                logger.info(f"Sync conflicts resolved for tenant {tenant.name}: {stats}")
                return stats
                
            except Exception as e:
                logger.error(f"Failed to handle sync conflicts: {e}")
                return {'created': 0, 'updated': 0, 'deactivated': 0, 'conflicts': 0}
    
    def _revoke_user_sessions(self, user: User):
        """Revoke all active sessions for user"""
        try:
            # This would typically involve invalidating JWT tokens
            # For now, we'll just log the action
            logger.info(f"Revoking sessions for user {user.email}")
            
            # TODO: Implement actual session revocation
            # - Invalidate JWT tokens
            # - Clear Redis sessions
            # - Notify frontend
            
        except Exception as e:
            logger.error(f"Failed to revoke sessions for user {user.email}: {e}")
    
    def _notify_admin_user_removed(self, tenant: Tenant, user: User):
        """Notify admin about user removal"""
        try:
            # Get tenant admins
            admins = User.objects.filter(
                tenant_memberships__tenant=tenant,
                tenant_memberships__role__in=['owner', 'admin'],
                tenant_memberships__is_active=True
            )
            
            for admin in admins:
                logger.info(f"Notifying admin {admin.email} about user removal: {user.email}")
                
                # TODO: Send email notification
                # TODO: Send in-app notification
                
        except Exception as e:
            logger.error(f"Failed to notify admin about user removal: {e}")
    
    def _notify_admin_role_changed(self, tenant: Tenant, user: User, old_role: str, new_role: str):
        """Notify admin about significant role changes"""
        try:
            # Only notify for significant changes
            significant_changes = [
                ('viewer', 'admin'),
                ('viewer', 'owner'),
                ('auditor', 'admin'),
                ('auditor', 'owner'),
                ('admin', 'owner'),
                ('admin', 'viewer'),
                ('owner', 'admin'),
                ('owner', 'viewer')
            ]
            
            if (old_role, new_role) in significant_changes:
                admins = User.objects.filter(
                    tenant_memberships__tenant=tenant,
                    tenant_memberships__role__in=['owner', 'admin'],
                    tenant_memberships__is_active=True
                )
                
                for admin in admins:
                    logger.info(f"Notifying admin {admin.email} about role change: {user.email} {old_role} -> {new_role}")
                    
                    # TODO: Send email notification
                    # TODO: Send in-app notification
                    
        except Exception as e:
            logger.error(f"Failed to notify admin about role change: {e}")
    
    def _notify_admin_sso_invalid(self, tenant: Tenant):
        """Notify admin about invalid SSO credentials"""
        try:
            admins = User.objects.filter(
                tenant_memberships__tenant=tenant,
                tenant_memberships__role__in=['owner', 'admin'],
                tenant_memberships__is_active=True
            )
            
            for admin in admins:
                logger.info(f"Notifying admin {admin.email} about invalid SSO credentials for tenant {tenant.name}")
                
                # TODO: Send email notification
                # TODO: Send in-app notification
                
        except Exception as e:
            logger.error(f"Failed to notify admin about invalid SSO: {e}")
    
    def _permissions_changed_significantly(self, old_role: str, new_role: str) -> bool:
        """Check if permissions changed significantly"""
        significant_changes = [
            ('viewer', 'admin'),
            ('viewer', 'owner'),
            ('auditor', 'admin'),
            ('auditor', 'owner'),
            ('admin', 'owner'),
            ('admin', 'viewer'),
            ('owner', 'admin'),
            ('owner', 'viewer')
        ]
        
        return (old_role, new_role) in significant_changes
    
    def _create_user_from_azure(self, tenant: Tenant, azure_user: Dict[str, Any]):
        """Create user from Azure AD data"""
        from api.services.azure_scim_service import AzureSCIMService
        
        scim_service = AzureSCIMService(tenant)
        return scim_service.handle_user_create(azure_user)
    
    def _update_user_from_azure(self, user: User, azure_user: Dict[str, Any]):
        """Update user from Azure AD data"""
        from api.services.azure_scim_service import AzureSCIMService
        
        scim_service = AzureSCIMService(user.primary_tenant)
        return scim_service.handle_user_update(user.azure_id, azure_user)
    
    def _user_data_different(self, user: User, azure_user: Dict[str, Any]) -> bool:
        """Check if user data is different from Azure AD"""
        # Compare key fields
        if user.first_name != azure_user.get('name', {}).get('givenName', ''):
            return True
        if user.last_name != azure_user.get('name', {}).get('familyName', ''):
            return True
        if user.department != azure_user.get('department', ''):
            return True
        if user.job_title != azure_user.get('title', ''):
            return True
        
        return False
