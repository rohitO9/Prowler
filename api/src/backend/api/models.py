import json
import re
import base64
import uuid
import logging
from django.db import models
from django.utils.translation import gettext_lazy as _
from uuid import UUID, uuid4
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.core.validators import MinLengthValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import threading

# Thread-local storage for current tenant
_thread_locals = threading.local()

def set_current_tenant(tenant):
    """Set current tenant in thread-local storage"""
    _thread_locals.tenant = tenant

def get_current_tenant():
    """Get current tenant from thread-local storage"""
    return getattr(_thread_locals, 'tenant', None)

def clear_current_tenant():
    """Clear current tenant from thread-local storage"""
    if hasattr(_thread_locals, 'tenant'):
        del _thread_locals.tenant
from django_celery_beat.models import PeriodicTask
from django_celery_results.models import TaskResult
from psqlextra.manager import PostgresManager
from psqlextra.models import PostgresPartitionedModel
from psqlextra.types import PostgresPartitioningMethod
from uuid6 import uuid7

from api.db_utils import (
    CustomUserManager,
    FindingDeltaEnumField,
    IntegrationTypeEnumField,
    InvitationStateEnumField,
    MemberRoleEnumField,
    ProviderEnumField,
    ProviderSecretTypeEnumField,
    ScanTriggerEnumField,
    SeverityEnumField,
    StateEnumField,
    StatusEnumField,
    enum_to_choices,
    generate_random_token,
    one_week_from_now,
    DB_USER,
    POSTGRES_TENANT_VAR,
)
from api.exceptions import ModelValidationError
# from api.api_rls import (
#     BaseSecurityConstraint,
#     RowLevelSecurityConstraint,
#     RowLevelSecurityProtectedModel,
# )
# from api.models import Tenant


from prowler.lib.check.models import Severity
from cryptography.fernet import Fernet

# Encryption setup
key = settings.SECRETS_ENCRYPTION_KEY
try:
    decoded_key = base64.urlsafe_b64decode(key)
    print(f"Decoded key length: {len(decoded_key)}")  # Should be 32 bytes
except Exception as e:
    print(f"Error decoding key: {e}")

load_dotenv()
print("Loaded key from settings:", os.getenv("SECRETS_ENCRYPTION_KEY"))

# Initialize Fernet with the key
fernet = Fernet(os.getenv("SECRETS_ENCRYPTION_KEY"))

# Convert Prowler Severity enum to Django TextChoices
SeverityChoices = enum_to_choices(Severity)

# remove top-level import

# Inside your model class or function that needs the base class:
# def get_row_level_security_protected_model():
#     from api.api_rls.row_level_security_protected_model import RowLevelSecurityProtectedModel
#     return RowLevelSecurityProtectedModel

def get_row_level_security_constraint():
    from api.api_rls import RowLevelSecurityConstraint
    return RowLevelSecurityConstraint

RowLevelSecurityConstraint = get_row_level_security_constraint()




def get_row_level_security_protected_model():
    from api.api_rls.row_level_security_protected_model import RowLevelSecurityProtectedModel
    return RowLevelSecurityProtectedModel

RowLevelSecurityProtectedModel = get_row_level_security_protected_model()


class StatusChoices(models.TextChoices):
    """
    This list is based on the finding status in the Prowler CLI.

    However, it adds another state, MUTED, which is not in the CLI.
    """

    FAIL = "FAIL", _("Fail")
    PASS = "PASS", _("Pass")
    MANUAL = "MANUAL", _("Manual")


class StateChoices(models.TextChoices):
    AVAILABLE = "available", _("Available")
    SCHEDULED = "scheduled", _("Scheduled")
    EXECUTING = "executing", _("Executing")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")
    CANCELLED = "cancelled", _("Cancelled")


class PermissionChoices(models.TextChoices):
    """
    Represents the different permission states that a role can have.

    Attributes:
        UNLIMITED: Indicates that the role possesses all permissions.
        LIMITED: Indicates that the role has some permissions but not all.
        NONE: Indicates that the role does not have any permissions.
    """

    UNLIMITED = "unlimited", _("Unlimited permissions")
    LIMITED = "limited", _("Limited permissions")
    NONE = "none", _("No permissions")


class ActiveProviderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(self.active_provider_filter())

    def active_provider_filter(self):
        if self.model is Provider:
            return Q(is_deleted=False)
        elif self.model in [Finding, ComplianceOverview, ScanSummary]:
            return Q(scan__provider__is_deleted=False)
        else:
            return Q(provider__is_deleted=False)


class ActiveProviderPartitionedManager(PostgresManager, ActiveProviderManager):
    def get_queryset(self):
        return super().get_queryset().filter(self.active_provider_filter())
def get_base_security_constraint():
    from api.api_rls import BaseSecurityConstraint
    return BaseSecurityConstraint    



class Tenant(models.Model):
    """
    Enhanced Tenant model with comprehensive multi-tenant isolation.
    Each tenant represents a completely isolated organization with strict security constraints.
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    
    # Core tenant identification with strict validation
    name = models.CharField(
        max_length=100, 
        unique=True,
        db_index=True,
        help_text="Organization name (must be unique)",
        validators=[MinLengthValidator(2)]
    )
    subdomain = models.CharField(
        max_length=63, 
        unique=True,
        db_index=True,
        help_text="Subdomain for tenant isolation (e.g., 'company1')",
        validators=[
            RegexValidator(
                regex=r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$',
                message='Subdomain must be lowercase alphanumeric with hyphens, no spaces',
                code='invalid_subdomain'
            )
        ]
    )
    domain = models.CharField(
        max_length=253, 
        blank=True, 
        null=True,
        unique=True,
        help_text="Custom domain (optional, must be unique if provided)"
    )
    
    # Tenant configuration with security defaults
    is_active = models.BooleanField(
        default=True, 
        db_index=True,
        help_text="Whether tenant is active - inactive tenants cannot login"
    )
    is_verified = models.BooleanField(
        default=False, 
        db_index=True,
        help_text="Whether tenant is verified by admin"
    )
    
    # Contact information
    contact_email = models.EmailField(
        help_text="Primary contact email for tenant"
    )
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    # Branding
    logo_url = models.URLField(blank=True, null=True)
    theme_color = models.CharField(
        max_length=7, 
        default="#3B82F6", 
        validators=[RegexValidator(
            regex=r'^#[0-9A-Fa-f]{6}$',
            message='Theme color must be a valid hex color code'
        )],
        help_text="Primary theme color"
    )
    secondary_color = models.CharField(
        max_length=7, 
        default="#1E40AF",
        validators=[RegexValidator(
            regex=r'^#[0-9A-Fa-f]{6}$',
            message='Secondary color must be a valid hex color code'
        )],
        help_text="Secondary theme color"
    )
    
    # Subscription & billing with limits
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    subscription_status = models.CharField(
        max_length=20, 
        choices=[
            ('trial', 'Trial'),
            ('active', 'Active'),
            ('suspended', 'Suspended'),
            ('cancelled', 'Cancelled'),
        ],
        default='trial',
        db_index=True
    )
    max_users = models.PositiveIntegerField(
        default=5,
        help_text="Maximum users allowed for this tenant"
    )
    max_providers = models.PositiveIntegerField(
        default=3,
        help_text="Maximum cloud providers allowed"
    )
    
    # Security settings with strict defaults
    allow_registration = models.BooleanField(
        default=True, 
        help_text="Allow new user registration"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    require_email_verification = models.BooleanField(
        default=True,
        help_text="Require email verification for new users"
    )
    session_timeout_minutes = models.PositiveIntegerField(
        default=480,
        help_text="Session timeout in minutes"
    )
    max_failed_login_attempts = models.PositiveIntegerField(
        default=5,
        help_text="Maximum failed login attempts before account lockout"
    )
    lockout_duration_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Account lockout duration in minutes"
    )
    
    # Audit fields
    created_by = models.ForeignKey(
        'User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_tenants'
    )
    last_activity = models.DateTimeField(auto_now=True)
    last_security_scan = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tenants"
        constraints = [
            models.UniqueConstraint(
                fields=['subdomain'], 
                name='unique_tenant_subdomain',
                violation_error_message='A tenant with this subdomain already exists'
            ),
            models.UniqueConstraint(
                fields=['name'], 
                name='unique_tenant_name',
                violation_error_message='A tenant with this name already exists'
            ),
            models.UniqueConstraint(
                fields=['domain'], 
                name='unique_tenant_domain',
                violation_error_message='A tenant with this domain already exists'
            ),
            models.CheckConstraint(
                check=models.Q(subdomain__regex=r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'),
                name='valid_subdomain_format'
            ),
            models.CheckConstraint(
                check=models.Q(max_users__gte=1),
                name='tenant_max_users_positive'
            ),
            models.CheckConstraint(
                check=models.Q(session_timeout_minutes__gte=15),
                name='tenant_session_timeout_minimum'
            )
        ]
        indexes = [
            models.Index(fields=['subdomain'], name='idx_tenant_subdomain'),
            models.Index(fields=['is_active'], name='idx_tenant_active'),
            models.Index(fields=['subscription_status'], name='idx_tenant_subscription'),
            models.Index(fields=['created_at'], name='idx_tenant_created'),
            models.Index(fields=['last_activity'], name='idx_tenant_activity'),
        ]
        ordering = ['name']

    class JSONAPIMeta:
        resource_name = "tenants"

    def save(self, *args, **kwargs):
        # Always force subdomain to lowercase
        if self.subdomain:
            self.subdomain = self.subdomain.lower().strip()
        
        # Auto-generate subdomain from name if not provided
        if not self.subdomain and self.name:
            import re
            self.subdomain = re.sub(r'[^a-z0-9-]', '', self.name.lower().replace(' ', '-'))
        
        super().save(*args, **kwargs)

    def clean(self):
        """Validate tenant data"""
        from django.core.exceptions import ValidationError
        
        if self.subdomain:
            # Reserved subdomains
            reserved = ['www', 'api', 'admin', 'app', 'mail', 'smtp', 'ftp', 'localhost', 'test', 'staging']
            if self.subdomain.lower() in reserved:
                raise ValidationError({
                    'subdomain': f'Subdomain "{self.subdomain}" is reserved and cannot be used'
                })
        
        # Validate domain format if provided
        if self.domain:
            import re
            domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
            if not re.match(domain_pattern, self.domain):
                raise ValidationError({
                    'domain': 'Invalid domain format'
                })

    def __str__(self):
        return f"{self.name} ({self.subdomain})"

    def get_absolute_url(self):
        """Get the tenant's subdomain URL"""
        if self.domain:
            return f"https://{self.domain}"
        return f"https://{self.subdomain}.localhost"  # Development URL

    def is_trial_expired(self):
        """Check if trial period has expired"""
        if not self.trial_ends_at:
            return False
        return timezone.now() > self.trial_ends_at

    def can_access_feature(self, feature_name):
        """Check if tenant can access a specific feature"""
        if self.subscription_status == 'active':
            return True
        if self.subscription_status == 'trial' and not self.is_trial_expired():
            return True
        return False

    @property
    def user_count(self):
        """Get number of users in this tenant"""
        return self.members.filter(is_active=True).count()

    @property
    def is_at_user_limit(self):
        """Check if tenant has reached user limit"""
        return self.user_count >= self.max_users

    def can_add_user(self):
        """Check if tenant can add another user"""
        return self.is_active and not self.is_at_user_limit

    def get_security_summary(self):
        """Get security summary for the tenant"""
        return {
            'total_users': self.user_count,
            'max_users': self.max_users,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'last_activity': self.last_activity,
            'session_timeout': self.session_timeout_minutes,
            'max_failed_attempts': self.max_failed_login_attempts
        }


