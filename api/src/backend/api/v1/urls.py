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
    path('tenant/login/', tenant_auth.TenantLoginView.as_view(), name='tenant-login'),
    path('tenant/login', tenant_auth.TenantLoginView.as_view(), name='tenant-login-no-slash'),
    path('tenant/refresh-token/', tenant_auth.TenantRefreshTokenView.as_view(), name='tenant-refresh-token'),
    path('tenant/logout/', tenant_auth.TenantLogoutView.as_view(), name='tenant-logout'),
    path('tenant/register/', tenant_auth.tenant_register, name='tenant-register'),
    path('tenant/register', tenant_auth.tenant_register, name='tenant-register-no-slash'),
    path('tenant/register-test/', tenant_auth.tenant_register_test, name='tenant-register-test'),
    
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
    
    # Include router URLs at the end to avoid conflicts
    path('', include(router.urls)),
]