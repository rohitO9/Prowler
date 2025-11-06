"""
User Service - Handles user creation, role assignment, and management.

This service manages the complete user lifecycle including:
- User creation from invitations
- Role assignment and permissions
- User profile management
- Account security and lockout
- Multi-tenant user management
"""

import logging
from typing import Dict, Any, Optional, List
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password

from api.models import User, Tenant, TenantMembership, Invitation, SecurityAuditLog
from api.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing users and their tenant memberships."""
    
    def __init__(self):
        self.audit_log = AuditLogService()
    
    def create_user_from_invite(self, invitation: Invitation, user_data: Dict[str, Any],
                              ip_address: Optional[str] = None) -> User:
        """
        Create a new user from an invitation.
        
        Args:
            invitation: The invitation being accepted
            user_data: User data for account creation
            ip_address: IP address of the user creating the account
            
        Returns:
            User: The created user instance
        """
        try:
            with transaction.atomic():
                # Validate user data
                self._validate_user_data(user_data)
                
                # Create user account (SSO-only for invited users - no password)
                user = User.objects.create(
                    email=invitation.email,
                    username=user_data.get('username', invitation.email),
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                    name=user_data.get('name', f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()),
                    primary_tenant=invitation.tenant,
                    is_active=True,
                    is_verified=True,  # Invited users are pre-verified
                    is_sso_user=True,  # Invited users are SSO-only
                    date_joined=timezone.now()
                )
                
                # DO NOT set password for invited users - they can ONLY login via SSO
                # This ensures invited users must use Azure AD SSO authentication
                
                # Create tenant membership
                membership = TenantMembership.objects.create(
                    user=user,
                    tenant=invitation.tenant,
                    role='member',  # Default role for invited users
                    is_active=True,
                    invited_by=invitation.inviter
                )
                
                # Set default permissions based on role
                self._set_default_permissions(membership, 'member')
                
                # Log user creation
                self.audit_log.log_event(
                    event_type='user_created',
                    message=f"New user {user.email} created from invitation",
                    user=user,
                    tenant=invitation.tenant,
                    severity='low',
                    details={
                        'user_id': str(user.id),
                        'invitation_id': str(invitation.id),
                        'membership_id': str(membership.id),
                        'ip_address': ip_address,
                        'created_from_invite': True
                    }
                )
                
                logger.info(f"✅ Created user {user.email} from invitation")
                return user
                
        except Exception as e:
            logger.error(f"❌ Failed to create user from invitation: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to create user from invitation: {str(e)}",
                tenant=invitation.tenant,
                severity='high',
                details={'error': str(e), 'invitation_id': str(invitation.id)}
            )
            raise
    
    def create_user(self, tenant: Tenant, user_data: Dict[str, Any],
                   created_by: Optional[User] = None) -> User:
        """
        Create a new user directly (admin function).
        
        Args:
            tenant: Tenant to create user in
            user_data: User data for account creation
            created_by: User who created this user account
            
        Returns:
            User: The created user instance
        """
        try:
            with transaction.atomic():
                # Validate user data
                self._validate_user_data(user_data)
                
                # Check if user already exists
                if User.objects.filter(email=user_data['email']).exists():
                    raise ValidationError(f"User with email {user_data['email']} already exists")
                
                # Check tenant limits
                if tenant.is_at_user_limit:
                    raise ValidationError(f"Tenant has reached user limit ({tenant.max_users})")
                
                # Create user account
                user = User.objects.create(
                    email=user_data['email'],
                    username=user_data.get('username', user_data['email']),
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', ''),
                    name=user_data.get('name', f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()),
                    primary_tenant=tenant,
                    is_active=True,
                    is_verified=user_data.get('is_verified', True),
                    date_joined=timezone.now()
                )
                
                # Set password if provided
                if user_data.get('password'):
                    user.set_password(user_data['password'])
                    user.save()
                
                # Create tenant membership
                role = user_data.get('role', 'member')
                membership = TenantMembership.objects.create(
                    user=user,
                    tenant=tenant,
                    role=role,
                    is_active=True,
                    invited_by=created_by
                )
                
                # Set permissions based on role
                self._set_default_permissions(membership, role)
                
                # Log user creation
                self.audit_log.log_event(
                    event_type='user_created',
                    message=f"User {user.email} created by {created_by.email if created_by else 'system'}",
                    user=created_by,
                    tenant=tenant,
                    severity='low',
                    details={
                        'user_id': str(user.id),
                        'membership_id': str(membership.id),
                        'role': role,
                        'created_by_admin': True
                    }
                )
                
                logger.info(f"✅ Created user {user.email} in tenant {tenant.name}")
                return user
                
        except Exception as e:
            logger.error(f"❌ Failed to create user: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to create user: {str(e)}",
                user=created_by,
                tenant=tenant,
                severity='high',
                details={'error': str(e), 'user_data': user_data}
            )
            raise
    
    def update_user_role(self, user: User, tenant: Tenant, new_role: str,
                        updated_by: Optional[User] = None) -> TenantMembership:
        """
        Update a user's role in a tenant.
        
        Args:
            user: User whose role to update
            tenant: Tenant context
            new_role: New role to assign
            updated_by: User who updated the role
            
        Returns:
            TenantMembership: The updated membership
        """
        try:
            with transaction.atomic():
                # Validate role
                valid_roles = ['owner', 'admin', 'member', 'guest']
                if new_role not in valid_roles:
                    raise ValidationError(f"Invalid role: {new_role}")
                
                # Get membership
                membership = TenantMembership.objects.get(user=user, tenant=tenant)
                old_role = membership.role
                
                # Update role
                membership.role = new_role
                membership.save()
                
                # Update permissions based on new role
                self._set_default_permissions(membership, new_role)
                
                # Log role update
                self.audit_log.log_event(
                    event_type='admin_action',
                    message=f"User {user.email} role changed from {old_role} to {new_role}",
                    user=updated_by,
                    tenant=tenant,
                    severity='medium',
                    details={
                        'user_id': str(user.id),
                        'membership_id': str(membership.id),
                        'old_role': old_role,
                        'new_role': new_role,
                        'updated_by': updated_by.email if updated_by else None
                    }
                )
                
                logger.info(f"✅ Updated user {user.email} role to {new_role}")
                return membership
                
        except Exception as e:
            logger.error(f"❌ Failed to update user role: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to update user role: {str(e)}",
                user=updated_by,
                tenant=tenant,
                severity='medium',
                details={'error': str(e), 'user_id': str(user.id), 'new_role': new_role}
            )
            raise
    
    def deactivate_user(self, user: User, tenant: Tenant, 
                       deactivated_by: Optional[User] = None,
                       reason: Optional[str] = None) -> bool:
        """
        Deactivate a user in a tenant.
        
        Args:
            user: User to deactivate
            tenant: Tenant context
            deactivated_by: User who deactivated the account
            reason: Reason for deactivation
            
        Returns:
            bool: True if user was deactivated successfully
        """
        try:
            with transaction.atomic():
                # Get membership
                membership = TenantMembership.objects.get(user=user, tenant=tenant)
                
                # Deactivate membership
                membership.is_active = False
                membership.save()
                
                # If this is the user's primary tenant, deactivate the user account
                if user.primary_tenant == tenant:
                    user.is_active = False
                    user.save()
                
                # Log deactivation
                self.audit_log.log_event(
                    event_type='admin_action',
                    message=f"User {user.email} deactivated in tenant {tenant.name}",
                    user=deactivated_by,
                    tenant=tenant,
                    severity='medium',
                    details={
                        'user_id': str(user.id),
                        'membership_id': str(membership.id),
                        'reason': reason,
                        'deactivated_by': deactivated_by.email if deactivated_by else None
                    }
                )
                
                logger.info(f"✅ Deactivated user {user.email} in tenant {tenant.name}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to deactivate user: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to deactivate user: {str(e)}",
                user=deactivated_by,
                tenant=tenant,
                severity='high',
                details={'error': str(e), 'user_id': str(user.id)}
            )
            raise
    
    def reactivate_user(self, user: User, tenant: Tenant,
                       reactivated_by: Optional[User] = None) -> bool:
        """
        Reactivate a user in a tenant.
        
        Args:
            user: User to reactivate
            tenant: Tenant context
            reactivated_by: User who reactivated the account
            
        Returns:
            bool: True if user was reactivated successfully
        """
        try:
            with transaction.atomic():
                # Get membership
                membership = TenantMembership.objects.get(user=user, tenant=tenant)
                
                # Reactivate membership
                membership.is_active = True
                membership.save()
                
                # Reactivate user account if needed
                if not user.is_active:
                    user.is_active = True
                    user.save()
                
                # Log reactivation
                self.audit_log.log_event(
                    event_type='admin_action',
                    message=f"User {user.email} reactivated in tenant {tenant.name}",
                    user=reactivated_by,
                    tenant=tenant,
                    severity='low',
                    details={
                        'user_id': str(user.id),
                        'membership_id': str(membership.id),
                        'reactivated_by': reactivated_by.email if reactivated_by else None
                    }
                )
                
                logger.info(f"✅ Reactivated user {user.email} in tenant {tenant.name}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to reactivate user: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to reactivate user: {str(e)}",
                user=reactivated_by,
                tenant=tenant,
                severity='medium',
                details={'error': str(e), 'user_id': str(user.id)}
            )
            raise
    
    def get_user_permissions(self, user: User, tenant: Tenant) -> Dict[str, bool]:
        """
        Get user permissions in a tenant.
        
        Args:
            user: User to get permissions for
            tenant: Tenant context
            
        Returns:
            Dict of permission names to boolean values
        """
        try:
            membership = TenantMembership.objects.get(user=user, tenant=tenant)
            
            return {
                'can_invite_users': membership.can_invite_users,
                'can_manage_settings': membership.can_manage_settings,
                'can_view_analytics': membership.can_view_analytics,
                'can_manage_users': membership.can_manage_users,
                'can_manage_billing': membership.can_manage_billing,
                'can_manage_providers': membership.can_manage_providers,
                'can_manage_integrations': membership.can_manage_integrations,
                'can_manage_scans': membership.can_manage_scans,
                'unlimited_visibility': membership.unlimited_visibility,
                'role': membership.role,
                'is_active': membership.is_active
            }
            
        except TenantMembership.DoesNotExist:
            return {}
        except Exception as e:
            logger.error(f"❌ Failed to get user permissions: {e}")
            raise
    
    def update_user_permissions(self, user: User, tenant: Tenant, 
                               permissions: Dict[str, bool],
                               updated_by: Optional[User] = None) -> TenantMembership:
        """
        Update user permissions in a tenant.
        
        Args:
            user: User whose permissions to update
            tenant: Tenant context
            permissions: Dict of permission names to boolean values
            updated_by: User who updated the permissions
            
        Returns:
            TenantMembership: The updated membership
        """
        try:
            with transaction.atomic():
                # Get membership
                membership = TenantMembership.objects.get(user=user, tenant=tenant)
                
                # Track changes
                changes = {}
                
                # Update permissions
                permission_fields = [
                    'can_invite_users', 'can_manage_settings', 'can_view_analytics',
                    'can_manage_users', 'can_manage_billing', 'can_manage_providers',
                    'can_manage_integrations', 'can_manage_scans', 'unlimited_visibility'
                ]
                
                for field in permission_fields:
                    if field in permissions:
                        old_value = getattr(membership, field)
                        new_value = permissions[field]
                        if old_value != new_value:
                            setattr(membership, field, new_value)
                            changes[field] = {'old': old_value, 'new': new_value}
                
                # Save changes
                if changes:
                    membership.save()
                    
                    # Log permission update
                    self.audit_log.log_event(
                        event_type='admin_action',
                        message=f"User {user.email} permissions updated in tenant {tenant.name}",
                        user=updated_by,
                        tenant=tenant,
                        severity='medium',
                        details={
                            'user_id': str(user.id),
                            'membership_id': str(membership.id),
                            'changes': changes,
                            'updated_by': updated_by.email if updated_by else None
                        }
                    )
                    
                    logger.info(f"✅ Updated permissions for user {user.email}")
                
                return membership
                
        except Exception as e:
            logger.error(f"❌ Failed to update user permissions: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to update user permissions: {str(e)}",
                user=updated_by,
                tenant=tenant,
                severity='high',
                details={'error': str(e), 'user_id': str(user.id), 'permissions': permissions}
            )
            raise
    
    def get_tenant_users(self, tenant: Tenant, active_only: bool = True) -> List[User]:
        """
        Get all users in a tenant.
        
        Args:
            tenant: Tenant to get users for
            active_only: Whether to return only active users
            
        Returns:
            List of User instances
        """
        try:
            memberships = TenantMembership.objects.filter(tenant=tenant)
            
            if active_only:
                memberships = memberships.filter(is_active=True)
            
            users = [membership.user for membership in memberships]
            return users
            
        except Exception as e:
            logger.error(f"❌ Failed to get tenant users: {e}")
            raise
    
    def get_user_tenants(self, user: User, active_only: bool = True) -> List[Tenant]:
        """
        Get all tenants a user belongs to.
        
        Args:
            user: User to get tenants for
            active_only: Whether to return only active memberships
            
        Returns:
            List of Tenant instances
        """
        try:
            memberships = user.tenant_memberships.all()
            
            if active_only:
                memberships = memberships.filter(is_active=True)
            
            tenants = [membership.tenant for membership in memberships]
            return tenants
            
        except Exception as e:
            logger.error(f"❌ Failed to get user tenants: {e}")
            raise
    
    def _validate_user_data(self, user_data: Dict[str, Any]) -> None:
        """Validate user data before creation."""
        required_fields = ['email']
        
        for field in required_fields:
            if not user_data.get(field):
                raise ValidationError(f"Field '{field}' is required")
        
        # Validate email format
        email = user_data['email']
        if not email or '@' not in email:
            raise ValidationError("Invalid email address")
        
        # Validate role if provided
        if 'role' in user_data:
            valid_roles = ['owner', 'admin', 'member', 'guest']
            if user_data['role'] not in valid_roles:
                raise ValidationError(f"Invalid role: {user_data['role']}")
    
    def _set_default_permissions(self, membership: TenantMembership, role: str) -> None:
        """Set default permissions based on role."""
        if role == 'owner':
            # Owners have all permissions
            membership.can_invite_users = True
            membership.can_manage_settings = True
            membership.can_view_analytics = True
            membership.can_manage_users = True
            membership.can_manage_billing = True
            membership.can_manage_providers = True
            membership.can_manage_integrations = True
            membership.can_manage_scans = True
            membership.unlimited_visibility = True
            
        elif role == 'admin':
            # Admins have most permissions except billing
            membership.can_invite_users = True
            membership.can_manage_settings = True
            membership.can_view_analytics = True
            membership.can_manage_users = True
            membership.can_manage_billing = False
            membership.can_manage_providers = True
            membership.can_manage_integrations = True
            membership.can_manage_scans = True
            membership.unlimited_visibility = True
            
        elif role == 'member':
            # Members have basic permissions
            membership.can_invite_users = False
            membership.can_manage_settings = False
            membership.can_view_analytics = True
            membership.can_manage_users = False
            membership.can_manage_billing = False
            membership.can_manage_providers = False
            membership.can_manage_integrations = False
            membership.can_manage_scans = False
            membership.unlimited_visibility = False
            
        elif role == 'guest':
            # Guests have minimal permissions
            membership.can_invite_users = False
            membership.can_manage_settings = False
            membership.can_view_analytics = False
            membership.can_manage_users = False
            membership.can_manage_billing = False
            membership.can_manage_providers = False
            membership.can_manage_integrations = False
            membership.can_manage_scans = False
            membership.unlimited_visibility = False
        
        membership.save()