class TenantMembership(models.Model):
    """
    Many-to-many relationship for users who belong to multiple tenants.
    Enhanced with comprehensive permissions and security features.
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='tenant_memberships')
    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE, related_name='tenant_memberships')
    role = models.CharField(
        max_length=50,
        default='member',
        choices=[
            ('owner', 'Owner'),
            ('admin', 'Administrator'),
            ('auditor', 'Auditor'),
            ('viewer', 'Viewer'),
        ]
    )
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invited_memberships'
    )
    
    # Enhanced permissions
    can_invite_users = models.BooleanField(default=False)
    can_manage_settings = models.BooleanField(default=False)
    can_view_analytics = models.BooleanField(default=True)
    can_manage_users = models.BooleanField(default=False)
    can_manage_billing = models.BooleanField(default=False)
    can_manage_providers = models.BooleanField(default=False)
    can_manage_integrations = models.BooleanField(default=False)
    can_manage_scans = models.BooleanField(default=False)
    unlimited_visibility = models.BooleanField(default=False)
    
    # Prowler-Specific Permissions
    can_run_scans = models.BooleanField(default=False, help_text="Can run security scans")
    can_export_reports = models.BooleanField(default=False, help_text="Can export compliance reports")
    
    # Invitation fields
    invited_at = models.DateTimeField(null=True, blank=True, help_text="When user was invited")
    invite_accepted_at = models.DateTimeField(null=True, blank=True, help_text="When user accepted invitation")
    invite_token = models.CharField(max_length=500, blank=True, db_index=True, help_text="JWT invite token")
    invite_expires_at = models.DateTimeField(null=True, blank=True, help_text="When invite expires")

    class Meta:
        db_table = 'tenant_memberships'
        unique_together = [['user', 'tenant']]
        indexes = [
            models.Index(fields=['user', 'tenant'], name='idx_membership_user_tenant'),
            models.Index(fields=['tenant', 'is_active']),
            models.Index(fields=['role']),
            models.Index(fields=['invite_token']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.tenant.name} ({self.role})"

    def has_permission(self, permission):
        """Check if membership has a specific permission"""
        permission_map = {
            'invite_users': self.can_invite_users,
            'manage_settings': self.can_manage_settings,
            'view_analytics': self.can_view_analytics,
            'manage_users': self.can_manage_users,
            'manage_billing': self.can_manage_billing,
            'manage_providers': self.can_manage_providers,
            'manage_integrations': self.can_manage_integrations,
            'manage_scans': self.can_manage_scans,
            'unlimited_visibility': self.unlimited_visibility,
            'run_scans': self.can_run_scans,
            'export_reports': self.can_export_reports,
        }
        return permission_map.get(permission, False)

    def is_owner_or_admin(self):
        """Check if user is owner or admin of the tenant"""
        return self.role in ['owner', 'admin']

    def get_permission_state(self):
        """Get permission state for this membership"""
        permissions = [
            self.can_invite_users,
            self.can_manage_settings,
            self.can_view_analytics,
            self.can_manage_users,
            self.can_manage_billing,
            self.can_manage_providers,
            self.can_manage_integrations,
            self.can_manage_scans,
        ]
        
        if all(permissions):
            return 'unlimited'
        elif not any(permissions):
            return 'none'
        else:
            return 'limited'


def apply_constraints_to_model(model_class):
    BaseSecurityConstraint = get_base_security_constraint()
    model_class._meta.constraints = [
        BaseSecurityConstraint(
            name="statements_on_constraints",
            statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
        )
    ]


# Call after the Tenant class is defined
apply_constraints_to_model(Tenant)




class User(AbstractUser):
    """
    Custom user model with tenant association.
    Email is globally unique - one user account across all tenants.
    Enhanced with comprehensive multi-tenant support and security.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False
    )
    
    email = models.EmailField(
        unique=True,  # One email = one account globally
        db_index=True,
        help_text="Email address (case insensitive)"
    )
    
    username = models.CharField(
        max_length=150,
        unique=True,  # Keep username unique
        blank=True,
        null=True,
        help_text="Username (auto-generated from email if not provided)"
    )
    
    name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Full name of the user"
    )
    
    primary_tenant = models.ForeignKey(
        'Tenant',
        on_delete=models.PROTECT,  # Don't delete tenant if users exist
        related_name='users',
        help_text='Primary tenant this user belongs to'
    )
    
    # For future: multi-tenant membership
    tenants = models.ManyToManyField(
        'Tenant',
        through='TenantMembership',
        through_fields=('user', 'tenant'),
        related_name='members',
        blank=True,
        help_text='All tenants this user has access to'
    )
    
    # Enhanced security fields
    is_verified = models.BooleanField(
        default=False, 
        db_index=True,
        help_text="Email verification status"
    )
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of consecutive failed login attempts"
    )
    locked_until = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    two_factor_enabled = models.BooleanField(
        default=False,
        help_text="Whether two-factor authentication is enabled"
    )
    two_factor_secret = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text="TOTP secret for 2FA"
    )
    
    # Security audit fields
    last_security_scan = models.DateTimeField(null=True, blank=True)
    security_notes = models.TextField(blank=True, null=True)
    
    # Free trial fields (deprecated - moved to tenant level)
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    is_trial_active = models.BooleanField(default=False)
    
    # Azure AD Integration
    azure_id = models.CharField(
        max_length=255, 
        unique=True, 
        null=True, 
        blank=True, 
        db_index=True,
        help_text="Azure AD User ID"
    )
    azure_tenant_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="Azure AD Tenant ID"
    )
    azure_upn = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="User Principal Name"
    )
    
    # Profile Data (synced from Azure AD)
    department = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Department from Azure AD"
    )
    job_title = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Job title from Azure AD"
    )
    phone_number = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Phone number from Azure AD"
    )
    manager_azure_id = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Manager's Azure AD ID"
    )
    
    # Status
    is_sso_user = models.BooleanField(
        default=False,
        help_text="Whether user was created via SSO"
    )
    deactivated_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When user was deactivated"
    )
    deactivation_reason = models.CharField(
        max_length=50, 
        choices=[
            ('REMOVED_FROM_AZURE', 'Removed from Azure'),
            ('DISABLED_IN_AZURE', 'Disabled in Azure'),
            ('MANUAL', 'Manual'),
            ('SUBSCRIPTION_EXPIRED', 'Subscription Expired')
        ], 
        blank=True,
        help_text="Reason for deactivation"
    )
    
    # Timestamps
    invited_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When user was invited"
    )
    accepted_invite_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When user accepted invitation"
    )
    first_login_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When user first logged in"
    )
    onboarding_completed_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When user completed onboarding"
    )

    class Meta:
        db_table = 'users'
        constraints = [
            models.CheckConstraint(
                check=models.Q(failed_login_attempts__gte=0),
                name='user_failed_attempts_positive'
            )
        ]
        indexes = [
            models.Index(fields=['email'], name='idx_user_email'),
            models.Index(fields=['primary_tenant'], name='idx_user_tenant'),
            models.Index(fields=['is_active'], name='idx_user_active'),
            models.Index(fields=['is_verified'], name='idx_user_verified'),
            models.Index(fields=['last_login'], name='idx_user_last_login'),
            models.Index(fields=['azure_id'], name='idx_user_azure_id'),
            models.Index(fields=['is_sso_user'], name='idx_user_sso_user'),
        ]

    class JSONAPIMeta:
        resource_name = "users"

    def save(self, *args, **kwargs):
        # Auto-generate username from email if not provided
        if not self.username:
            self.username = self.email
        
        # Auto-generate name from first_name and last_name if not provided
        if not self.name and (self.first_name or self.last_name):
            self.name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        
        # Normalize email
        if self.email:
            self.email = self.email.strip().lower()
        
        # Disabled: Membership is created AFTER user save, causing chicken-egg problem
        # TODO: Re-enable after refactoring registration flow
        # if self.pk and self.primary_tenant_id and not self.is_superuser:
        #     if not self.is_member_of_tenant(self.primary_tenant_id):
        #         raise ValidationError("User must be a member of their primary tenant")
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.primary_tenant.name if self.primary_tenant else 'No Tenant'})"

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def is_member_of_tenant(self, tenant_id):
        """Check if user is a member of the specified tenant"""
        # Debug: Log the check
        memberships = self.tenant_memberships.filter(tenant_id=tenant_id, is_active=True)
        logger.info(f"🔍 [USER] Checking membership for user {self.email} in tenant {tenant_id}")
        logger.info(f"🔍 [USER] Found {memberships.count()} active memberships")
        for membership in memberships:
            logger.info(f"🔍 [USER] Membership: {membership.id}, tenant: {membership.tenant_id}, active: {membership.is_active}")
        
        return memberships.exists()

    def get_tenant_role(self, tenant_id):
        """Get user's role in a specific tenant"""
        try:
            membership = self.tenant_memberships.get(tenant_id=tenant_id, is_active=True)
            return membership.role
        except TenantMembership.DoesNotExist:
            return None

    def can_access_tenant(self, tenant_id):
        """Check if user can access a specific tenant with enhanced security"""
        if not self.is_active:
            return False
        
        # Superusers can access any tenant
        if self.is_superuser:
            return True
            
        # Check if user is locked
        if self.is_locked():
            return False
            
        return self.is_member_of_tenant(tenant_id)
    
    def get_tenant_memberships(self):
        """Get all active tenant memberships for this user"""
        return self.tenant_memberships.filter(is_active=True)
    
    def get_tenant_ids(self):
        """Get list of tenant IDs this user belongs to"""
        return list(self.tenant_memberships.filter(is_active=True).values_list('tenant_id', flat=True))

    def is_locked(self):
        """Check if user account is locked"""
        if not self.locked_until:
            return False
        return timezone.now() < self.locked_until

    def lock_account(self, duration_minutes=30, reason="Too many failed login attempts"):
        """Lock user account for specified duration with reason"""
        self.locked_until = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        self.security_notes = f"{self.security_notes or ''}\n{timezone.now()}: Account locked - {reason}".strip()
        self.save(update_fields=['locked_until', 'security_notes'])

    def unlock_account(self):
        """Unlock user account"""
        self.locked_until = None
        self.failed_login_attempts = 0
        self.security_notes = f"{self.security_notes or ''}\n{timezone.now()}: Account unlocked".strip()
        self.save(update_fields=['locked_until', 'failed_login_attempts', 'security_notes'])

    def record_failed_login(self, ip_address=None):
        """Record a failed login attempt with IP tracking"""
        self.failed_login_attempts += 1
        
        # Get tenant-specific lockout settings
        if self.primary_tenant:
            max_attempts = self.primary_tenant.max_failed_login_attempts
            lockout_duration = self.primary_tenant.lockout_duration_minutes
        else:
            max_attempts = 5
            lockout_duration = 30
            
        if self.failed_login_attempts >= max_attempts:
            self.lock_account(duration_minutes=lockout_duration)
        else:
            self.save(update_fields=['failed_login_attempts'])

    def record_successful_login(self, ip_address=None):
        """Record a successful login with security tracking"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = timezone.now()
        if ip_address:
            self.last_login_ip = ip_address
        self.save(update_fields=['failed_login_attempts', 'locked_until', 'last_login', 'last_login_ip'])

    def get_security_summary(self):
        """Get comprehensive security summary for the user"""
        return {
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'is_locked': self.is_locked(),
            'failed_attempts': self.failed_login_attempts,
            'last_login': self.last_login,
            'last_login_ip': self.last_login_ip,
            'two_factor_enabled': self.two_factor_enabled,
            'tenant_count': self.get_tenant_memberships().count(),
            'primary_tenant': self.primary_tenant.name if self.primary_tenant else None
        }

    def has_permission_in_tenant(self, permission, tenant_id):
        """Check if user has specific permission in a tenant"""
        if not self.can_access_tenant(tenant_id):
            return False
            
        membership = self.tenant_memberships.filter(
            tenant_id=tenant_id, 
            is_active=True
        ).first()
        
        if not membership:
            return False
            
        return membership.has_permission(permission)


class Membership(models.Model):
    class RoleChoices(models.TextChoices):
        OWNER = "owner", _("Owner")
        MEMBER = "member", _("Member")

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="memberships",
        related_query_name="membership",
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="memberships",
        related_query_name="membership",
    )
    role = MemberRoleEnumField(choices=RoleChoices.choices, default=RoleChoices.MEMBER)
    date_joined = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        db_table = "memberships"

        constraints = [
            models.UniqueConstraint(
                fields=("user", "tenant"),
                name="unique_resources_by_membership",
            ),
        ]

    class JSONAPIMeta:
        resource_name = "memberships"


def apply_membership_constraints():
    BaseSecurityConstraint = get_base_security_constraint()
    Membership._meta.constraints.append(
        BaseSecurityConstraint(
            name="statements_on_tanent_contraints",
            statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
        )
    )

apply_membership_constraints()


class Provider(RowLevelSecurityProtectedModel):
    objects = ActiveProviderManager()
    all_objects = models.Manager()

    class ProviderChoices(models.TextChoices):
        AWS = "aws", _("AWS")
        AZURE = "azure", _("Azure")
        GCP = "gcp", _("GCP")
        KUBERNETES = "kubernetes", _("Kubernetes")
        M365 = "m365", _("M365")

    @staticmethod
    def validate_aws_uid(value):
        if not re.match(r"^\d{12}$", value):
            raise ModelValidationError(
                detail="AWS provider ID must be exactly 12 digits.",
                code="aws-uid",
                pointer="/data/attributes/uid",
            )

    @staticmethod
    def validate_azure_uid(value):
        try:
            val = UUID(value, version=4)
            if str(val) != value:
                raise ValueError
        except ValueError:
            raise ModelValidationError(
                detail="Azure provider ID must be a valid UUID.",
                code="azure-uid",
                pointer="/data/attributes/uid",
            )

    @staticmethod
    def validate_m365_uid(value):
        if not re.match(
            r"""^(?!-)[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.(?!-)[A-Za-z0-9]"""
            r"""(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\.[A-Za-z]{2,}$""",
            value,
        ):
            raise ModelValidationError(
                detail="M365 domain ID must be a valid domain.",
                code="m365-uid",
                pointer="/data/attributes/uid",
            )

    @staticmethod
    def validate_gcp_uid(value):
        if not re.match(r"^[a-z][a-z0-9-]{5,29}$", value):
            raise ModelValidationError(
                detail="GCP provider ID must be 6 to 30 characters, start with a letter, and contain only lowercase "
                "letters, numbers, and hyphens.",
                code="gcp-uid",
                pointer="/data/attributes/uid",
            )

    @staticmethod
    def validate_kubernetes_uid(value):
        if not re.match(
            r"^[a-zA-Z0-9][a-zA-Z0-9._@:\/-]{1,250}$",
            value,
        ):
            raise ModelValidationError(
                detail="The value must either be a valid Kubernetes UID (up to 63 characters, "
                "starting and ending with a lowercase letter or number, containing only "
                "lowercase alphanumeric characters and hyphens) or a valid AWS EKS Cluster ARN, GCP GKE Context Name or Azure AKS Cluster Name.",
                code="kubernetes-uid",
                pointer="/data/attributes/uid",
            )

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    is_deleted = models.BooleanField(default=False)
    provider = ProviderEnumField(
        choices=ProviderChoices.choices, default=ProviderChoices.AWS
    )
    uid = models.CharField(
        "Unique identifier for the provider, set by the provider",
        max_length=250,
        blank=False,
        validators=[MinLengthValidator(3)],
    )
    alias = models.CharField(
        blank=True, null=True, max_length=100, validators=[MinLengthValidator(3)]
    )
    connected = models.BooleanField(null=True, blank=True)
    connection_last_checked_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    scanner_args = models.JSONField(default=dict, blank=True)

    def clean(self):
        super().clean()
        getattr(self, f"validate_{self.provider}_uid")(self.uid)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        db_table = "providers"
        # Don't inherit from base class Meta to avoid constraint issues
        
        constraints = [
            models.UniqueConstraint(
                fields=("tenant_id", "provider", "uid", "is_deleted"),
                name="unique_provider_uids",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_provider_tenant",  # Unique name for this model
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

    class JSONAPIMeta:
        resource_name = "providers"

    def __str__(self):
        return f"{self.provider} - {self.uid}" + (f" ({self.alias})" if self.alias else "")

    def __repr__(self):
        return f"<Provider {self.id}: {self.provider} - {self.uid}>"


class ProviderGroup(RowLevelSecurityProtectedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    providers = models.ManyToManyField(
        Provider, through="ProviderGroupMembership", related_name="provider_groups"
    )

    class Meta:
        db_table = "provider_groups"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="unique_group_name_per_tenant",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_ProviderGroup",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

    class JSONAPIMeta:
        resource_name = "provider-groups"


class ProviderGroupMembership(RowLevelSecurityProtectedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    provider_group = models.ForeignKey(ProviderGroup, on_delete=models.CASCADE)
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE)
    inserted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "provider_group_memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["provider_id", "provider_group"],
                name="unique_provider_group_membership",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_ProviderGroupMembership",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

    class JSONAPIMeta:
        resource_name = "provider_groups-provider"


class Task(RowLevelSecurityProtectedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    task_runner_task = models.OneToOneField(
        TaskResult,
        on_delete=models.CASCADE,
        related_name="task",
        related_query_name="task",
        null=True,
        blank=True,
    )

    class Meta(RowLevelSecurityProtectedModel.Meta):
        db_table = "tasks"

        constraints = [
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_Task",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

        indexes = [
            models.Index(
                fields=["id", "task_runner_task"],
                name="tasks_id_trt_id_idx",
            ),
        ]

    class JSONAPIMeta:
        resource_name = "tasks"


class Scan(RowLevelSecurityProtectedModel):
    objects = ActiveProviderManager()
    all_objects = models.Manager()

    class TriggerChoices(models.TextChoices):
        SCHEDULED = "scheduled", _("Scheduled")
        MANUAL = "manual", _("Manual")

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(
        blank=True, null=True, max_length=100, validators=[MinLengthValidator(3)]
    )
    provider = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        related_name="scans",
        related_query_name="scan",
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="scans",
        related_query_name="scan",
        null=True,
        blank=True,
    )
    trigger = ScanTriggerEnumField(
        choices=TriggerChoices.choices,
    )
    state = StateEnumField(choices=StateChoices.choices, default=StateChoices.AVAILABLE)
    unique_resource_count = models.IntegerField(default=0)
    progress = models.IntegerField(default=0)
    scanner_args = models.JSONField(default=dict)
    duration = models.IntegerField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    next_scan_at = models.DateTimeField(null=True, blank=True)
    scheduler_task = models.ForeignKey(
        PeriodicTask, on_delete=models.CASCADE, null=True, blank=True
    )
    output_location = models.CharField(blank=True, null=True, max_length=200)

    # TODO: mutelist foreign key

    class Meta(RowLevelSecurityProtectedModel.Meta):
        db_table = "scans"

        constraints = [
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_Scan",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

        indexes = [
            models.Index(
                fields=["provider", "state", "trigger", "scheduled_at"],
                name="scans_prov_state_trig_sche_idx",
            ),
            models.Index(
                fields=["tenant_id", "provider_id", "state", "inserted_at"],
                name="scans_prov_state_insert_idx",
            ),
            models.Index(
                fields=["tenant_id", "provider_id", "state", "-inserted_at"],
                condition=Q(state=StateChoices.COMPLETED),
                name="scans_prov_state_ins_desc_idx",
            ),
        ]

    class JSONAPIMeta:
        resource_name = "scans"


class ResourceTag(RowLevelSecurityProtectedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    key = models.TextField(blank=False)
    value = models.TextField(blank=False)

    text_search = models.GeneratedField(
        expression=SearchVector("key", weight="A", config="simple")
        + SearchVector("value", weight="B", config="simple"),
        output_field=SearchVectorField(),
        db_persist=True,
        null=True,
        editable=False,
    )

    class Meta(RowLevelSecurityProtectedModel.Meta):
        db_table = "resource_tags"

        indexes = [
            GinIndex(fields=["text_search"], name="gin_resource_tags_search_idx"),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=("tenant_id", "key", "value"),
                name="unique_resource_tags_by_tenant_key_value",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_ResourceTag",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]


class Resource(RowLevelSecurityProtectedModel):
    objects = ActiveProviderManager()
    all_objects = models.Manager()

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    provider = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        related_name="resources",
        related_query_name="resource",
    )

    uid = models.TextField(
        "Unique identifier for the resource, set by the provider", blank=False
    )
    name = models.TextField("Name of the resource, as set in the provider", blank=False)
    region = models.TextField(
        "Location of the resource, as set by the provider", blank=False
    )
    service = models.TextField(
        "Service of the resource, as set by the provider", blank=False
    )
    type = models.TextField("Type of the resource, as set by the provider", blank=False)

    text_search = models.GeneratedField(
        expression=SearchVector("uid", weight="A", config="simple")
        + SearchVector("name", weight="B", config="simple")
        + SearchVector("region", weight="C", config="simple")
        + SearchVector("service", "type", weight="D", config="simple"),
        output_field=SearchVectorField(),
        db_persist=True,
        null=True,
        editable=False,
    )

    metadata = models.TextField(blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    partition = models.TextField(blank=True, null=True)

    # Relationships
    tags = models.ManyToManyField(
        ResourceTag,
        verbose_name="Tags associated with the resource, by provider",
        through="ResourceTagMapping",
    )

    def get_tags(self, tenant_id: str) -> dict:
        return {tag.key: tag.value for tag in self.tags.filter(tenant_id=tenant_id)}

    def clear_tags(self):
        self.tags.clear()
        self.save()

    def upsert_or_delete_tags(self, tags: list[ResourceTag] | None):
        if tags is None:
            self.clear_tags()
            return

        # Add new relationships with the tenant_id field
        for tag in tags:
            ResourceTagMapping.objects.update_or_create(
                tag=tag, resource=self, tenant_id=self.tenant_id
            )

        # Save the instance
        self.save()

    class Meta(RowLevelSecurityProtectedModel.Meta):
        db_table = "resources"

        indexes = [
            models.Index(
                fields=["uid", "region", "service", "name"],
                name="resource_uid_reg_serv_name_idx",
            ),
            models.Index(
                fields=["tenant_id", "service", "region", "type"],
                name="resource_tenant_metadata_idx",
            ),
            GinIndex(fields=["text_search"], name="gin_resources_search_idx"),
            models.Index(fields=["tenant_id", "id"], name="resources_tenant_id_idx"),
            models.Index(
                fields=["tenant_id", "provider_id"],
                name="resources_tenant_provider_idx",
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=("tenant_id", "provider_id", "uid"),
                name="unique_resources_by_provider",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_Resource",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

    class JSONAPIMeta:
        resource_name = "resources"


class ResourceTagMapping(RowLevelSecurityProtectedModel):
    # NOTE that we don't really need a primary key here,
    #      but everything is easier with django if we do
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    tag = models.ForeignKey(ResourceTag, on_delete=models.CASCADE)

    class Meta(RowLevelSecurityProtectedModel.Meta):
        db_table = "resource_tag_mappings"

        # django will automatically create indexes for:
        #   - resource_id
        #   - tag_id
        #   - tenant_id
        #   - id

        constraints = [
            models.UniqueConstraint(
                fields=("tenant_id", "resource_id", "tag_id"),
                name="unique_resource_tag_mappings_by_tenant",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_ResourceTagMapping",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

        indexes = [
            models.Index(
                fields=["tenant_id", "resource_id"], name="resource_tag_tenant_idx"
            ),
        ]


class Finding(PostgresPartitionedModel, RowLevelSecurityProtectedModel):
    """
    Defines the Finding model.

    Findings uses a partitioned table to store findings. The partitions are created based on the UUIDv7 `id` field.

    Note when creating migrations, you must use `python manage.py pgmakemigrations` to create the migrations.
    """

    objects = ActiveProviderPartitionedManager()
    all_objects = models.Manager()

    class PartitioningMeta:
        method = PostgresPartitioningMethod.RANGE
        key = ["id"]

    class DeltaChoices(models.TextChoices):
        NEW = "new", _("New")
        CHANGED = "changed", _("Changed")

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    first_seen_at = models.DateTimeField(editable=False, null=True)

    uid = models.CharField(max_length=300)
    delta = FindingDeltaEnumField(
        choices=DeltaChoices.choices,
        blank=True,
        null=True,
    )

    status = StatusEnumField(choices=StatusChoices)
    status_extended = models.TextField(blank=True, null=True)

    severity = SeverityEnumField(choices=SeverityChoices)

    impact = SeverityEnumField(choices=SeverityChoices)
    impact_extended = models.TextField(blank=True, null=True)

    raw_result = models.JSONField(default=dict)
    tags = models.JSONField(default=dict, null=True, blank=True)
    check_id = models.CharField(max_length=100, blank=False, null=False)
    check_metadata = models.JSONField(default=dict, null=False)
    muted = models.BooleanField(default=False, null=False)
    compliance = models.JSONField(default=dict, null=True, blank=True)

    # Denormalize resource data for performance
    resource_regions = ArrayField(
        models.CharField(max_length=100), blank=True, null=True
    )
    resource_services = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        null=True,
    )
    resource_types = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        null=True,
    )

    # Relationships
    scan = models.ForeignKey(to=Scan, related_name="findings", on_delete=models.CASCADE)

    # many-to-many Resources. Relationship is defined on Resource
    resources = models.ManyToManyField(
        Resource,
        verbose_name="Resources associated with the finding",
        through="ResourceFindingMapping",
        related_name="findings",
    )

    # TODO: Add resource search
    text_search = models.GeneratedField(
        expression=SearchVector(
            "impact_extended", "status_extended", weight="A", config="simple"
        ),
        output_field=SearchVectorField(),
        db_persist=True,
        null=True,
        editable=False,
    )

    class Meta(RowLevelSecurityProtectedModel.Meta):
        db_table = "findings"

        constraints = [
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_Finding",
                statements=["SELECT", "UPDATE", "INSERT", "DELETE"],
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_modelname_default",
                partition_name="default",
                statements=["SELECT", "UPDATE", "INSERT", "DELETE"],
            ),
        ]

        indexes = [
            models.Index(fields=["tenant_id", "id"], name="findings_tenant_and_id_idx"),
            GinIndex(fields=["text_search"], name="gin_findings_search_idx"),
            models.Index(fields=["tenant_id", "scan_id"], name="find_tenant_scan_idx"),
            models.Index(
                fields=["tenant_id", "scan_id", "id"], name="find_tenant_scan_id_idx"
            ),
            models.Index(
                fields=["tenant_id", "id"],
                condition=Q(delta="new"),
                name="find_delta_new_idx",
            ),
            models.Index(
                fields=["tenant_id", "uid", "-inserted_at"],
                name="find_tenant_uid_inserted_idx",
            ),
            GinIndex(fields=["resource_services"], name="gin_find_service_idx"),
            GinIndex(fields=["resource_regions"], name="gin_find_region_idx"),
            GinIndex(fields=["resource_types"], name="gin_find_rtype_idx"),
            models.Index(
                fields=["tenant_id", "scan_id", "check_id"],
                name="find_tenant_scan_check_idx",
            ),
        ]

    class JSONAPIMeta:
        resource_name = "findings"

    def add_resources(self, resources: list[Resource] | None):
        if not resources:
            return

        self.resource_regions = self.resource_regions or []
        self.resource_services = self.resource_services or []
        self.resource_types = self.resource_types or []

        # Deduplication
        regions = set(self.resource_regions)
        services = set(self.resource_services)
        types = set(self.resource_types)

        for resource in resources:
            ResourceFindingMapping.objects.update_or_create(
                resource=resource, finding=self, tenant_id=self.tenant_id
            )
            regions.add(resource.region)
            services.add(resource.service)
            types.add(resource.type)

        self.resource_regions = list(regions)
        self.resource_services = list(services)
        self.resource_types = list(types)
        self.save()


class ResourceFindingMapping(PostgresPartitionedModel, RowLevelSecurityProtectedModel):
    """
    Defines the ResourceFindingMapping model.

    ResourceFindingMapping is used to map a Finding to a Resource.

    It follows the same partitioning strategy as the Finding model.
    """

    # NOTE that we don't really need a primary key here,
    #      but everything is easier with django if we do
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    finding = models.ForeignKey(Finding, on_delete=models.CASCADE)

    class PartitioningMeta:
        method = PostgresPartitioningMethod.RANGE
        key = ["finding_id"]

    class Meta(RowLevelSecurityProtectedModel.Meta):
        db_table = "resource_finding_mappings"
        base_manager_name = "objects"
        abstract = False

        # django will automatically create indexes for:
        #   - resource_id
        #   - finding_id
        #   - tenant_id
        #   - id

        constraints = [
            models.UniqueConstraint(
                fields=("tenant_id", "resource_id", "finding_id"),
                name="unique_resource_finding_mappings_by_tenant",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_ResourceFindingMapping",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
            RowLevelSecurityConstraint(
                "tenant_id",
                name=f"rls_on_{db_table}_default",
                partition_name="default",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]


class ProviderSecret(RowLevelSecurityProtectedModel):
    objects = ActiveProviderManager()
    all_objects = models.Manager()

    class TypeChoices(models.TextChoices):
        STATIC = "static", _("Key-value pairs")
        ROLE = "role", _("Role assumption")
        SERVICE_ACCOUNT = "service_account", _("GCP Service Account Key")

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    name = models.CharField(
        blank=True, null=True, max_length=100, validators=[MinLengthValidator(3)]
    )
    secret_type = ProviderSecretTypeEnumField(choices=TypeChoices.choices)
    _secret = models.BinaryField(db_column="secret")
    provider = models.OneToOneField(
        Provider,
        on_delete=models.CASCADE,
        related_name="secret",
        related_query_name="secret",
    )

    class Meta(RowLevelSecurityProtectedModel.Meta):
        db_table = "provider_secrets"

        constraints = [
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_ProviderSecret",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

    class JSONAPIMeta:
        resource_name = "provider-secrets"

    @property
    def secret(self):
        if isinstance(self._secret, memoryview):
            encrypted_bytes = self._secret.tobytes()
        elif isinstance(self._secret, str):
            encrypted_bytes = self._secret.encode()
        else:
            encrypted_bytes = self._secret
        decrypted_data = fernet.decrypt(encrypted_bytes)
        return json.loads(decrypted_data.decode())

    @secret.setter
    def secret(self, value):
        encrypted_data = fernet.encrypt(json.dumps(value).encode())
        self._secret = encrypted_data


class Invitation(RowLevelSecurityProtectedModel):
    class State(models.TextChoices):
        PENDING = "pending", _("Invitation is pending")
        ACCEPTED = "accepted", _("Invitation was accepted by a user")
        EXPIRED = "expired", _("Invitation expired after the configured time")
        REVOKED = "revoked", _("Invitation was revoked by a user")

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    email = models.EmailField(max_length=254, blank=False, null=False)
    state = InvitationStateEnumField(choices=State.choices, default=State.PENDING)
    token = models.CharField(
        max_length=500,  # Increased to accommodate JWT tokens
        unique=True,
        default=generate_random_token,
        editable=False,
        blank=False,
        null=False,
        validators=[MinLengthValidator(14)],
    )
    expires_at = models.DateTimeField(default=one_week_from_now)
    inviter = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # Prevent deletion of user who created invitation
        related_name="invitations",
        related_query_name="invitation",
        null=False,  # Database requires NOT NULL
        db_column='invited_by_id',  # Map to existing database column
    )

    class Meta(RowLevelSecurityProtectedModel.Meta):
        db_table = "invitations"

        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "token", "email"),
                name="unique_tenant_token_email_by_invitation",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_ProviderSecret_new",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

    class JSONAPIMeta:
        resource_name = "invitations"


class Role(RowLevelSecurityProtectedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    manage_users = models.BooleanField(default=False)
    manage_account = models.BooleanField(default=False)
    manage_billing = models.BooleanField(default=False)
    manage_providers = models.BooleanField(default=False)
    manage_integrations = models.BooleanField(default=False)
    manage_scans = models.BooleanField(default=False)
    unlimited_visibility = models.BooleanField(default=False)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    provider_groups = models.ManyToManyField(
        ProviderGroup, through="RoleProviderGroupRelationship", related_name="roles"
    )
    users = models.ManyToManyField(
        User, through="UserRoleRelationship", related_name="roles"
    )
    invitations = models.ManyToManyField(
        Invitation, through="InvitationRoleRelationship", related_name="roles"
    )

    # Filter permission_state
    PERMISSION_FIELDS = [
        "manage_users",
        "manage_account",
        "manage_billing",
        "manage_providers",
        "manage_integrations",
        "manage_scans",
    ]

    @property
    def permission_state(self):
        values = [getattr(self, field) for field in self.PERMISSION_FIELDS]
        if all(values):
            return PermissionChoices.UNLIMITED
        elif not any(values):
            return PermissionChoices.NONE
        else:
            return PermissionChoices.LIMITED

    @classmethod
    def filter_by_permission_state(cls, queryset, value):
        q_all_true = Q(**{field: True for field in cls.PERMISSION_FIELDS})
        q_all_false = Q(**{field: False for field in cls.PERMISSION_FIELDS})

        if value == PermissionChoices.UNLIMITED:
            return queryset.filter(q_all_true)
        elif value == PermissionChoices.NONE:
            return queryset.filter(q_all_false)
        else:
            return queryset.exclude(q_all_true | q_all_false)

    class Meta:
        db_table = "roles"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="unique_role_per_tenant",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_Provider_Secret",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

    class JSONAPIMeta:
        resource_name = "roles"


class RoleProviderGroupRelationship(RowLevelSecurityProtectedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    provider_group = models.ForeignKey(ProviderGroup, on_delete=models.CASCADE)
    inserted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "role_provider_group_relationship"
        constraints = [
            models.UniqueConstraint(
                fields=["role_id", "provider_group_id"],
                name="unique_role_provider_group_relationship",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_Role_Provider",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

    class JSONAPIMeta:
        resource_name = "role-provider_groups"


class UserRoleRelationship(RowLevelSecurityProtectedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    inserted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "role_user_relationship"
        constraints = [
            models.UniqueConstraint(
                fields=["role_id", "user_id"],
                name="unique_role_user_relationship",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_Role_Provider_Group",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

    class JSONAPIMeta:
        resource_name = "user-roles"


class InvitationRoleRelationship(RowLevelSecurityProtectedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    invitation = models.ForeignKey(Invitation, on_delete=models.CASCADE)
    inserted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "role_invitation_relationship"
        constraints = [
            models.UniqueConstraint(
                fields=["role_id", "invitation_id"],
                name="unique_role_invitation_relationship",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_Role_RElationship",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

    class JSONAPIMeta:
        resource_name = "invitation-roles"


class AzureOAuthConfig(models.Model):
    """
    Stores Azure AD OAuth configuration per organization (pre-auth), keyed by tenant_name.
    """
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    tenant_name = models.CharField(max_length=255, db_index=True)
    client_id = models.CharField(max_length=255)
    client_secret = models.TextField()
    tenant_id = models.CharField(max_length=255)
    redirect_uri = models.CharField(max_length=500)
    scopes = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "azure_oauth_configs"
        unique_together = (("tenant_name",),)

class ComplianceOverview(RowLevelSecurityProtectedModel):
    objects = ActiveProviderManager()
    all_objects = models.Manager()

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    compliance_id = models.CharField(max_length=100, blank=False, null=False)
    framework = models.CharField(max_length=100, blank=False, null=False)
    version = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    region = models.CharField(max_length=50, blank=True)
    requirements = models.JSONField(default=dict)
    requirements_passed = models.IntegerField(default=0)
    requirements_failed = models.IntegerField(default=0)
    requirements_manual = models.IntegerField(default=0)
    total_requirements = models.IntegerField(default=0)

    scan = models.ForeignKey(
        Scan,
        on_delete=models.CASCADE,
        related_name="compliance_overviews",
        related_query_name="compliance_overview",
        null=True,
    )

    class Meta(RowLevelSecurityProtectedModel.Meta):
        db_table = "compliance_overviews"

        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "scan", "compliance_id", "region"),
                name="unique_tenant_scan_region_compliance_by_compliance_overview",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_complianceoverview",
                statements=["SELECT", "INSERT", "DELETE"],
            ),
        ]
        indexes = [
            models.Index(fields=["compliance_id"], name="comp_ov_cp_id_idx"),
            models.Index(fields=["requirements_failed"], name="comp_ov_req_fail_idx"),
            models.Index(
                fields=["compliance_id", "requirements_failed"],
                name="comp_ov_cp_id_req_fail_idx",
            ),
        ]

    class JSONAPIMeta:
        resource_name = "compliance-overviews"


class ComplianceRequirementOverview(RowLevelSecurityProtectedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    compliance_id = models.TextField(blank=False)
    framework = models.TextField(blank=False)
    version = models.TextField(blank=True)
    description = models.TextField(blank=True)
    region = models.TextField(blank=False)

    requirement_id = models.TextField(blank=False)
    requirement_status = StatusEnumField(choices=StatusChoices)
    passed_checks = models.IntegerField(default=0)
    failed_checks = models.IntegerField(default=0)
    total_checks = models.IntegerField(default=0)

    scan = models.ForeignKey(
        Scan,
        on_delete=models.CASCADE,
        related_name="compliance_requirements_overviews",
        related_query_name="compliance_requirements_overview",
    )

    class Meta(RowLevelSecurityProtectedModel.Meta):
        db_table = "compliance_requirements_overviews"

        constraints = [
            models.UniqueConstraint(
                fields=(
                    "tenant_id",
                    "scan_id",
                    "compliance_id",
                    "requirement_id",
                    "region",
                ),
                name="unique_tenant_compliance_requirement_overview",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_compliance",
                statements=["SELECT", "INSERT", "DELETE"],
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "scan_id"], name="cro_tenant_scan_idx"),
            models.Index(
                fields=["tenant_id", "scan_id", "compliance_id"],
                name="cro_scan_comp_idx",
            ),
            models.Index(
                fields=["tenant_id", "scan_id", "compliance_id", "region"],
                name="cro_scan_comp_reg_idx",
            ),
            models.Index(
                fields=["tenant_id", "scan_id", "compliance_id", "requirement_id"],
                name="cro_scan_comp_req_idx",
            ),
            models.Index(
                fields=[
                    "tenant_id",
                    "scan_id",
                    "compliance_id",
                    "requirement_id",
                    "region",
                ],
                name="cro_scan_comp_req_reg_idx",
            ),
        ]

    class JSONAPIMeta:
        resource_name = "compliance-requirements-overviews"


class ScanSummary(RowLevelSecurityProtectedModel):
    objects = ActiveProviderManager()
    all_objects = models.Manager()

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    check_id = models.CharField(max_length=100, blank=False, null=False)
    service = models.TextField(blank=False)
    severity = SeverityEnumField(choices=SeverityChoices)
    region = models.TextField(blank=False)
    _pass = models.IntegerField(db_column="pass", default=0)
    fail = models.IntegerField(default=0)
    muted = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    new = models.IntegerField(default=0)
    changed = models.IntegerField(default=0)
    unchanged = models.IntegerField(default=0)

    fail_new = models.IntegerField(default=0)
    fail_changed = models.IntegerField(default=0)
    pass_new = models.IntegerField(default=0)
    pass_changed = models.IntegerField(default=0)
    muted_new = models.IntegerField(default=0)
    muted_changed = models.IntegerField(default=0)

    scan = models.ForeignKey(
        Scan,
        on_delete=models.CASCADE,
        related_name="aggregations",
        related_query_name="aggregation",
    )

    class Meta(RowLevelSecurityProtectedModel.Meta):
        db_table = "scan_summaries"

        constraints = [
            models.UniqueConstraint(
                fields=("tenant", "scan", "check_id", "service", "severity", "region"),
                name="unique_scan_summary",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_scan",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "scan_id"],
                name="scan_summaries_tenant_scan_idx",
            ),
            models.Index(
                fields=["tenant_id", "scan_id", "service"],
                name="ss_tenant_scan_service_idx",
            ),
            models.Index(
                fields=["tenant_id", "scan_id", "severity"],
                name="ss_tenant_scan_severity_idx",
            ),
        ]

    class JSONAPIMeta:
        resource_name = "scan-summaries"


class Integration(RowLevelSecurityProtectedModel):
    class IntegrationChoices(models.TextChoices):
        S3 = "amazon_s3", _("Amazon S3")
        SAML = "saml", _("SAML")
        AWS_SECURITY_HUB = "aws_security_hub", _("AWS Security Hub")
        JIRA = "jira", _("JIRA")
        SLACK = "slack", _("Slack")

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    inserted_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    enabled = models.BooleanField(default=False)
    connected = models.BooleanField(null=True, blank=True)
    connection_last_checked_at = models.DateTimeField(null=True, blank=True)
    integration_type = IntegrationTypeEnumField(choices=IntegrationChoices.choices)
    configuration = models.JSONField(default=dict)
    _credentials = models.BinaryField(db_column="credentials")

    providers = models.ManyToManyField(
        Provider,
        related_name="integrations",
        through="IntegrationProviderRelationship",
        blank=True,
    )

    class Meta(RowLevelSecurityProtectedModel.Meta):
        db_table = "integrations"

        constraints = [
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_integrations",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

    class JSONAPIMeta:
        resource_name = "integrations"

    @property
    def credentials(self):
        if isinstance(self._credentials, memoryview):
            encrypted_bytes = self._credentials.tobytes()
        elif isinstance(self._credentials, str):
            encrypted_bytes = self._credentials.encode()
        else:
            encrypted_bytes = self._credentials
        decrypted_data = fernet.decrypt(encrypted_bytes)
        return json.loads(decrypted_data.decode())

    @credentials.setter
    def credentials(self, value):
        encrypted_data = fernet.encrypt(json.dumps(value).encode())
        self._credentials = encrypted_data


class IntegrationProviderRelationship(RowLevelSecurityProtectedModel):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE)
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE)
    inserted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "integration_provider_mappings"
        constraints = [
            models.UniqueConstraint(
                fields=["integration_id", "provider_id"],
                name="unique_integration_provider_rel",
            ),
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_on_tanent",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]


class ResourceScanSummary(RowLevelSecurityProtectedModel):
    scan_id = models.UUIDField(default=uuid7, db_index=True)
    resource_id = models.UUIDField(default=uuid4, db_index=True)
    service = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=100)

    class Meta:
        db_table = "resource_scan_summaries"
        unique_together = (("tenant_id", "scan_id", "resource_id"),)

        indexes = [
            # Single-dimension lookups:
            models.Index(
                fields=["tenant_id", "scan_id", "service"],
                name="rss_tenant_scan_svc_idx",
            ),
            models.Index(
                fields=["tenant_id", "scan_id", "region"],
                name="rss_tenant_scan_reg_idx",
            ),
            models.Index(
                fields=["tenant_id", "scan_id", "resource_type"],
                name="rss_tenant_scan_type_idx",
            ),
            # Two-dimension cross-filters:
            models.Index(
                fields=["tenant_id", "scan_id", "region", "service"],
                name="rss_tenant_scan_reg_svc_idx",
            ),
            models.Index(
                fields=["tenant_id", "scan_id", "service", "resource_type"],
                name="rss_tenant_scan_svc_type_idx",
            ),
            models.Index(
                fields=["tenant_id", "scan_id", "region", "resource_type"],
                name="rss_tenant_scan_reg_type_idx",
            ),
        ]

        constraints = [
            RowLevelSecurityConstraint(
                field="tenant_id",
                name="rls_Row_level",
                statements=["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
        ]

# Add this after the Invitation model definition
TenantInvitation = Invitation  # Create an alias for backward compatibility


class TenantOAuthConfig(models.Model):
    """
    Stores OAuth provider configuration for each tenant.
    Each tenant can have multiple OAuth providers configured.
    """
    
    OAUTH_PROVIDERS = [
        ('azure', 'Azure AD (Microsoft Entra ID)'),
        ('google', 'Google OAuth'),
        ('github', 'GitHub OAuth'),
        ('okta', 'Okta'),
        ('auth0', 'Auth0'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='oauth_configs',
        help_text="Tenant this OAuth config belongs to"
    )
    provider = models.CharField(
        max_length=50,
        choices=OAUTH_PROVIDERS,
        help_text="OAuth provider type"
    )
    
    # OAuth Configuration
    client_id = models.CharField(max_length=255, help_text="OAuth Client ID")
    _client_secret = models.BinaryField(
        db_column="client_secret",
        help_text="Encrypted OAuth Client Secret"
    )
    redirect_uri = models.URLField(help_text="OAuth Redirect URI")
    
    # Provider-specific configuration
    provider_tenant_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Provider-specific tenant ID (e.g., Azure tenant ID)"
    )
    scopes = models.JSONField(
        default=list,
        help_text="OAuth scopes to request"
    )
    allowed_domains = models.JSONField(
        default=list,
        help_text="Allowed email domains for this provider"
    )
    
    # Configuration settings
    is_active = models.BooleanField(default=True, help_text="Whether this config is active")
    auto_create_users = models.BooleanField(
        default=True,
        help_text="Automatically create users on first login"
    )
    require_email_verification = models.BooleanField(
        default=False,
        help_text="Require email verification for new users"
    )
    
    # Advanced settings
    additional_params = models.JSONField(
        default=dict,
        help_text="Additional OAuth parameters"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_oauth_configs'
    )
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'tenant_oauth_configs'
        unique_together = ['tenant', 'provider']
        indexes = [
            models.Index(fields=['tenant', 'provider']),
            models.Index(fields=['tenant', 'is_active']),
            models.Index(fields=['provider']),
        ]
    
    def __str__(self):
        return f"{self.tenant.name} - {self.get_provider_display()}"
    
    @property
    def client_secret(self):
        """Decrypt and return the OAuth client secret"""
        if not self._client_secret:
            return None
        
        try:
            fernet = Fernet(settings.SECRETS_ENCRYPTION_KEY.encode())
            decrypted_data = fernet.decrypt(self._client_secret)
            return decrypted_data.decode()
        except Exception as e:
            raise ValidationError(f"Failed to decrypt client secret: {e}")
    
    @client_secret.setter
    def client_secret(self, value):
        """Encrypt and store the OAuth client secret"""
        if not value:
            self._client_secret = None
            return
        
        try:
            fernet = Fernet(settings.SECRETS_ENCRYPTION_KEY.encode())
            encrypted_data = fernet.encrypt(value.encode())
            self._client_secret = encrypted_data
        except Exception as e:
            raise ValidationError(f"Failed to encrypt client secret: {e}")


class TenantOAuthUser(models.Model):
    """
    Links users to their OAuth provider accounts within a tenant.
    This allows users to have different OAuth accounts for different tenants.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='oauth_users'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tenant_oauth_accounts'
    )
    oauth_config = models.ForeignKey(
        TenantOAuthConfig,
        on_delete=models.CASCADE,
        related_name='oauth_users'
    )
    
    # Provider-specific user identifiers
    provider_user_id = models.CharField(
        max_length=255,
        help_text="User ID from the OAuth provider"
    )
    provider_email = models.EmailField(
        help_text="Email from the OAuth provider"
    )
    
    # OAuth token storage (encrypted)
    _access_token = models.BinaryField(
        db_column="access_token",
        null=True,
        blank=True,
        help_text="Encrypted access token"
    )
    _refresh_token = models.BinaryField(
        db_column="refresh_token",
        null=True,
        blank=True,
        help_text="Encrypted refresh token"
    )
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the access token expires"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tenant_oauth_users'
        unique_together = ['tenant', 'oauth_config', 'provider_user_id']
        indexes = [
            models.Index(fields=['tenant', 'user']),
            models.Index(fields=['tenant', 'oauth_config']),
            models.Index(fields=['provider_user_id']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.tenant.name} - {self.oauth_config.provider}"
    
    @property
    def access_token(self):
        """Decrypt and return the access token"""
        if not self._access_token:
            return None
        
        try:
            fernet = Fernet(settings.SECRETS_ENCRYPTION_KEY.encode())
            decrypted_data = fernet.decrypt(self._access_token)
            return decrypted_data.decode()
        except Exception as e:
            raise ValidationError(f"Failed to decrypt access token: {e}")
    
    @access_token.setter
    def access_token(self, value):
        """Encrypt and store the access token"""
        if not value:
            self._access_token = None
            return
        
        try:
            fernet = Fernet(settings.SECRETS_ENCRYPTION_KEY.encode())
            encrypted_data = fernet.encrypt(value.encode())
            self._access_token = encrypted_data
        except Exception as e:
            raise ValidationError(f"Failed to encrypt access token: {e}")
    
    @property
    def refresh_token(self):
        """Decrypt and return the refresh token"""
        if not self._refresh_token:
            return None
        
        try:
            fernet = Fernet(settings.SECRETS_ENCRYPTION_KEY.encode())
            decrypted_data = fernet.decrypt(self._refresh_token)
            return decrypted_data.decode()
        except Exception as e:
            raise ValidationError(f"Failed to decrypt refresh token: {e}")
    
    @refresh_token.setter
    def refresh_token(self, value):
        """Encrypt and store the refresh token"""
        if not value:
            self._refresh_token = None
            return
        
        try:
            fernet = Fernet(settings.SECRETS_ENCRYPTION_KEY.encode())
            encrypted_data = fernet.encrypt(value.encode())
            self._refresh_token = encrypted_data
        except Exception as e:
            raise ValidationError(f"Failed to encrypt refresh token: {e}")
    
    def is_token_expired(self):
        """Check if the access token is expired"""
        if not self.token_expires_at:
            return True
        return timezone.now() >= self.token_expires_at
    
    def update_tokens(self, access_token: str, refresh_token: str = None, expires_in: int = None):
        """Update stored OAuth tokens"""
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        
        if expires_in:
            self.token_expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)
        
        self.save()
    
    def update_last_login(self):
        """Update the last login timestamp"""
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])


