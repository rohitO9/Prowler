"""
Enhanced URL Configuration for Multi-Tenant API

This module provides comprehensive URL routing for the multi-tenant API,
including tenant-aware authentication, validation, and data access endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.v1.views import (
    tenant_auth,
    tenant_validation,
    tenant_azure_auth,
    tenant_registration,
    tenant_onboarding,
    scim,
    TenantViewSet,
    InvitationViewSet,
    InvitationAcceptViewSet,
    CustomTokenObtainView,
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'invitations', InvitationViewSet, basename='invitation')
router.register(r'invitation-accept', InvitationAcceptViewSet, basename='invitation-accept')

# Multi-tenant URL patterns
urlpatterns = [
    # Basic Authentication Endpoints (working)
    path('tokens/', CustomTokenObtainView.as_view(), name='token-obtain'),
    path('tokens', CustomTokenObtainView.as_view(), name='token-obtain-no-slash'),
    
    # User endpoints
    path('users/me/', tenant_validation.get_user_me, name='user-me'),
    path('users/me', tenant_validation.get_user_me, name='user-me-no-slash'),
    
    # Tenant Authentication Endpoints
    path('tenant/login/', tenant_auth.tenant_login, name='tenant-login'),
    path('tenant/login', tenant_auth.tenant_login, name='tenant-login-no-slash'),
    path('tenant/register/', tenant_auth.tenant_register, name='tenant-register'),
    path('tenant/register', tenant_auth.tenant_register, name='tenant-register-no-slash'),
    
    # Tenant Registration Endpoints (for creating new tenants)
    path('tenant/register-tenant/', tenant_registration.register_tenant, name='register-tenant'),
    path('tenant/register-tenant', tenant_registration.register_tenant, name='register-tenant-no-slash'),
    
    # Tenant Validation Endpoints
    path('tenant/validate-access/', tenant_validation.TenantAccessValidationView.as_view(), name='tenant-validate-access'),
    path('tenant/validate-permission/', tenant_validation.TenantPermissionValidationView.as_view(), name='tenant-validate-permission'),
    path('tenant/check-feature/', tenant_validation.TenantFeatureAccessView.as_view(), name='tenant-check-feature'),
    path('tenant/members/', tenant_validation.get_tenant_members, name='tenant-members'),
    path('tenant/invite-member/', tenant_validation.invite_tenant_member, name='tenant-invite-member'),
    path('tenant/settings/', tenant_validation.get_tenant_settings, name='tenant-settings'),
    
    # Public Tenant Information (no authentication required)
    path('tenant/public-info/', tenant_validation.get_tenant_public_info, name='tenant-public-info'),
    path('tenant/public-info', tenant_validation.get_tenant_public_info, name='tenant-public-info-no-slash'),
    
    # Authenticated Tenant Information
    # path('tenant/info/', include('api.v1.views.tenant_info.urls')),
    
    # Tenant-specific Data Endpoints
    # path('tenant/data/', include('api.v1.views.tenant_data.urls')),
    
    # User Management within Tenant
    # path('tenant/users/', include('api.v1.views.tenant_users.urls')),
    
    # Tenant Analytics and Reporting
    # path('tenant/analytics/', include('api.v1.views.tenant_analytics.urls')),
    
    # Tenant Configuration and Settings
    # path('tenant/config/', include('api.v1.views.tenant_config.urls')),
    
    # Tenant Azure AD Authentication
    path('tenant/azure/init/', tenant_azure_auth.TenantAzureInitView.as_view(), name='tenant-azure-init'),
    path('tenant/azure/callback/', tenant_azure_auth.TenantAzureCallbackView.as_view(), name='tenant-azure-callback'),
    path('tenant/azure/refresh/', tenant_azure_auth.TenantAzureRefreshView.as_view(), name='tenant-azure-refresh'),
    path('tenant/azure/config/', tenant_azure_auth.TenantAzureConfigView.as_view(), name='tenant-azure-config'),
    path('tenant/azure/login-url/', tenant_azure_auth.get_azure_login_url, name='tenant-azure-login-url'),
    
    # New Multi-Tenant Onboarding Endpoints
    path('tenant/create/', tenant_onboarding.create_tenant, name='tenant-create'),
    path('tenant/setup-azure-sso/', tenant_onboarding.setup_azure_sso, name='tenant-setup-azure-sso'),
    path('tenant/sso-config/', tenant_onboarding.get_azure_sso_config, name='tenant-sso-config'),
    path('tokens/azure/config/', tenant_onboarding.get_azure_ad_config_for_auth, name='azure-ad-config-for-auth'),
    path('tenant/invite/', tenant_onboarding.create_invite, name='tenant-invite'),
    path('tenant/invite-user/', tenant_onboarding.invite_user, name='tenant-invite-user'),
    path('tenant/bulk-invite/', tenant_onboarding.create_bulk_invites, name='tenant-bulk-invite'),
    path('tenant/validate-invite/', tenant_onboarding.validate_invite_token, name='tenant-validate-invite'),
    path('tenant/accept-invite/', tenant_onboarding.accept_invite, name='tenant-accept-invite'),
    path('tenant/invites/', tenant_onboarding.get_tenant_invites, name='tenant-invites'),
    path('tenant/revoke-invite/', tenant_onboarding.revoke_invite, name='tenant-revoke-invite'),
    path('tenant/summary/', tenant_onboarding.get_tenant_summary, name='tenant-summary'),
    path('tenant/verify-domain/', tenant_onboarding.verify_domain, name='tenant-verify-domain'),
    path('tenant/domain-instructions/', tenant_onboarding.get_domain_verification_instructions, name='tenant-domain-instructions'),
    
    # Tenant User Management Endpoints
    path('tenant/sync-users/', tenant_onboarding.sync_users_from_azure, name='tenant-sync-users'),
    path('tenant/users/', tenant_onboarding.get_tenant_users, name='tenant-users'),
    path('tenant/users/<str:user_id>/assign-role/', tenant_onboarding.assign_user_role, name='tenant-assign-role'),
    path('tenant/users/<str:user_id>/permissions/', tenant_onboarding.update_user_permissions, name='tenant-update-permissions'),
    path('tenant/users/<str:user_id>/', tenant_onboarding.delete_tenant_user, name='tenant-delete-user'),
    
    # SCIM 2.0 Endpoints for Azure AD Integration
    path('scim/v2/Users/', scim.scim_list_users, name='scim-list-users'),
    path('scim/v2/Users', scim.scim_list_users, name='scim-list-users-no-slash'),
    path('scim/v2/Users/', scim.scim_create_user, name='scim-create-user'),
    path('scim/v2/Users/<str:azure_user_id>/', scim.scim_get_user, name='scim-get-user'),
    path('scim/v2/Users/<str:azure_user_id>/', scim.scim_update_user, name='scim-update-user'),
    path('scim/v2/Users/<str:azure_user_id>/', scim.scim_delete_user, name='scim-delete-user'),
    path('scim/v2/ServiceProviderConfig/', scim.scim_service_provider_config, name='scim-service-provider-config'),
    
    # Include router URLs at the end to avoid conflicts
    path('', include(router.urls)),
]