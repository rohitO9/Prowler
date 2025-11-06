"""
Tenant Service - Handles tenant creation, SSO setup, and Azure AD integration.

This service manages the complete tenant lifecycle including:
- Tenant creation and configuration
- Azure AD OAuth app registration
- SSO setup and configuration
- Domain verification
- Tenant settings management
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from api.models import Tenant, TenantOAuthConfig, SecurityAuditLog
from api.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)


class TenantService:
    """Service for managing tenant creation and SSO setup."""
    
    def __init__(self):
        self.audit_log = AuditLogService()
    
    def create_tenant(self, tenant_data: Dict[str, Any], created_by_user=None) -> Tenant:
        """
        Create a new tenant with initial configuration.
        
        Args:
            tenant_data: Dictionary containing tenant information
            created_by_user: User who created the tenant (for audit logging)
            
        Returns:
            Tenant: The created tenant instance
        """
        try:
            with transaction.atomic():
                # Validate tenant data
                self._validate_tenant_data(tenant_data)
                
                # Create tenant
                tenant = Tenant.objects.create(
                    name=tenant_data['name'],
                    subdomain=tenant_data['subdomain'],
                    domain=tenant_data.get('domain'),
                    contact_email=tenant_data['contact_email'],
                    contact_phone=tenant_data.get('contact_phone'),
                    address=tenant_data.get('address'),
                    logo_url=tenant_data.get('logo_url'),
                    theme_color=tenant_data.get('theme_color', '#3B82F6'),
                    secondary_color=tenant_data.get('secondary_color', '#1E40AF'),
                    max_users=tenant_data.get('max_users', 5),
                    max_providers=tenant_data.get('max_providers', 3),
                    trial_ends_at=timezone.now() + timezone.timedelta(days=14),  # 14-day trial
                    subscription_status='trial',
                    created_by=created_by_user,
                    is_active=True,
                    is_verified=False,  # Requires admin verification
                    allow_registration=False,  # Invite-only by default
                )
                
                # Log tenant creation
                self.audit_log.log_event(
                    event_type='tenant_created',
                    message=f"Tenant '{tenant.name}' created with subdomain '{tenant.subdomain}'",
                    user=created_by_user,
                    tenant=tenant,
                    severity='medium',
                    details={
                        'tenant_id': str(tenant.id),
                        'subdomain': tenant.subdomain,
                        'contact_email': tenant.contact_email,
                        'trial_ends_at': tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None
                    }
                )
                
                logger.info(f"✅ Created tenant: {tenant.name} ({tenant.subdomain})")
                return tenant
                
        except Exception as e:
            logger.error(f"❌ Failed to create tenant: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to create tenant: {str(e)}",
                user=created_by_user,
                severity='high',
                details={'error': str(e), 'tenant_data': tenant_data}
            )
            raise
    
    def setup_azure_ad_sso(self, tenant: Tenant, oauth_config: Dict[str, Any], 
                          configured_by_user=None) -> TenantOAuthConfig:
        """
        Set up Azure AD SSO for a tenant.
        
        Args:
            tenant: The tenant to configure SSO for
            oauth_config: Azure AD OAuth configuration
            configured_by_user: User who configured SSO
            
        Returns:
            TenantOAuthConfig: The created OAuth configuration
        """
        try:
            with transaction.atomic():
                # Validate OAuth configuration
                self._validate_azure_oauth_config(oauth_config)
                
                # Create OAuth configuration
                oauth_config_obj = TenantOAuthConfig.objects.create(
                    tenant=tenant,
                    provider='azure',
                    client_id=oauth_config['client_id'],
                    client_secret=oauth_config['client_secret'],
                    redirect_uri=oauth_config['redirect_uri'],
                    provider_tenant_id=oauth_config.get('tenant_id'),
                    scopes=oauth_config.get('scopes', ['openid', 'profile', 'email']),
                    allowed_domains=oauth_config.get('allowed_domains', []),
                    is_active=True,
                    auto_create_users=True,
                    require_email_verification=False,
                    created_by=configured_by_user
                )
                
                # Log SSO setup
                self.audit_log.log_event(
                    event_type='admin_action',
                    message=f"Azure AD SSO configured for tenant '{tenant.name}'",
                    user=configured_by_user,
                    tenant=tenant,
                    severity='medium',
                    details={
                        'provider': 'azure',
                        'client_id': oauth_config['client_id'],
                        'redirect_uri': oauth_config['redirect_uri'],
                        'scopes': oauth_config.get('scopes', []),
                        'allowed_domains': oauth_config.get('allowed_domains', [])
                    }
                )
                
                logger.info(f"✅ Azure AD SSO configured for tenant: {tenant.name}")
                return oauth_config_obj
                
        except Exception as e:
            logger.error(f"❌ Failed to setup Azure AD SSO: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to setup Azure AD SSO for tenant '{tenant.name}': {str(e)}",
                user=configured_by_user,
                tenant=tenant,
                severity='high',
                details={'error': str(e), 'oauth_config': oauth_config}
            )
            raise
    
    def register_azure_app(self, tenant: Tenant, app_name: str, redirect_uri: str) -> Dict[str, str]:
        """
        Register a new Azure AD application for the tenant.
        This would typically be done through Azure AD Graph API or Microsoft Graph API.
        
        Args:
            tenant: The tenant to register the app for
            app_name: Name for the Azure AD application
            redirect_uri: Redirect URI for the application
            
        Returns:
            Dict containing client_id, client_secret, and tenant_id
        """
        try:
            # This is a placeholder implementation
            # In a real implementation, you would:
            # 1. Authenticate with Azure AD using admin credentials
            # 2. Create a new application registration
            # 3. Generate client secret
            # 4. Configure redirect URIs and permissions
            
            # For now, return mock data
            mock_config = {
                'client_id': f"mock-client-id-{tenant.subdomain}",
                'client_secret': f"mock-client-secret-{tenant.subdomain}",
                'tenant_id': f"mock-tenant-id-{tenant.subdomain}",
                'redirect_uri': redirect_uri
            }
            
            logger.info(f"🔧 Mock Azure AD app registration for tenant: {tenant.name}")
            return mock_config
            
        except Exception as e:
            logger.error(f"❌ Failed to register Azure AD app: {e}")
            raise
    
    def verify_domain_ownership(self, tenant: Tenant, domain: str, 
                              verification_method: str = 'dns') -> bool:
        """
        Verify domain ownership for a tenant.
        
        Args:
            tenant: The tenant to verify domain for
            domain: The domain to verify
            verification_method: Method to use for verification ('dns', 'file', 'email')
            
        Returns:
            bool: True if domain is verified
        """
        try:
            if verification_method == 'dns':
                return self._verify_domain_dns(domain)
            elif verification_method == 'file':
                return self._verify_domain_file(domain)
            elif verification_method == 'email':
                return self._verify_domain_email(domain)
            else:
                raise ValueError(f"Unsupported verification method: {verification_method}")
                
        except Exception as e:
            logger.error(f"❌ Domain verification failed: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Domain verification failed for '{domain}': {str(e)}",
                tenant=tenant,
                severity='medium',
                details={'domain': domain, 'method': verification_method, 'error': str(e)}
            )
            return False
    
    def update_tenant_settings(self, tenant: Tenant, settings_data: Dict[str, Any], 
                              updated_by_user=None) -> Tenant:
        """
        Update tenant settings and configuration.
        
        Args:
            tenant: The tenant to update
            settings_data: Dictionary containing settings to update
            updated_by_user: User who updated the settings
            
        Returns:
            Tenant: The updated tenant instance
        """
        try:
            with transaction.atomic():
                # Track changes for audit logging
                changes = {}
                
                # Update allowed fields
                updatable_fields = [
                    'name', 'contact_email', 'contact_phone', 'address',
                    'logo_url', 'theme_color', 'secondary_color',
                    'max_users', 'max_providers', 'session_timeout_minutes',
                    'max_failed_login_attempts', 'lockout_duration_minutes',
                    'require_email_verification', 'allow_registration'
                ]
                
                for field in updatable_fields:
                    if field in settings_data:
                        old_value = getattr(tenant, field)
                        new_value = settings_data[field]
                        if old_value != new_value:
                            setattr(tenant, field, new_value)
                            changes[field] = {'old': old_value, 'new': new_value}
                
                # Save changes
                if changes:
                    tenant.save()
                    
                    # Log settings update
                    self.audit_log.log_event(
                        event_type='tenant_modified',
                        message=f"Tenant settings updated for '{tenant.name}'",
                        user=updated_by_user,
                        tenant=tenant,
                        severity='low',
                        details={'changes': changes}
                    )
                    
                    logger.info(f"✅ Updated tenant settings: {tenant.name}")
                
                return tenant
                
        except Exception as e:
            logger.error(f"❌ Failed to update tenant settings: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Failed to update tenant settings: {str(e)}",
                user=updated_by_user,
                tenant=tenant,
                severity='medium',
                details={'error': str(e), 'settings_data': settings_data}
            )
            raise
    
    def get_tenant_summary(self, tenant: Tenant) -> Dict[str, Any]:
        """
        Get comprehensive summary of tenant status and configuration.
        
        Args:
            tenant: The tenant to get summary for
            
        Returns:
            Dict containing tenant summary information
        """
        try:
            # Get OAuth configurations
            oauth_configs = tenant.oauth_configs.filter(is_active=True)
            
            # Get user statistics
            user_count = tenant.user_count
            is_at_limit = tenant.is_at_user_limit
            
            # Get security summary
            security_summary = tenant.get_security_summary()
            
            return {
                'tenant': {
                    'id': str(tenant.id),
                    'name': tenant.name,
                    'subdomain': tenant.subdomain,
                    'domain': tenant.domain,
                    'is_active': tenant.is_active,
                    'is_verified': tenant.is_verified,
                    'subscription_status': tenant.subscription_status,
                    'trial_ends_at': tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
                    'created_at': tenant.created_at.isoformat(),
                    'last_activity': tenant.last_activity.isoformat() if tenant.last_activity else None
                },
                'users': {
                    'count': user_count,
                    'max_users': tenant.max_users,
                    'is_at_limit': is_at_limit,
                    'can_add_user': tenant.can_add_user()
                },
                'oauth_configs': [
                    {
                        'provider': config.provider,
                        'is_active': config.is_active,
                        'auto_create_users': config.auto_create_users,
                        'require_email_verification': config.require_email_verification,
                        'last_used': config.last_used.isoformat() if config.last_used else None
                    }
                    for config in oauth_configs
                ],
                'security': security_summary,
                'settings': {
                    'session_timeout_minutes': tenant.session_timeout_minutes,
                    'max_failed_login_attempts': tenant.max_failed_login_attempts,
                    'lockout_duration_minutes': tenant.lockout_duration_minutes,
                    'require_email_verification': tenant.require_email_verification,
                    'allow_registration': tenant.allow_registration
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get tenant summary: {e}")
            raise
    
    def _validate_tenant_data(self, tenant_data: Dict[str, Any]) -> None:
        """Validate tenant data before creation."""
        required_fields = ['name', 'subdomain', 'contact_email']
        
        for field in required_fields:
            if not tenant_data.get(field):
                raise ValidationError(f"Field '{field}' is required")
        
        # Validate subdomain format
        subdomain = tenant_data['subdomain']
        if not subdomain.replace('-', '').replace('_', '').isalnum():
            raise ValidationError("Subdomain must contain only alphanumeric characters and hyphens")
        
        # Check for reserved subdomains
        reserved = ['www', 'api', 'admin', 'app', 'mail', 'smtp', 'ftp', 'localhost', 'test', 'staging']
        if subdomain.lower() in reserved:
            raise ValidationError(f"Subdomain '{subdomain}' is reserved")
    
    def _validate_azure_oauth_config(self, oauth_config: Dict[str, Any]) -> None:
        """Validate Azure OAuth configuration."""
        required_fields = ['client_id', 'client_secret', 'redirect_uri']
        
        for field in required_fields:
            if not oauth_config.get(field):
                raise ValidationError(f"Azure OAuth field '{field}' is required")
    
    def _verify_domain_dns(self, domain: str) -> bool:
        """Verify domain ownership using DNS TXT record."""
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Generate a unique verification token
        # 2. Instruct the user to add a TXT record
        # 3. Query DNS to verify the record exists
        logger.info(f"🔍 DNS verification for domain: {domain}")
        return True  # Mock success
    
    def _verify_domain_file(self, domain: str) -> bool:
        """Verify domain ownership using file upload."""
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Generate a unique verification file
        # 2. Instruct the user to upload it to their domain root
        # 3. Make an HTTP request to verify the file exists
        logger.info(f"🔍 File verification for domain: {domain}")
        return True  # Mock success
    
    def _verify_domain_email(self, domain: str) -> bool:
        """Verify domain ownership using email verification."""
        # This is a placeholder implementation
        # In a real implementation, you would:
        # 1. Generate a unique verification code
        # 2. Send email to admin@domain.com
        # 3. Verify the code when user enters it
        logger.info(f"🔍 Email verification for domain: {domain}")
        return True  # Mock success