class SecurityAuditLog(models.Model):
    """
    Comprehensive audit logging for security violations and important events.
    This model tracks all security-related activities across the multi-tenant system.
    """
    
    # Event types for categorization
    EVENT_TYPES = [
        ('login_success', 'Successful Login'),
        ('login_failed', 'Failed Login'),
        ('login_blocked', 'Login Blocked'),
        ('account_locked', 'Account Locked'),
        ('account_unlocked', 'Account Unlocked'),
        ('password_changed', 'Password Changed'),
        ('tenant_access_denied', 'Tenant Access Denied'),
        ('tenant_switched', 'Tenant Switched'),
        ('permission_denied', 'Permission Denied'),
        ('data_access_violation', 'Data Access Violation'),
        ('api_rate_limit', 'API Rate Limit Exceeded'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('security_scan', 'Security Scan'),
        ('user_created', 'User Created'),
        ('user_deleted', 'User Deleted'),
        ('tenant_created', 'Tenant Created'),
        ('tenant_modified', 'Tenant Modified'),
        ('tenant_deleted', 'Tenant Deleted'),
        ('oauth_login', 'OAuth Login'),
        ('oauth_failed', 'OAuth Failed'),
        ('two_factor_enabled', '2FA Enabled'),
        ('two_factor_disabled', '2FA Disabled'),
        ('admin_action', 'Admin Action'),
        ('system_error', 'System Error'),
    ]
    
    # Severity levels
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Event details
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES,
        db_index=True,
        help_text="Type of security event"
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_LEVELS,
        default='medium',
        db_index=True,
        help_text="Severity level of the event"
    )
    
    # User and tenant context
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_audit_logs',
        help_text="User involved in the event (if applicable)"
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_audit_logs',
        help_text="Tenant context of the event"
    )
    
    # Request context
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the request"
    )
    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text="User agent string from the request"
    )
    request_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Request path that triggered the event"
    )
    request_method = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text="HTTP method of the request"
    )
    
    # Event details
    message = models.TextField(
        help_text="Human-readable description of the event"
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional structured data about the event"
    )
    
    # Security context
    is_security_violation = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this event represents a security violation"
    )
    requires_investigation = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this event requires manual investigation"
    )
    
    # Resolution tracking
    resolved = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this event has been resolved"
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_audit_logs',
        help_text="User who resolved this event"
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this event was resolved"
    )
    resolution_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Notes about how this event was resolved"
    )
    
    class Meta:
        db_table = 'security_audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp'], name='idx_audit_timestamp'),
            models.Index(fields=['event_type'], name='idx_audit_event_type'),
            models.Index(fields=['severity'], name='idx_audit_severity'),
            models.Index(fields=['user'], name='idx_audit_user'),
            models.Index(fields=['tenant'], name='idx_audit_tenant'),
            models.Index(fields=['is_security_violation'], name='idx_audit_violation'),
            models.Index(fields=['requires_investigation'], name='idx_audit_investigation'),
            models.Index(fields=['resolved'], name='idx_audit_resolved'),
            models.Index(fields=['ip_address'], name='idx_audit_ip'),
            models.Index(fields=['timestamp', 'event_type'], name='idx_audit_timestamp_event'),
            models.Index(fields=['tenant', 'timestamp'], name='idx_audit_tenant_timestamp'),
        ]
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.timestamp} - {self.message[:50]}"
    
    @classmethod
    def log_event(cls, event_type, message, user=None, tenant=None, severity='medium', 
                  ip_address=None, user_agent=None, request_path=None, request_method=None,
                  details=None, is_security_violation=False, requires_investigation=False):
        """
        Log a security event with comprehensive context.
        
        Args:
            event_type: Type of event from EVENT_TYPES
            message: Human-readable description
            user: User involved (if applicable)
            tenant: Tenant context (if applicable)
            severity: Severity level
            ip_address: IP address of the request
            user_agent: User agent string
            request_path: Request path
            request_method: HTTP method
            details: Additional structured data
            is_security_violation: Whether this is a security violation
            requires_investigation: Whether manual investigation is needed
        """
        return cls.objects.create(
            event_type=event_type,
            message=message,
            user=user,
            tenant=tenant,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            request_method=request_method,
            details=details or {},
            is_security_violation=is_security_violation,
            requires_investigation=requires_investigation
        )
    
    @classmethod
    def log_login_attempt(cls, user, success, ip_address=None, user_agent=None, 
                          request_path=None, tenant=None, details=None):
        """Log a login attempt with appropriate severity and flags."""
        if success:
            event_type = 'login_success'
            severity = 'low'
            message = f"Successful login for user {user.email}"
            is_violation = False
            requires_investigation = False
        else:
            event_type = 'login_failed'
            severity = 'medium'
            message = f"Failed login attempt for user {user.email if user else 'unknown'}"
            is_violation = True
            requires_investigation = True
        
        return cls.log_event(
            event_type=event_type,
            message=message,
            user=user,
            tenant=tenant,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            details=details,
            is_security_violation=is_violation,
            requires_investigation=requires_investigation
        )
    
    @classmethod
    def log_tenant_access_denied(cls, user, tenant, ip_address=None, user_agent=None, 
                                 request_path=None, details=None):
        """Log when a user is denied access to a tenant."""
        return cls.log_event(
            event_type='tenant_access_denied',
            message=f"User {user.email} denied access to tenant {tenant.name}",
            user=user,
            tenant=tenant,
            severity='high',
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            details=details,
            is_security_violation=True,
            requires_investigation=True
        )
    
    @classmethod
    def log_data_access_violation(cls, user, tenant, resource_type, ip_address=None, 
                                  user_agent=None, request_path=None, details=None):
        """Log when a user attempts to access data they shouldn't."""
        return cls.log_event(
            event_type='data_access_violation',
            message=f"User {user.email} attempted unauthorized access to {resource_type} in tenant {tenant.name}",
            user=user,
            tenant=tenant,
            severity='critical',
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            details=details,
            is_security_violation=True,
            requires_investigation=True
        )
    
    def resolve(self, resolved_by, resolution_notes=None):
        """Mark this audit log as resolved."""
        self.resolved = True
        self.resolved_by = resolved_by
        self.resolved_at = timezone.now()
        self.resolution_notes = resolution_notes
        self.save()
    
    def get_security_summary(self):
        """Get a summary of security events for this log entry."""
        return {
            'event_type': self.get_event_type_display(),
            'severity': self.get_severity_display(),
            'timestamp': self.timestamp,
            'user': self.user.email if self.user else None,
            'tenant': self.tenant.name if self.tenant else None,
            'is_violation': self.is_security_violation,
            'requires_investigation': self.requires_investigation,
            'resolved': self.resolved
        }
