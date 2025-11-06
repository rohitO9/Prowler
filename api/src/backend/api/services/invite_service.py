"""
Invite Service - Handles user invitations and magic link generation.

This service manages the complete invite lifecycle including:
- JWT-based invite link generation
- Bulk invite processing
- Invite validation and acceptance
- Email delivery and tracking
- Invite expiration and cleanup
"""

import logging
import jwt
import secrets
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.template.loader import render_to_string

from api.models import Tenant, User, Invitation, TenantMembership, SecurityAuditLog
from api.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)


class InviteService:
    """Service for managing user invitations and magic links."""
    
    def __init__(self):
        self.audit_log = AuditLogService()
        self.jwt_secret = settings.SECRET_KEY
        self.invite_expiry_hours = getattr(settings, 'INVITE_EXPIRY_HOURS', 168)  # 7 days default
    
    def create_invite(self, tenant: Tenant, email: str, role: str = 'member',
                     invited_by: Optional[User] = None, 
                     custom_message: Optional[str] = None,
                     expires_hours: Optional[int] = None) -> Invitation:
        """
        Create a single user invitation.
        
        Args:
            tenant: Tenant to invite user to
            email: Email address to invite
            role: Role to assign to the user ('owner', 'admin', 'member', 'guest')
            invited_by: User who sent the invitation
            custom_message: Custom message to include in invitation
            expires_hours: Hours until invitation expires (default: 7 days)
            
        Returns:
            Invitation: The created invitation instance
        """
        try:
            with transaction.atomic():
                # Validate inputs
                self._validate_invite_data(tenant, email, role)
                
                # Note: We allow inviting existing users (e.g., synced from Azure AD)
                # The caller (invite_user view) handles membership logic for existing users
                
                # Check if pending invitation already exists
                existing_invite = Invitation.objects.filter(
                    email=email, 
                    tenant_id=tenant.id, 
                    state=Invitation.State.PENDING
                ).first()
                
                if existing_invite:
                    # Update existing invitation
                    existing_invite.expires_at = timezone.now() + timedelta(
                        hours=expires_hours or self.invite_expiry_hours
                    )
                    existing_invite.inviter = invited_by
                    existing_invite.save()
                    
                    logger.info(f"✅ Updated existing invitation for {email} to {tenant.name}")
                    return existing_invite
                
                # Create new invitation
                expires_at = timezone.now() + timedelta(
                    hours=expires_hours or self.invite_expiry_hours
                )
                
                # Ensure inviter is set - database requires it to be non-null
                if not invited_by:
                    raise ValueError("invited_by is required to create an invitation")
                
                # Debug: Log inviter details
                logger.debug(f"Creating invitation with inviter: {invited_by.id if invited_by else 'None'}, type: {type(invited_by)}")
                
                invitation = Invitation.objects.create(
                    email=email,
                    tenant_id=tenant,  # Django ORM accepts Tenant instance for ForeignKey
                    state=Invitation.State.PENDING,
                    expires_at=expires_at,
                    inviter=invited_by  # Field name is 'inviter', maps to 'inviter_id' in DB
                )
                
                # Generate JWT token for magic link
                magic_link = self._generate_magic_link(invitation)
                # Extract token from URL: format is /accept-invite?token=JWT_TOKEN
                # We need to extract just the token part, not the query string
                url_parts = magic_link.split('?token=')
                if len(url_parts) > 1:
                    invitation.token = url_parts[1]  # Extract token from query parameter
                else:
                    # Fallback: use a short token if URL parsing fails
                    invitation.token = magic_link.split('/')[-1][:500]  # Limit to 500 chars
                invitation.save()
                
                # Log invitation creation
                self.audit_log.log_event(
                    event_type='admin_action',
                    message=f"Invitation created for {email} to tenant {tenant.name}",
                    user=invited_by,
                    tenant=tenant,
                    severity='low',
                    details={
                        'invitation_id': str(invitation.id),
                        'email': email,
                        'role': role,
                        'expires_at': expires_at.isoformat(),
                        'custom_message': custom_message
                    }
                )
                
                logger.info(f"✅ Created invitation for {email} to {tenant.name}")
                return invitation
                
        except Exception as e:
            logger.error(f"❌ Failed to create invitation: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to create invitation for {email}: {str(e)}",
                user=invited_by,
                tenant=tenant,
                severity='high',
                details={'error': str(e), 'email': email, 'role': role}
            )
            raise
    
    def create_bulk_invites(self, tenant: Tenant, invite_data: List[Dict[str, Any]],
                          invited_by: Optional[User] = None) -> List[Invitation]:
        """
        Create multiple user invitations.
        
        Args:
            tenant: Tenant to invite users to
            invite_data: List of dictionaries containing invite information
            invited_by: User who sent the invitations
            
        Returns:
            List of created Invitation instances
        """
        try:
            with transaction.atomic():
                invitations = []
                
                for invite_info in invite_data:
                    email = invite_info['email']
                    role = invite_info.get('role', 'member')
                    custom_message = invite_info.get('custom_message')
                    expires_hours = invite_info.get('expires_hours')
                    
                    try:
                        invitation = self.create_invite(
                            tenant=tenant,
                            email=email,
                            role=role,
                            invited_by=invited_by,
                            custom_message=custom_message,
                            expires_hours=expires_hours
                        )
                        invitations.append(invitation)
                        
                    except ValidationError as e:
                        logger.warning(f"⚠️ Skipped invalid invitation for {email}: {e}")
                        continue
                
                # Log bulk invitation creation
                self.audit_log.log_event(
                    event_type='admin_action',
                    message=f"Bulk invitations created for {len(invitations)} users to tenant {tenant.name}",
                    user=invited_by,
                    tenant=tenant,
                    severity='low',
                    details={
                        'total_invitations': len(invitations),
                        'requested_count': len(invite_data),
                        'successful_count': len(invitations)
                    }
                )
                
                logger.info(f"✅ Created {len(invitations)} bulk invitations for {tenant.name}")
                return invitations
                
        except Exception as e:
            logger.error(f"❌ Failed to create bulk invitations: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to create bulk invitations: {str(e)}",
                user=invited_by,
                tenant=tenant,
                severity='high',
                details={'error': str(e), 'invite_count': len(invite_data)}
            )
            raise
    
    def send_invite_email(self, invitation: Invitation, 
                         custom_message: Optional[str] = None) -> bool:
        """
        Send invitation email with magic link.
        
        Args:
            invitation: The invitation to send
            custom_message: Custom message to include in email
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            # Generate magic link
            magic_link = self._generate_magic_link(invitation)
            
            # Prepare email context
            context = {
                'invitation': invitation,
                'tenant': invitation.tenant_id,
                'magic_link': magic_link,
                'expires_at': invitation.expires_at,
                'custom_message': custom_message,
                'inviter_name': invitation.inviter.name if invitation.inviter else 'Administrator'
            }
            
            # Render email templates
            subject = f"Invitation to join {invitation.tenant_id.name}"
            html_message = render_to_string('emails/invitation.html', context)
            plain_message = render_to_string('emails/invitation.txt', context)
            
            # Log email backend being used
            logger.info(f"📧 Sending invitation email to {invitation.email} using backend: {settings.EMAIL_BACKEND}")
            
            # Send email
            try:
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[invitation.email],
                    html_message=html_message,
                    fail_silently=False
                )
                
                # Log email sent
                self.audit_log.log_event(
                    event_type='admin_action',
                    message=f"Invitation email sent to {invitation.email}",
                    user=invitation.inviter,
                    tenant=invitation.tenant_id,
                    severity='low',
                    details={
                        'invitation_id': str(invitation.id),
                        'email': invitation.email,
                        'magic_link': magic_link,
                        'email_backend': settings.EMAIL_BACKEND
                    }
                )
                
                # Check if using console backend
                if 'console' in settings.EMAIL_BACKEND.lower():
                    logger.warning(f"⚠️ Using console email backend - email was printed to console, not actually sent to {invitation.email}")
                
                logger.info(f"✅ Invitation email sent to {invitation.email}")
                return True
            except Exception as email_error:
                logger.error(f"❌ Failed to send email via {settings.EMAIL_BACKEND}: {email_error}")
                raise  # Re-raise to be caught by outer exception handler
            
        except Exception as e:
            logger.error(f"❌ Failed to send invitation email: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to send invitation email to {invitation.email}: {str(e)}",
                user=invitation.inviter,
                tenant=invitation.tenant_id,
                severity='medium',
                details={'error': str(e), 'invitation_id': str(invitation.id)}
            )
            return False
    
    def validate_invite_token(self, token: str) -> Tuple[bool, Optional[Invitation], Optional[str]]:
        """
        Validate an invitation token and return the invitation if valid.
        
        Args:
            token: The invitation token to validate
            
        Returns:
            Tuple of (is_valid, invitation, error_message)
        """
        try:
            # Decode JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # Extract invitation ID
            invitation_id = payload.get('invitation_id')
            if not invitation_id:
                return False, None, "Invalid token format"
            
            # Get invitation
            try:
                invitation = Invitation.objects.get(id=invitation_id)
            except Invitation.DoesNotExist:
                return False, None, "Invitation not found"
            
            # Check if invitation is still pending
            if invitation.state != Invitation.State.PENDING:
                return False, invitation, f"Invitation has already been {invitation.state}"
            
            # Check if invitation has expired
            if invitation.expires_at < timezone.now():
                invitation.state = Invitation.State.EXPIRED
                invitation.save()
                return False, invitation, "Invitation has expired"
            
            return True, invitation, None
            
        except jwt.ExpiredSignatureError:
            return False, None, "Token has expired"
        except jwt.InvalidTokenError:
            return False, None, "Invalid token"
        except Exception as e:
            logger.error(f"❌ Failed to validate invite token: {e}")
            return False, None, f"Token validation error: {str(e)}"
    
    def accept_invite(self, invitation: Invitation, user_data: Dict[str, Any],
                     ip_address: Optional[str] = None) -> Tuple[bool, Optional[User], Optional[str]]:
        """
        Accept an invitation and create the user account.
        
        Args:
            invitation: The invitation to accept
            user_data: User data for account creation
            ip_address: IP address of the user accepting the invitation
            
        Returns:
            Tuple of (success, user, error_message)
        """
        try:
            with transaction.atomic():
                # Validate invitation is still valid
                is_valid, _, error = self.validate_invite_token(invitation.token)
                if not is_valid:
                    return False, None, error
                
                # Check if user already exists
                existing_user = User.objects.filter(email=invitation.email).first()
                if existing_user:
                    # User exists, check if membership already exists
                    from api.models import TenantMembership
                    membership, created = TenantMembership.objects.get_or_create(
                        user=existing_user,
                        tenant=invitation.tenant_id,
                        defaults={
                            'role': 'member',  # Default role for existing users
                            'is_active': True,
                            'invited_by': invitation.inviter
                        }
                    )
                    
                    # If membership already existed, update it
                    if not created:
                        # Update existing membership
                        membership.is_active = True
                        if not membership.invite_accepted_at:
                            membership.invite_accepted_at = timezone.now()
                        if invitation.inviter and not membership.invited_by:
                            membership.invited_by = invitation.inviter
                        membership.save()
                        logger.info(f"✅ Updated existing membership for {existing_user.email} in {invitation.tenant_id.name}")
                    else:
                        logger.info(f"✅ Created new membership for {existing_user.email} in {invitation.tenant_id.name}")
                    
                    # Mark invitation as accepted
                    invitation.state = Invitation.State.ACCEPTED
                    invitation.save()
                    
                    # Log invitation acceptance
                    self.audit_log.log_event(
                        event_type='user_created',
                        message=f"Existing user {existing_user.email} joined tenant {invitation.tenant_id.name}",
                        user=existing_user,
                        tenant=invitation.tenant_id,
                        severity='low',
                        details={
                            'invitation_id': str(invitation.id),
                            'membership_id': str(membership.id),
                            'membership_created': created,
                            'ip_address': ip_address
                        }
                    )
                    
                    logger.info(f"✅ Existing user {existing_user.email} joined {invitation.tenant_id.name}")
                    return True, existing_user, None
                
                # Create new user
                from api.services.user_service import UserService
                user_service = UserService()
                
                user = user_service.create_user_from_invite(
                    invitation=invitation,
                    user_data=user_data,
                    ip_address=ip_address
                )
                
                # Mark invitation as accepted
                invitation.state = Invitation.State.ACCEPTED
                invitation.save()
                
                # Log invitation acceptance
                self.audit_log.log_event(
                    event_type='user_created',
                        message=f"New user {user.email} created and joined tenant {invitation.tenant_id.name}",
                    user=user,
                    tenant=invitation.tenant_id,
                    severity='low',
                    details={
                        'invitation_id': str(invitation.id),
                        'user_id': str(user.id),
                        'ip_address': ip_address
                    }
                )
                
                logger.info(f"✅ New user {user.email} created and joined {invitation.tenant_id.name}")
                return True, user, None
                
        except Exception as e:
            logger.error(f"❌ Failed to accept invitation: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to accept invitation: {str(e)}",
                tenant=invitation.tenant_id,
                severity='high',
                details={'error': str(e), 'invitation_id': str(invitation.id)}
            )
            return False, None, f"Failed to accept invitation: {str(e)}"
    
    def revoke_invite(self, invitation: Invitation, revoked_by: Optional[User] = None) -> bool:
        """
        Revoke an invitation.
        
        Args:
            invitation: The invitation to revoke
            revoked_by: User who revoked the invitation
            
        Returns:
            bool: True if invitation was revoked successfully
        """
        try:
            with transaction.atomic():
                # Check if invitation can be revoked
                if invitation.state != Invitation.State.PENDING:
                    raise ValidationError(f"Cannot revoke invitation in state: {invitation.state}")
                
                # Revoke invitation
                invitation.state = Invitation.State.REVOKED
                invitation.save()
                
                # Log invitation revocation
                self.audit_log.log_event(
                    event_type='admin_action',
                    message=f"Invitation revoked for {invitation.email}",
                    user=revoked_by,
                    tenant=invitation.tenant_id,
                    severity='low',
                    details={
                        'invitation_id': str(invitation.id),
                        'email': invitation.email,
                        'revoked_by': revoked_by.email if revoked_by else None
                    }
                )
                
                logger.info(f"✅ Invitation revoked for {invitation.email}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to revoke invitation: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to revoke invitation: {str(e)}",
                user=revoked_by,
                tenant=invitation.tenant_id,
                severity='medium',
                details={'error': str(e), 'invitation_id': str(invitation.id)}
            )
            raise
    
    def cleanup_expired_invites(self, tenant: Optional[Tenant] = None) -> int:
        """
        Clean up expired invitations.
        
        Args:
            tenant: Tenant to clean up invites for (None for all tenants)
            
        Returns:
            int: Number of invitations cleaned up
        """
        try:
            queryset = Invitation.objects.filter(
                state=Invitation.State.PENDING,
                expires_at__lt=timezone.now()
            )
            
            if tenant:
                queryset = queryset.filter(tenant_id=tenant.id)
            
            expired_count = queryset.count()
            
            # Mark as expired
            queryset.update(state=Invitation.State.EXPIRED)
            
            # Log cleanup
            self.audit_log.log_event(
                event_type='admin_action',
                message=f"Cleaned up {expired_count} expired invitations",
                tenant=tenant,
                severity='low',
                details={'expired_count': expired_count}
            )
            
            logger.info(f"✅ Cleaned up {expired_count} expired invitations")
            return expired_count
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup expired invitations: {e}")
            raise
    
    def get_tenant_invites(self, tenant: Tenant, status: Optional[str] = None) -> List[Invitation]:
        """
        Get all invitations for a tenant.
        
        Args:
            tenant: Tenant to get invitations for
            status: Filter by invitation status
            
        Returns:
            List of Invitation instances
        """
        try:
            queryset = Invitation.objects.filter(tenant_id=tenant.id)
            
            if status:
                queryset = queryset.filter(state=status)
            
            return list(queryset.order_by('-inserted_at'))
            
        except Exception as e:
            logger.error(f"❌ Failed to get tenant invitations: {e}")
            raise
    
    def _generate_magic_link(self, invitation: Invitation) -> str:
        """Generate a JWT-based magic link for the invitation."""
        try:
            # Create JWT payload
            # Note: invitation.tenant_id gives us the Tenant object (from ForeignKey field named tenant_id)
            payload = {
                'invitation_id': str(invitation.id),
                'email': invitation.email,
                'tenant_id': str(invitation.tenant_id.id),
                'exp': int((invitation.expires_at).timestamp()),
                'iat': int(timezone.now().timestamp())
            }
            
            # Generate JWT token
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            
            # Create magic link URL
            base_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
            magic_link = f"{base_url}/accept-invite?token={token}"
            
            return magic_link
            
        except Exception as e:
            logger.error(f"❌ Failed to generate magic link: {e}")
            raise
    
    def _validate_invite_data(self, tenant: Tenant, email: str, role: str) -> None:
        """Validate invitation data."""
        # Validate email format
        if not email or '@' not in email:
            raise ValidationError("Invalid email address")
        
        # Validate role
        valid_roles = ['owner', 'admin', 'member', 'guest']
        if role not in valid_roles:
            raise ValidationError(f"Invalid role: {role}. Must be one of {valid_roles}")
        
        # Check tenant limits
        if tenant.is_at_user_limit:
            raise ValidationError(f"Tenant has reached user limit ({tenant.max_users})")
        
        # Check if tenant allows registration
        if not tenant.allow_registration:
            raise ValidationError("Tenant does not allow user registration")
